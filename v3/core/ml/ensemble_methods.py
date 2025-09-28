"""Ensemble methods for combining multiple ML models."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import logging
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Some ensemble methods may not work.")


@dataclass
class EnsembleConfig:
    """Configuration for ensemble methods."""
    base_models: List[str] = None
    voting_method: str = 'soft'  # 'hard', 'soft'
    stacking_method: str = 'linear'  # 'linear', 'nonlinear'
    meta_model: str = 'linear'  # 'linear', 'ridge', 'lasso', 'rf', 'gb'
    cv_folds: int = 5
    use_proba: bool = True
    random_state: int = 42


class BaseModel(ABC):
    """Abstract base class for ensemble models."""
    
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BaseModel':
        """Fit the model."""
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        pass
    
    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities (for classification)."""
        pass


class SklearnModel(BaseModel):
    """Wrapper for sklearn models."""
    
    def __init__(self, model, name: str = None):
        self.model = model
        self.name = name or model.__class__.__name__
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'SklearnModel':
        """Fit the sklearn model."""
        self.model.fit(X, y)
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)
        else:
            # For regression models, return normalized predictions
            predictions = self.predict(X)
            # Convert to probabilities (simple normalization)
            predictions_norm = (predictions - predictions.min()) / (predictions.max() - predictions.min() + 1e-8)
            return np.column_stack([1 - predictions_norm, predictions_norm])


