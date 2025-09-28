"""Reinforcement Learning for trading strategy optimization."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import logging
from abc import ABC, abstractmethod
import random
from collections import deque

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Install torch for RL functionality.")


@dataclass
class RLConfig:
    """Configuration for reinforcement learning."""
    state_size: int = 10
    action_size: int = 3  # Buy, Hold, Sell
    hidden_size: int = 64
    learning_rate: float = 0.001
    gamma: float = 0.95  # Discount factor
    epsilon: float = 1.0  # Exploration rate
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995
    memory_size: int = 10000
    batch_size: int = 32
    target_update_frequency: int = 100
    episodes: int = 1000
    max_steps: int = 1000
    use_gpu: bool = False


class TradingEnvironment:
    """Trading environment for reinforcement learning."""
    
    def __init__(self, data: pd.DataFrame, initial_balance: float = 10000.0,
                 transaction_cost: float = 0.001, max_position: float = 1.0):
        self.data = data.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        self.max_position = max_position
        
        # State variables
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0.0  # Position size (-1 to 1)
        self.shares = 0.0
        self.portfolio_value = initial_balance
        self.done = False
        
        # Track performance
        self.portfolio_history = [initial_balance]
        self.action_history = []
        self.reward_history = []
    
    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0.0
        self.shares = 0.0
        self.portfolio_value = self.initial_balance
        self.done = False
        
        self.portfolio_history = [self.initial_balance]
        self.action_history = []
        self.reward_history = []
        
        return self._get_state()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Take a step in the environment."""
        if self.done:
            return self._get_state(), 0, True, {}
        
        # Execute action
        reward = self._execute_action(action)
        
        # Update state
        self.current_step += 1
        self._update_portfolio_value()
        
        # Check if done
        if self.current_step >= len(self.data) - 1:
            self.done = True
        
        # Get next state
        next_state = self._get_state()
        
        # Store history
        self.portfolio_history.append(self.portfolio_value)
        self.action_history.append(action)
        self.reward_history.append(reward)
        
        info = {
            'portfolio_value': self.portfolio_value,
            'balance': self.balance,
            'shares': self.shares,
            'position': self.position,
            'step': self.current_step
        }
        
        return next_state, reward, self.done, info
    
    def _execute_action(self, action: int) -> float:
        """Execute trading action and return reward."""
        current_price = self.data.iloc[self.current_step]['close']
        previous_price = self.data.iloc[self.current_step - 1]['close'] if self.current_step > 0 else current_price
        
        # Calculate price change
        price_change = (current_price - previous_price) / previous_price if previous_price > 0 else 0
        
        # Execute action
        if action == 0:  # Buy
            new_position = min(1.0, self.position + 0.1)
        elif action == 1:  # Hold
            new_position = self.position
        else:  # Sell
            new_position = max(-1.0, self.position - 0.1)
        
        # Calculate transaction cost
        position_change = abs(new_position - self.position)
        transaction_cost = position_change * self.transaction_cost * self.portfolio_value
        
        # Update position
        self.position = new_position
        
        # Update shares and balance
        if new_position > 0:
            # Long position
            target_shares = (new_position * self.portfolio_value) / current_price
            shares_change = target_shares - self.shares
            cost = shares_change * current_price
            self.shares = target_shares
            self.balance -= cost + transaction_cost
        elif new_position < 0:
            # Short position
            target_shares = (new_position * self.portfolio_value) / current_price
            shares_change = target_shares - self.shares
            proceeds = -shares_change * current_price
            self.shares = target_shares
            self.balance += proceeds - transaction_cost
        else:
            # No position
            if self.shares > 0:
                proceeds = self.shares * current_price
                self.balance += proceeds - transaction_cost
            elif self.shares < 0:
                cost = -self.shares * current_price
                self.balance -= cost + transaction_cost
            self.shares = 0
        
        # Calculate reward
        reward = self._calculate_reward(price_change, position_change)
        
        return reward
    
    def _calculate_reward(self, price_change: float, position_change: float) -> float:
        """Calculate reward based on action and market movement."""
        # Base reward from position and price change
        position_reward = self.position * price_change
        
        # Transaction cost penalty
        transaction_penalty = -position_change * self.transaction_cost
        
        # Risk penalty for large positions
        risk_penalty = -abs(self.position) * 0.01
        
        # Portfolio value change
        portfolio_change = (self.portfolio_value - self.initial_balance) / self.initial_balance
        portfolio_reward = portfolio_change * 0.1
        
        total_reward = position_reward + transaction_penalty + risk_penalty + portfolio_reward
        
        return total_reward
    
    def _update_portfolio_value(self):
        """Update portfolio value based on current position."""
        if self.current_step < len(self.data):
            current_price = self.data.iloc[self.current_step]['close']
            self.portfolio_value = self.balance + self.shares * current_price
    
    def _get_state(self) -> np.ndarray:
        """Get current state representation."""
        if self.current_step >= len(self.data):
            return np.zeros(10)  # Return zero state if out of bounds
        
        row = self.data.iloc[self.current_step]
        
        # Basic price features
        state = [
            row['close'] / row['open'] - 1,  # Price change
            row['high'] / row['close'] - 1,  # High to close ratio
            row['low'] / row['close'] - 1,   # Low to close ratio
            row['volume'] / self.data['volume'].mean() if 'volume' in self.data.columns else 1.0,  # Volume ratio
        ]
        
        # Technical indicators if available
        if 'rsi' in row:
            state.append(row['rsi'] / 100 - 0.5)  # Normalized RSI
        else:
            state.append(0)
        
        if 'macd' in row:
            state.append(np.tanh(row['macd'] * 100))  # Normalized MACD
        else:
            state.append(0)
        
        if 'sma_20' in row and 'close' in row:
            state.append(row['close'] / row['sma_20'] - 1)  # Price to SMA ratio
        else:
            state.append(0)
        
        # Portfolio state
        state.extend([
            self.position,  # Current position
            self.portfolio_value / self.initial_balance - 1,  # Portfolio return
            self.balance / self.portfolio_value,  # Cash ratio
        ])
        
        # Pad or truncate to fixed size
        while len(state) < 10:
            state.append(0)
        
        return np.array(state[:10], dtype=np.float32)


