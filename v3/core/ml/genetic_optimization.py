"""Genetic algorithms for trading strategy optimization."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass
import logging
import random
from abc import ABC, abstractmethod
import copy

logger = logging.getLogger(__name__)


@dataclass
class GeneticConfig:
    """Configuration for genetic algorithm."""
    population_size: int = 100
    generations: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    elite_size: int = 10
    tournament_size: int = 5
    random_state: Optional[int] = None
    early_stopping_patience: int = 10
    convergence_threshold: float = 1e-6


@dataclass
class OptimizationResult:
    """Result of genetic optimization."""
    best_individual: Dict[str, float]
    best_fitness: float
    generation: int
    fitness_history: List[float]
    population_diversity: List[float]
    convergence_generation: Optional[int]


class Individual:
    """Represents a single individual in the genetic algorithm."""
    
    def __init__(self, parameters: Dict[str, Tuple[float, float]], 
                 values: Optional[Dict[str, float]] = None):
        self.parameters = parameters
        self.fitness = -np.inf
        self.generation = 0
        
        if values is None:
            self.values = self._randomize_parameters()
        else:
            self.values = values.copy()
    
    def _randomize_parameters(self) -> Dict[str, float]:
        """Randomize parameter values within bounds."""
        values = {}
        for param, (min_val, max_val) in self.parameters.items():
            values[param] = random.uniform(min_val, max_val)
        return values
    
    def mutate(self, mutation_rate: float, mutation_strength: float = 0.1):
        """Apply mutation to the individual."""
        for param in self.values:
            if random.random() < mutation_rate:
                min_val, max_val = self.parameters[param]
                current_val = self.values[param]
                
                # Gaussian mutation
                mutation = np.random.normal(0, mutation_strength * (max_val - min_val))
                new_val = current_val + mutation
                
                # Ensure bounds
                self.values[param] = max(min_val, min(max_val, new_val))
    
    def crossover(self, other: 'Individual', crossover_rate: float) -> Tuple['Individual', 'Individual']:
        """Perform crossover with another individual."""
        if random.random() > crossover_rate:
            return Individual(self.parameters, self.values), Individual(self.parameters, other.values)
        
        child1_values = {}
        child2_values = {}
        
        for param in self.values:
            if random.random() < 0.5:
                child1_values[param] = self.values[param]
                child2_values[param] = other.values[param]
            else:
                child1_values[param] = other.values[param]
                child2_values[param] = self.values[param]
        
        child1 = Individual(self.parameters, child1_values)
        child2 = Individual(self.parameters, child2_values)
        
        return child1, child2
    
    def copy(self) -> 'Individual':
        """Create a copy of the individual."""
        return Individual(self.parameters, self.values)


class FitnessFunction(ABC):
    """Abstract base class for fitness functions."""
    
    @abstractmethod
    def evaluate(self, individual: Individual, data: pd.DataFrame) -> float:
        """Evaluate fitness of an individual."""
        pass


class TradingStrategyFitness(FitnessFunction):
    """Fitness function for trading strategy optimization."""
    
    def __init__(self, 
                 data: pd.DataFrame,
                 target_metric: str = 'sharpe_ratio',
                 risk_free_rate: float = 0.02,
                 transaction_cost: float = 0.001):
        self.data = data
        self.target_metric = target_metric
        self.risk_free_rate = risk_free_rate
        self.transaction_cost = transaction_cost
    
    def evaluate(self, individual: Individual, data: pd.DataFrame) -> float:
        """Evaluate trading strategy fitness."""
        try:
            # Extract strategy parameters
            params = individual.values
            
            # Generate trading signals based on parameters
            signals = self._generate_signals(data, params)
            
            # Calculate returns
            returns = self._calculate_returns(data, signals)
            
            # Calculate fitness metric
            if self.target_metric == 'sharpe_ratio':
                return self._calculate_sharpe_ratio(returns)
            elif self.target_metric == 'max_drawdown':
                return -self._calculate_max_drawdown(returns)  # Negative because we want to minimize
            elif self.target_metric == 'profit_factor':
                return self._calculate_profit_factor(returns)
            elif self.target_metric == 'total_return':
                return self._calculate_total_return(returns)
            else:
                return self._calculate_sharpe_ratio(returns)
        
        except Exception as e:
            logger.warning(f"Fitness evaluation failed: {e}")
            return -np.inf
    
    def _generate_signals(self, data: pd.DataFrame, params: Dict[str, float]) -> pd.Series:
        """Generate trading signals based on parameters."""
        signals = pd.Series(0, index=data.index)
        
        # Simple moving average crossover strategy
        if 'sma_short' in params and 'sma_long' in params:
            sma_short = data['close'].rolling(int(params['sma_short'])).mean()
            sma_long = data['close'].rolling(int(params['sma_long'])).mean()
            
            # Buy signal when short MA crosses above long MA
            signals[(sma_short > sma_long) & (sma_short.shift(1) <= sma_long.shift(1))] = 1
            # Sell signal when short MA crosses below long MA
            signals[(sma_short < sma_long) & (sma_short.shift(1) >= sma_long.shift(1))] = -1
        
        # RSI strategy
        if 'rsi_threshold' in params and 'rsi' in data.columns:
            rsi = data['rsi']
            rsi_threshold = params['rsi_threshold']
            
            # Buy when RSI is oversold
            signals[(rsi < 30) & (rsi.shift(1) >= 30)] = 1
            # Sell when RSI is overbought
            signals[(rsi > 70) & (rsi.shift(1) <= 70)] = -1
        
        # MACD strategy
        if 'macd_threshold' in params and 'macd' in data.columns:
            macd = data['macd']
            macd_threshold = params['macd_threshold']
            
            # Buy when MACD crosses above threshold
            signals[(macd > macd_threshold) & (macd.shift(1) <= macd_threshold)] = 1
            # Sell when MACD crosses below threshold
            signals[(macd < -macd_threshold) & (macd.shift(1) >= -macd_threshold)] = -1
        
        return signals
    
    def _calculate_returns(self, data: pd.DataFrame, signals: pd.Series) -> pd.Series:
        """Calculate strategy returns."""
        price_changes = data['close'].pct_change()
        strategy_returns = signals.shift(1) * price_changes
        
        # Apply transaction costs
        signal_changes = signals.diff().abs()
        transaction_costs = signal_changes * self.transaction_cost
        strategy_returns -= transaction_costs
        
        return strategy_returns.fillna(0)
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) == 0 or returns.std() == 0:
            return 0
        
        excess_returns = returns - self.risk_free_rate / 252  # Daily risk-free rate
        return excess_returns.mean() / returns.std() * np.sqrt(252)
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _calculate_profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor."""
        positive_returns = returns[returns > 0].sum()
        negative_returns = abs(returns[returns < 0].sum())
        
        if negative_returns == 0:
            return float('inf') if positive_returns > 0 else 0
        
        return positive_returns / negative_returns
    
    def _calculate_total_return(self, returns: pd.Series) -> float:
        """Calculate total return."""
        return (1 + returns).prod() - 1


