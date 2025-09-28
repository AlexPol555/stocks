"""Advanced risk management system for automated trading."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.analytics.risk import TradeRecord, simulate_trades
from core.analytics.metrics import TradingCosts

logger = logging.getLogger(__name__)


@dataclass
class RiskProfile:
    """Risk management profile for automated trading."""
    max_position_size: float = 10000.0
    max_portfolio_risk: float = 0.05  # 5% of portfolio
    max_daily_loss: float = 0.02  # 2% daily loss limit
    max_drawdown: float = 0.10  # 10% maximum drawdown
    max_correlation: float = 0.7  # Maximum correlation between positions
    max_positions: int = 10  # Maximum number of open positions
    stop_loss_atr_multiplier: float = 2.0
    take_profit_atr_multiplier: float = 3.0
    trailing_stop_multiplier: float = 1.5
    max_holding_days: int = 5
    min_risk_reward_ratio: float = 1.5


@dataclass
class Position:
    """Represents an open trading position."""
    contract_code: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    entry_date: str
    stop_loss: float
    take_profit: float
    current_price: float
    unrealized_pnl: float
    atr: float
    risk_amount: float


class AdvancedRiskManager:
    """Advanced risk management system."""
    
    def __init__(self, risk_profile: Optional[RiskProfile] = None, 
                 trading_costs: Optional[TradingCosts] = None):
        self.risk_profile = risk_profile or RiskProfile()
        self.trading_costs = trading_costs or TradingCosts()
        self.positions: Dict[str, Position] = {}
        self.daily_pnl: float = 0.0
        self.portfolio_value: float = 1000000.0  # Default portfolio value
        self.max_portfolio_value: float = 1000000.0  # Track peak for drawdown calculation
    
    def can_open_position(self, contract_code: str, side: str, quantity: float, 
                         entry_price: float, atr: float) -> Tuple[bool, str]:
        """
        Check if a new position can be opened based on risk rules.
        
        Returns
        -------
        Tuple[bool, str]
            (can_open, reason)
        """
        # Check maximum number of positions
        if len(self.positions) >= self.risk_profile.max_positions:
            return False, "Maximum number of positions reached"
        
        # Check if position already exists for this contract
        if contract_code in self.positions:
            return False, "Position already exists for this contract"
        
        # Calculate position value
        position_value = quantity * entry_price
        
        # Check maximum position size
        if position_value > self.risk_profile.max_position_size:
            return False, f"Position size {position_value} exceeds maximum {self.risk_profile.max_position_size}"
        
        # Check portfolio risk
        risk_amount = self._calculate_risk_amount(entry_price, atr, side)
        portfolio_risk = risk_amount / self.portfolio_value
        
        if portfolio_risk > self.risk_profile.max_portfolio_risk:
            return False, f"Portfolio risk {portfolio_risk:.2%} exceeds maximum {self.risk_profile.max_portfolio_risk:.2%}"
        
        # Check daily loss limit
        if self.daily_pnl < -self.portfolio_value * self.risk_profile.max_daily_loss:
            return False, "Daily loss limit reached"
        
        # Check maximum drawdown
        current_drawdown = (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        if current_drawdown > self.risk_profile.max_drawdown:
            return False, f"Maximum drawdown {current_drawdown:.2%} exceeded"
        
        # Check correlation with existing positions
        if not self._check_correlation(contract_code):
            return False, "High correlation with existing positions"
        
        return True, "Position approved"
    
    def _calculate_risk_amount(self, entry_price: float, atr: float, side: str) -> float:
        """Calculate risk amount for a position."""
        if side == 'long':
            stop_loss = entry_price - (atr * self.risk_profile.stop_loss_atr_multiplier)
        else:
            stop_loss = entry_price + (atr * self.risk_profile.stop_loss_atr_multiplier)
        
        return abs(entry_price - stop_loss)
    
    def _check_correlation(self, contract_code: str) -> bool:
        """Check correlation with existing positions (simplified)."""
        # In a real implementation, this would calculate actual correlation
        # For now, we'll use a simple rule: no more than 2 positions in same sector
        if len(self.positions) < 2:
            return True
        
        # Simple heuristic: limit positions in similar contracts
        similar_contracts = 0
        for pos_contract in self.positions:
            if self._are_contracts_similar(contract_code, pos_contract):
                similar_contracts += 1
        
        return similar_contracts < 2
    
    def _are_contracts_similar(self, contract1: str, contract2: str) -> bool:
        """Check if two contracts are similar (simplified)."""
        # Simple heuristic based on contract code patterns
        if contract1 == contract2:
            return True
        
        # Check if they're in the same sector (simplified)
        sectors1 = self._get_contract_sector(contract1)
        sectors2 = self._get_contract_sector(contract2)
        
        return len(set(sectors1) & set(sectors2)) > 0
    
    def _get_contract_sector(self, contract_code: str) -> List[str]:
        """Get sector information for a contract (simplified)."""
        # This is a simplified implementation
        # In reality, you'd have a mapping of contracts to sectors
        if contract_code.startswith('SBER') or contract_code.startswith('VTB'):
            return ['banking']
        elif contract_code.startswith('GAZP') or contract_code.startswith('LKOH'):
            return ['energy']
        elif contract_code.startswith('NVTK') or contract_code.startswith('ROSN'):
            return ['oil_gas']
        else:
            return ['other']
    
    def add_position(self, contract_code: str, side: str, quantity: float, 
                    entry_price: float, entry_date: str, atr: float) -> bool:
        """Add a new position to the portfolio."""
        can_open, reason = self.can_open_position(contract_code, side, quantity, entry_price, atr)
        
        if not can_open:
            logger.warning(f"Cannot add position for {contract_code}: {reason}")
            return False
        
        # Calculate stop loss and take profit
        if side == 'long':
            stop_loss = entry_price - (atr * self.risk_profile.stop_loss_atr_multiplier)
            take_profit = entry_price + (atr * self.risk_profile.take_profit_atr_multiplier)
        else:
            stop_loss = entry_price + (atr * self.risk_profile.stop_loss_atr_multiplier)
            take_profit = entry_price - (atr * self.risk_profile.take_profit_atr_multiplier)
        
        # Calculate risk amount
        risk_amount = self._calculate_risk_amount(entry_price, atr, side)
        
        # Create position
        position = Position(
            contract_code=contract_code,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            entry_date=entry_date,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_price=entry_price,
            unrealized_pnl=0.0,
            atr=atr,
            risk_amount=risk_amount
        )
        
        self.positions[contract_code] = position
        
        # Update portfolio value
        self.portfolio_value -= quantity * entry_price
        
        logger.info(f"Added position: {contract_code} {side} {quantity} @ {entry_price}")
        return True
    
    def update_position_price(self, contract_code: str, current_price: float) -> bool:
        """Update current price for a position."""
        if contract_code not in self.positions:
            return False
        
        position = self.positions[contract_code]
        position.current_price = current_price
        
        # Calculate unrealized P&L
        if position.side == 'long':
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:
            position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
        
        # Update portfolio value
        self.portfolio_value += position.unrealized_pnl
        
        # Update maximum portfolio value for drawdown calculation
        if self.portfolio_value > self.max_portfolio_value:
            self.max_portfolio_value = self.portfolio_value
        
        return True
    
    def check_exit_signals(self) -> List[Tuple[str, str]]:
        """
        Check for exit signals on all positions.
        
        Returns
        -------
        List[Tuple[str, str]]
            List of (contract_code, exit_reason) tuples
        """
        exit_signals = []
        
        for contract_code, position in self.positions.items():
            # Check stop loss
            if self._check_stop_loss(position):
                exit_signals.append((contract_code, 'stop_loss'))
                continue
            
            # Check take profit
            if self._check_take_profit(position):
                exit_signals.append((contract_code, 'take_profit'))
                continue
            
            # Check time-based exit
            if self._check_time_exit(position):
                exit_signals.append((contract_code, 'time_exit'))
                continue
            
            # Check trailing stop
            if self._check_trailing_stop(position):
                exit_signals.append((contract_code, 'trailing_stop'))
                continue
        
        return exit_signals
    
    def _check_stop_loss(self, position: Position) -> bool:
        """Check if stop loss is triggered."""
        if position.side == 'long':
            return position.current_price <= position.stop_loss
        else:
            return position.current_price >= position.stop_loss
    
    def _check_take_profit(self, position: Position) -> bool:
        """Check if take profit is triggered."""
        if position.side == 'long':
            return position.current_price >= position.take_profit
        else:
            return position.current_price <= position.take_profit
    
    def _check_time_exit(self, position: Position) -> bool:
        """Check if position should be closed due to time limit."""
        from datetime import datetime, timedelta
        
        entry_date = datetime.strptime(position.entry_date, '%Y-%m-%d')
        days_held = (datetime.now() - entry_date).days
        
        return days_held >= self.risk_profile.max_holding_days
    
    def _check_trailing_stop(self, position: Position) -> bool:
        """Check if trailing stop is triggered."""
        if position.side == 'long':
            trailing_stop = position.current_price - (position.atr * self.risk_profile.trailing_stop_multiplier)
            if trailing_stop > position.stop_loss:
                position.stop_loss = trailing_stop
            return position.current_price <= position.stop_loss
        else:
            trailing_stop = position.current_price + (position.atr * self.risk_profile.trailing_stop_multiplier)
            if trailing_stop < position.stop_loss:
                position.stop_loss = trailing_stop
            return position.current_price >= position.stop_loss
    
    def close_position(self, contract_code: str, exit_price: float, exit_reason: str) -> Optional[Dict]:
        """Close a position and return trade summary."""
        if contract_code not in self.positions:
            return None
        
        position = self.positions[contract_code]
        
        # Calculate final P&L
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Calculate P&L percentage
        pnl_percent = pnl / (position.entry_price * position.quantity) * 100
        
        # Calculate holding days
        from datetime import datetime
        entry_date = datetime.strptime(position.entry_date, '%Y-%m-%d')
        holding_days = (datetime.now() - entry_date).days
        
        # Create trade summary
        trade_summary = {
            'contract_code': contract_code,
            'side': position.side,
            'quantity': position.quantity,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'holding_days': holding_days,
            'exit_reason': exit_reason,
            'entry_date': position.entry_date,
            'exit_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Update portfolio value
        self.portfolio_value += pnl
        self.daily_pnl += pnl
        
        # Remove position
        del self.positions[contract_code]
        
        logger.info(f"Closed position {contract_code}: P&L = {pnl:.2f} ({pnl_percent:.2f}%)")
        
        return trade_summary
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary."""
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_risk = sum(pos.risk_amount for pos in self.positions.values())
        
        # Calculate current drawdown
        current_drawdown = (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        
        return {
            'portfolio_value': self.portfolio_value,
            'max_portfolio_value': self.max_portfolio_value,
            'current_drawdown': current_drawdown,
            'daily_pnl': self.daily_pnl,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_risk': total_risk,
            'risk_percentage': total_risk / self.portfolio_value if self.portfolio_value > 0 else 0,
            'num_positions': len(self.positions),
            'max_positions': self.risk_profile.max_positions,
            'positions': [
                {
                    'contract_code': pos.contract_code,
                    'side': pos.side,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit
                }
                for pos in self.positions.values()
            ]
        }
    
    def reset_daily_pnl(self):
        """Reset daily P&L (call at start of new trading day)."""
        self.daily_pnl = 0.0
        logger.info("Reset daily P&L")
    
    def update_risk_profile(self, new_profile: RiskProfile):
        """Update risk management profile."""
        self.risk_profile = new_profile
        logger.info("Updated risk management profile")

