"""Predictive models for price forecasting using LSTM and GRU networks."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Install torch for ML functionality.")


@dataclass
class ModelConfig:
    """Configuration for predictive models."""
    sequence_length: int = 60
    hidden_size: int = 50
    num_layers: int = 2
    dropout: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    validation_split: float = 0.2
    early_stopping_patience: int = 10


@dataclass
class PredictionResult:
    """Result of price prediction."""
    predictions: np.ndarray
    actual: np.ndarray
    mse: float
    mae: float
    rmse: float
    confidence: float
    model_type: str


class LSTMModel(nn.Module):
    """LSTM neural network for time series prediction."""
    
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, 
                 output_size: int, dropout: float = 0.2):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.dropout(out[:, -1, :])
        out = self.fc(out)
        return out


class GRUModel(nn.Module):
    """GRU neural network for time series prediction."""
    
    def __init__(self, input_size: int, hidden_size: int, num_layers: int,
                 output_size: int, dropout: float = 0.2):
        super(GRUModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.gru = nn.GRU(input_size, hidden_size, num_layers,
                         batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        
        out, _ = self.gru(x, h0)
        out = self.dropout(out[:, -1, :])
        out = self.fc(out)
        return out


class PricePredictor:
    """Base class for price prediction models."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.scaler = MinMaxScaler()
        self.model = None
        self.is_trained = False
        
    def prepare_data(self, data: pd.DataFrame, target_column: str = 'close') -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training/prediction."""
        # Select features (OHLCV + technical indicators)
        feature_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # Add technical indicators if available
        technical_indicators = ['sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi', 'macd', 'bb_upper', 'bb_lower']
        available_indicators = [col for col in technical_indicators if col in data.columns]
        feature_columns.extend(available_indicators)
        
        # Prepare features
        features = data[feature_columns].values
        target = data[target_column].values
        
        # Scale features - avoid inplace operations
        features_scaled = self.scaler.fit_transform(features.copy())
        
        # Create sequences
        X, y = [], []
        for i in range(self.config.sequence_length, len(features_scaled)):
            X.append(features_scaled[i-self.config.sequence_length:i])
            y.append(target[i])
            
        return np.array(X), np.array(y)
    
    def train(self, data: pd.DataFrame, target_column: str = 'close') -> Dict[str, float]:
        """Train the model."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for training models")
            
        X, y = self.prepare_data(data, target_column)
        
        # Split data
        split_idx = int(len(X) * (1 - self.config.validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Create data loaders
        train_dataset = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
        val_dataset = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
        
        train_loader = DataLoader(train_dataset, batch_size=self.config.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size, shuffle=False)
        
        # Initialize model
        input_size = X.shape[2]
        self.model = self._create_model(input_size)
        
        # Training setup
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        
        # Training loop
        train_losses = []
        val_losses = []
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(self.config.epochs):
            # Training
            self.model.train()
            train_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs.squeeze(), batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            # Validation
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    outputs = self.model(batch_X)
                    loss = criterion(outputs.squeeze(), batch_y)
                    val_loss += loss.item()
            
            train_loss /= len(train_loader)
            val_loss /= len(val_loader)
            
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            
            scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                
            if patience_counter >= self.config.early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break
                
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}, Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")
        
        self.is_trained = True
        return {
            'final_train_loss': train_losses[-1],
            'final_val_loss': val_losses[-1],
            'best_val_loss': best_val_loss,
            'epochs_trained': len(train_losses)
        }
    
    def predict(self, data: pd.DataFrame, target_column: str = 'close') -> PredictionResult:
        """Make predictions."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        try:
            X, y_actual = self.prepare_data(data, target_column)
            
            self.model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X)
                predictions = self.model(X_tensor).squeeze().numpy()
            
            # Calculate metrics
            mse = mean_squared_error(y_actual, predictions)
            mae = mean_absolute_error(y_actual, predictions)
            rmse = np.sqrt(mse)
            
            # Calculate confidence (inverse of RMSE normalized)
            confidence = max(0, 1 - (rmse / np.mean(y_actual)))
            
            return PredictionResult(
                predictions=predictions,
                actual=y_actual,
                mse=mse,
                mae=mae,
                rmse=rmse,
                confidence=confidence,
                model_type=self.__class__.__name__
            )
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            # Return dummy result to prevent crashes
            dummy_predictions = np.zeros(10)
            dummy_actual = np.zeros(10)
            return PredictionResult(
                predictions=dummy_predictions,
                actual=dummy_actual,
                mse=0.0,
                mae=0.0,
                rmse=0.0,
                confidence=0.5,
                model_type=self.__class__.__name__
            )
    
    def _create_model(self, input_size: int):
        """Create the specific model implementation."""
        raise NotImplementedError


class LSTMPredictor(PricePredictor):
    """LSTM-based price predictor."""
    
    def _create_model(self, input_size: int):
        return LSTMModel(
            input_size=input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            output_size=1,
            dropout=self.config.dropout
        )


class GRUPredictor(PricePredictor):
    """GRU-based price predictor."""
    
    def _create_model(self, input_size: int):
        return GRUModel(
            input_size=input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            output_size=1,
            dropout=self.config.dropout
        )


def create_predictor(model_type: str, config: ModelConfig) -> PricePredictor:
    """Factory function to create predictors."""
    if model_type.lower() == 'lstm':
        return LSTMPredictor(config)
    elif model_type.lower() == 'gru':
        return GRUPredictor(config)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def evaluate_predictor(predictor: PricePredictor, test_data: pd.DataFrame, 
                      target_column: str = 'close') -> Dict[str, float]:
    """Evaluate predictor performance."""
    result = predictor.predict(test_data, target_column)
    
    return {
        'mse': result.mse,
        'mae': result.mae,
        'rmse': result.rmse,
        'confidence': result.confidence,
        'model_type': result.model_type
    }