class GeneticOptimizer:
    """Genetic algorithm optimizer for trading strategies."""
    
    def __init__(self, config: GeneticConfig, fitness_function: FitnessFunction):
        self.config = config
        self.fitness_function = fitness_function
        self.population = []
        self.fitness_history = []
        self.diversity_history = []
        self.best_individual = None
        self.best_fitness = -np.inf
        
        if config.random_state is not None:
            random.seed(config.random_state)
            np.random.seed(config.random_state)
    
    def optimize(self, parameters: Dict[str, Tuple[float, float]], 
                 data: pd.DataFrame) -> OptimizationResult:
        """Run genetic algorithm optimization."""
        # Initialize population
        self._initialize_population(parameters)
        
        # Track convergence
        best_fitness_history = []
        convergence_generation = None
        
        for generation in range(self.config.generations):
            # Evaluate fitness
            self._evaluate_fitness(data)
            
            # Track best individual
            current_best = max(self.population, key=lambda x: x.fitness)
            if current_best.fitness > self.best_fitness:
                self.best_fitness = current_best.fitness
                self.best_individual = current_best.copy()
            
            best_fitness_history.append(self.best_fitness)
            self.fitness_history.append(self.best_fitness)
            
            # Calculate population diversity
            diversity = self._calculate_diversity()
            self.diversity_history.append(diversity)
            
            # Check convergence
            if len(best_fitness_history) >= self.config.early_stopping_patience:
                recent_improvement = max(best_fitness_history[-self.config.early_stopping_patience:]) - min(best_fitness_history[-self.config.early_stopping_patience:])
                if recent_improvement < self.config.convergence_threshold:
                    convergence_generation = generation
                    logger.info(f"Convergence reached at generation {generation}")
                    break
            
            # Create next generation
            self._evolve_generation()
            
            if generation % 10 == 0:
                logger.info(f"Generation {generation}: Best fitness = {self.best_fitness:.6f}, Diversity = {diversity:.6f}")
        
        return OptimizationResult(
            best_individual=self.best_individual.values,
            best_fitness=self.best_fitness,
            generation=generation,
            fitness_history=self.fitness_history,
            population_diversity=self.diversity_history,
            convergence_generation=convergence_generation
        )
    
    def _initialize_population(self, parameters: Dict[str, Tuple[float, float]]):
        """Initialize population with random individuals."""
        self.population = []
        for _ in range(self.config.population_size):
            individual = Individual(parameters)
            self.population.append(individual)
    
    def _evaluate_fitness(self, data: pd.DataFrame):
        """Evaluate fitness for all individuals in population."""
        for individual in self.population:
            individual.fitness = self.fitness_function.evaluate(individual, data)
    
    def _calculate_diversity(self) -> float:
        """Calculate population diversity."""
        if len(self.population) < 2:
            return 0
        
        # Calculate average pairwise distance
        total_distance = 0
        count = 0
        
        for i in range(len(self.population)):
            for j in range(i + 1, len(self.population)):
                distance = self._calculate_individual_distance(self.population[i], self.population[j])
                total_distance += distance
                count += 1
        
        return total_distance / count if count > 0 else 0
    
    def _calculate_individual_distance(self, ind1: Individual, ind2: Individual) -> float:
        """Calculate distance between two individuals."""
        distance = 0
        for param in ind1.values:
            if param in ind2.values:
                min_val, max_val = ind1.parameters[param]
                normalized_diff = abs(ind1.values[param] - ind2.values[param]) / (max_val - min_val)
                distance += normalized_diff ** 2
        
        return np.sqrt(distance)
    
    def _evolve_generation(self):
        """Create next generation through selection, crossover, and mutation."""
        new_population = []
        
        # Elitism: keep best individuals
        sorted_population = sorted(self.population, key=lambda x: x.fitness, reverse=True)
        for i in range(min(self.config.elite_size, len(sorted_population))):
            new_population.append(sorted_population[i].copy())
        
        # Generate offspring
        while len(new_population) < self.config.population_size:
            # Tournament selection
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()
            
            # Crossover
            child1, child2 = parent1.crossover(parent2, self.config.crossover_rate)
            
            # Mutation
            child1.mutate(self.config.mutation_rate)
            child2.mutate(self.config.mutation_rate)
            
            new_population.extend([child1, child2])
        
        # Trim to population size
        self.population = new_population[:self.config.population_size]
    
    def _tournament_selection(self) -> Individual:
        """Select individual using tournament selection."""
        tournament = random.sample(self.population, min(self.config.tournament_size, len(self.population)))
        return max(tournament, key=lambda x: x.fitness)