class VotingEnsemble:
    """Voting ensemble for combining multiple models."""
    
    def __init__(self, models: List[BaseModel], voting: str = 'soft', weights: Optional[List[float]] = None):
        self.models = models
        self.voting = voting
        self.weights = weights or [1.0] * len(models)
        self.is_fitted = False
        
        if len(self.weights) != len(self.models):
            raise ValueError("Number of weights must match number of models")
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'VotingEnsemble':
        """Fit all models in the ensemble."""
        for model in self.models:
            model.fit(X, y)
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using voting."""
        if not self.is_fitted:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        if self.voting == 'hard':
            return self._hard_voting(X)
        else:
            return self._soft_voting(X)
    
    def _hard_voting(self, X: np.ndarray) -> np.ndarray:
        """Hard voting: majority vote."""
        predictions = np.array([model.predict(X) for model in self.models])
        
        # For regression, use weighted average
        if predictions.ndim == 1:
            return np.average(predictions, axis=0, weights=self.weights)
        
        # For classification, use majority vote
        final_predictions = []
        for i in range(predictions.shape[1]):
            votes = predictions[:, i]
            unique, counts = np.unique(votes, return_counts=True)
            weighted_counts = np.zeros(len(unique))
            for j, vote in enumerate(votes):
                idx = np.where(unique == vote)[0][0]
                weighted_counts[idx] += self.weights[j]
            final_predictions.append(unique[np.argmax(weighted_counts)])
        
        return np.array(final_predictions)
    
    def _soft_voting(self, X: np.ndarray) -> np.ndarray:
        """Soft voting: weighted average of probabilities."""
        predictions = np.array([model.predict_proba(X) for model in self.models])
        
        # Weighted average of probabilities
        weighted_predictions = np.average(predictions, axis=0, weights=self.weights)
        
        # For regression, return the weighted average
        if weighted_predictions.ndim == 1:
            return weighted_predictions
        
        # For classification, return class with highest probability
        return np.argmax(weighted_predictions, axis=1)


class StackingEnsemble:
    """Stacking ensemble with meta-learner."""
    
    def __init__(self, base_models: List[BaseModel], meta_model: BaseModel, cv_folds: int = 5):
        self.base_models = base_models
        self.meta_model = meta_model
        self.cv_folds = cv_folds
        self.is_fitted = False
        self.kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'StackingEnsemble':
        """Fit the stacking ensemble."""
        # Generate meta-features using cross-validation
        meta_features = self._generate_meta_features(X, y)
        
        # Fit meta-model
        self.meta_model.fit(meta_features, y)
        
        # Fit base models on full data
        for model in self.base_models:
            model.fit(X, y)
        
        self.is_fitted = True
        return self
    
    def _generate_meta_features(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Generate meta-features using cross-validation."""
        meta_features = np.zeros((X.shape[0], len(self.base_models)))
        
        for fold, (train_idx, val_idx) in enumerate(self.kfold.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train = y[train_idx]
            
            for i, model in enumerate(self.base_models):
                # Fit model on training fold
                model.fit(X_train, y_train)
                
                # Predict on validation fold
                predictions = model.predict(X_val)
                meta_features[val_idx, i] = predictions
        
        return meta_features
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using stacking."""
        if not self.is_fitted:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        # Generate meta-features
        meta_features = np.column_stack([model.predict(X) for model in self.base_models])
        
        # Predict using meta-model
        return self.meta_model.predict(meta_features)


class EnsemblePredictor:
    """Main ensemble predictor class."""
    
    def __init__(self, config: EnsembleConfig):
        self.config = config
        self.ensemble = None
        self.is_fitted = False
        self.feature_names = None
    
    def _create_base_models(self) -> List[BaseModel]:
        """Create base models based on configuration."""
        models = []
        
        if self.config.base_models is None:
            self.config.base_models = ['linear', 'ridge', 'rf', 'gb']
        
        for model_name in self.config.base_models:
            if model_name == 'linear':
                models.append(SklearnModel(LinearRegression(), 'LinearRegression'))
            elif model_name == 'ridge':
                models.append(SklearnModel(Ridge(alpha=1.0), 'Ridge'))
            elif model_name == 'lasso':
                models.append(SklearnModel(Lasso(alpha=0.1), 'Lasso'))
            elif model_name == 'rf':
                models.append(SklearnModel(RandomForestRegressor(n_estimators=100, random_state=42), 'RandomForest'))
            elif model_name == 'gb':
                models.append(SklearnModel(GradientBoostingRegressor(n_estimators=100, random_state=42), 'GradientBoosting'))
            else:
                logger.warning(f"Unknown model type: {model_name}")
        
        return models
    
    def _create_meta_model(self) -> BaseModel:
        """Create meta-model for stacking."""
        if self.config.meta_model == 'linear':
            return SklearnModel(LinearRegression(), 'MetaLinear')
        elif self.config.meta_model == 'ridge':
            return SklearnModel(Ridge(alpha=1.0), 'MetaRidge')
        elif self.config.meta_model == 'lasso':
            return SklearnModel(Lasso(alpha=0.1), 'MetaLasso')
        elif self.config.meta_model == 'rf':
            return SklearnModel(RandomForestRegressor(n_estimators=50, random_state=42), 'MetaRF')
        elif self.config.meta_model == 'gb':
            return SklearnModel(GradientBoostingRegressor(n_estimators=50, random_state=42), 'MetaGB')
        else:
            return SklearnModel(LinearRegression(), 'MetaLinear')
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'EnsemblePredictor':
        """Fit the ensemble model."""
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X = X.values
        
        if isinstance(y, pd.Series):
            y = y.values
        
        # Create base models
        base_models = self._create_base_models()
        
        if self.config.stacking_method == 'linear':
            # Use stacking ensemble
            meta_model = self._create_meta_model()
            self.ensemble = StackingEnsemble(base_models, meta_model, self.config.cv_folds)
        else:
            # Use voting ensemble
            self.ensemble = VotingEnsemble(
                base_models, 
                voting=self.config.voting_method,
                weights=[1.0] * len(base_models)
            )
        
        # Fit ensemble
        self.ensemble.fit(X, y)
        self.is_fitted = True
        
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        return self.ensemble.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        if hasattr(self.ensemble, 'predict_proba'):
            return self.ensemble.predict_proba(X)
        else:
            # For regression, convert predictions to probabilities
            predictions = self.predict(X)
            predictions_norm = (predictions - predictions.min()) / (predictions.max() - predictions.min() + 1e-8)
            return np.column_stack([1 - predictions_norm, predictions_norm])
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Evaluate ensemble performance."""
        predictions = self.predict(X)
        
        mse = mean_squared_error(y, predictions)
        mae = mean_absolute_error(y, predictions)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, predictions)
        
        return {
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'r2': r2
        }
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance if available."""
        if not self.is_fitted or self.feature_names is None:
            return None
        
        # Try to get feature importance from meta-model
        if hasattr(self.ensemble, 'meta_model') and hasattr(self.ensemble.meta_model, 'model'):
            if hasattr(self.ensemble.meta_model.model, 'feature_importances_'):
                importance = self.ensemble.meta_model.model.feature_importances_
                return dict(zip(self.feature_names, importance))
            elif hasattr(self.ensemble.meta_model.model, 'coef_'):
                coef = self.ensemble.meta_model.model.coef_
                if coef.ndim == 1:
                    return dict(zip(self.feature_names, coef))
        
        return None


class AdaptiveEnsemble:
    """Adaptive ensemble that adjusts weights based on performance."""
    
    def __init__(self, models: List[BaseModel], learning_rate: float = 0.01):
        self.models = models
        self.learning_rate = learning_rate
        self.weights = np.ones(len(models)) / len(models)
        self.performance_history = []
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'AdaptiveEnsemble':
        """Fit all models and initialize weights."""
        for model in self.models:
            model.fit(X, y)
        self.is_fitted = True
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with adaptive weights."""
        if not self.is_fitted:
            raise ValueError("Ensemble must be fitted before making predictions")
        
        predictions = np.array([model.predict(X) for model in self.models])
        weighted_predictions = np.average(predictions, axis=0, weights=self.weights)
        
        return weighted_predictions
    
    def update_weights(self, X: np.ndarray, y: np.ndarray):
        """Update model weights based on recent performance."""
        if not self.is_fitted:
            return
        
        # Get predictions from all models
        predictions = np.array([model.predict(X) for model in self.models])
        
        # Calculate errors for each model
        errors = []
        for pred in predictions:
            error = mean_squared_error(y, pred)
            errors.append(error)
        
        # Update weights inversely proportional to error
        errors = np.array(errors)
        if errors.sum() > 0:
            inverse_errors = 1.0 / (errors + 1e-8)
            new_weights = inverse_errors / inverse_errors.sum()
            
            # Smooth weight update
            self.weights = (1 - self.learning_rate) * self.weights + self.learning_rate * new_weights
        
        # Store performance
        self.performance_history.append(errors.tolist())