class DQNNetwork(nn.Module):
    """Deep Q-Network for trading."""
    
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 64):
        super(DQNNetwork, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        self.dropout = nn.Dropout(0.2)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x


class ReplayBuffer:
    """Experience replay buffer for DQN."""
    
    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        """Add experience to buffer."""
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size: int):
        """Sample batch of experiences."""
        batch = random.sample(self.buffer, min(batch_size, len(self.buffer)))
        state, action, reward, next_state, done = map(np.stack, zip(*batch))
        return state, action, reward, next_state, done
    
    def __len__(self):
        return len(self.buffer)


class TradingAgent:
    """Deep Q-Network trading agent."""
    
    def __init__(self, config: RLConfig):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for RL functionality")
        
        self.config = config
        self.device = torch.device("cuda" if config.use_gpu and torch.cuda.is_available() else "cpu")
        
        # Networks
        self.q_network = DQNNetwork(config.state_size, config.action_size, config.hidden_size).to(self.device)
        self.target_network = DQNNetwork(config.state_size, config.action_size, config.hidden_size).to(self.device)
        
        # Copy weights to target network
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Optimizer
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=config.learning_rate)
        
        # Experience replay
        self.memory = ReplayBuffer(config.memory_size)
        
        # Training state
        self.epsilon = config.epsilon
        self.step_count = 0
    
    def act(self, state: np.ndarray, training: bool = True) -> int:
        """Choose action using epsilon-greedy policy."""
        if training and random.random() < self.epsilon:
            return random.randrange(self.config.action_size)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        q_values = self.q_network(state_tensor)
        return q_values.argmax().item()
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay buffer."""
        self.memory.push(state, action, reward, next_state, done)
    
    def replay(self):
        """Train the network on a batch of experiences."""
        if len(self.memory) < self.config.batch_size:
            return
        
        # Sample batch
        states, actions, rewards, next_states, dones = self.memory.sample(self.config.batch_size)
        
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.BoolTensor(dones).to(self.device)
        
        # Current Q values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Next Q values from target network
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (self.config.gamma * next_q_values * ~dones)
        
        # Compute loss
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Update target network
        self.step_count += 1
        if self.step_count % self.config.target_update_frequency == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Decay epsilon
        if self.epsilon > self.config.epsilon_min:
            self.epsilon *= self.config.epsilon_decay
    
    def save(self, filepath: str):
        """Save model weights."""
        torch.save({
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'step_count': self.step_count
        }, filepath)
    
    def load(self, filepath: str):
        """Load model weights."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.step_count = checkpoint['step_count']


class RLEnvironment:
    """Wrapper for trading environment with RL-specific functionality."""
    
    def __init__(self, data: pd.DataFrame, config: RLConfig):
        self.env = TradingEnvironment(data)
        self.config = config
    
    def train_agent(self, agent: TradingAgent) -> Dict[str, List[float]]:
        """Train the RL agent."""
        scores = []
        portfolio_values = []
        
        for episode in range(self.config.episodes):
            state = self.env.reset()
            total_reward = 0
            
            for step in range(self.config.max_steps):
                action = agent.act(state, training=True)
                next_state, reward, done, info = self.env.step(action)
                
                agent.remember(state, action, reward, next_state, done)
                agent.replay()
                
                state = next_state
                total_reward += reward
                
                if done:
                    break
            
            scores.append(total_reward)
            portfolio_values.append(self.env.portfolio_value)
            
            if episode % 100 == 0:
                avg_score = np.mean(scores[-100:])
                avg_portfolio = np.mean(portfolio_values[-100:])
                logger.info(f"Episode {episode}, Avg Score: {avg_score:.2f}, Avg Portfolio: {avg_portfolio:.2f}")
        
        return {
            'scores': scores,
            'portfolio_values': portfolio_values
        }
    
    def evaluate_agent(self, agent: TradingAgent) -> Dict[str, Any]:
        """Evaluate trained agent."""
        state = self.env.reset()
        total_reward = 0
        actions_taken = []
        
        for step in range(self.config.max_steps):
            action = agent.act(state, training=False)
            next_state, reward, done, info = self.env.step(action)
            
            actions_taken.append(action)
            state = next_state
            total_reward += reward
            
            if done:
                break
        
        return {
            'total_reward': total_reward,
            'final_portfolio_value': self.env.portfolio_value,
            'portfolio_return': (self.env.portfolio_value - self.env.initial_balance) / self.env.initial_balance,
            'actions_taken': actions_taken,
            'portfolio_history': self.env.portfolio_history
        }


def create_trading_agent(config: Optional[RLConfig] = None) -> TradingAgent:
    """Factory function to create trading agent."""
    if config is None:
        config = RLConfig()
    return TradingAgent(config)


def create_rl_environment(data: pd.DataFrame, config: Optional[RLConfig] = None) -> RLEnvironment:
    """Factory function to create RL environment."""
    if config is None:
        config = RLConfig()
    return RLEnvironment(data, config)