def optimize_trading_strategy(data: pd.DataFrame,
                            parameters: Dict[str, Tuple[float, float]],
                            target_metric: str = 'sharpe_ratio',
                            config: Optional[GeneticConfig] = None) -> OptimizationResult:
    """Optimize trading strategy using genetic algorithm."""
    if config is None:
        config = GeneticConfig()
    
    fitness_function = TradingStrategyFitness(data, target_metric)
    optimizer = GeneticOptimizer(config, fitness_function)
    
    return optimizer.optimize(parameters, data)


def create_parameter_space(strategy_type: str) -> Dict[str, Tuple[float, float]]:
    """Create parameter space for different strategy types."""
    if strategy_type == 'sma_crossover':
        return {
            'sma_short': (5, 50),
            'sma_long': (20, 200),
        }
    elif strategy_type == 'rsi':
        return {
            'rsi_threshold': (20, 40),
        }
    elif strategy_type == 'macd':
        return {
            'macd_threshold': (0.001, 0.01),
        }
    elif strategy_type == 'combined':
        return {
            'sma_short': (5, 50),
            'sma_long': (20, 200),
            'rsi_threshold': (20, 40),
            'macd_threshold': (0.001, 0.01),
        }
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")


def create_genetic_optimizer(config: Optional[GeneticConfig] = None) -> GeneticOptimizer:
    """Factory function to create genetic optimizer."""
    if config is None:
        config = GeneticConfig()
    
    # Create a dummy fitness function - will be replaced in optimize()
    class DummyFitness(FitnessFunction):
        def evaluate(self, individual, data):
            return 0
    
    return GeneticOptimizer(config, DummyFitness())