def create_ensemble_predictor(config: Optional[EnsembleConfig] = None) -> EnsemblePredictor:
    """Factory function to create ensemble predictor."""
    if config is None:
        config = EnsembleConfig()
    return EnsemblePredictor(config)


def create_adaptive_ensemble(models: List[BaseModel], learning_rate: float = 0.01) -> AdaptiveEnsemble:
    """Factory function to create adaptive ensemble."""
    return AdaptiveEnsemble(models, learning_rate)


def compare_ensemble_methods(X: np.ndarray, y: np.ndarray, 
                           configs: List[EnsembleConfig] = None) -> pd.DataFrame:
    """Compare different ensemble methods."""
    if configs is None:
        configs = [
            EnsembleConfig(voting_method='hard', stacking_method='linear'),
            EnsembleConfig(voting_method='soft', stacking_method='linear'),
            EnsembleConfig(voting_method='soft', stacking_method='nonlinear'),
        ]
    
    results = []
    
    for i, config in enumerate(configs):
        try:
            ensemble = create_ensemble_predictor(config)
            ensemble.fit(X, y)
            metrics = ensemble.evaluate(X, y)
            
            results.append({
                'method': f'Config_{i+1}',
                'voting': config.voting_method,
                'stacking': config.stacking_method,
                'meta_model': config.meta_model,
                **metrics
            })
        except Exception as e:
            logger.warning(f"Failed to evaluate config {i+1}: {e}")
    
    return pd.DataFrame(results)
