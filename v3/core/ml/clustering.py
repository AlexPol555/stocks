"""Stock clustering for portfolio optimization and market segmentation."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import logging
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, calinski_harabasz_score
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


@dataclass
class ClusteringConfig:
    """Configuration for clustering algorithms."""
    algorithm: str = 'kmeans'  # 'kmeans', 'dbscan', 'hierarchical'
    n_clusters: int = 5
    random_state: int = 42
    min_samples: int = 5  # For DBSCAN
    eps: float = 0.5  # For DBSCAN
    linkage: str = 'ward'  # For hierarchical
    scaler: str = 'standard'  # 'standard', 'minmax', 'none'
    use_pca: bool = False
    pca_components: Optional[int] = None


@dataclass
class ClusteringResult:
    """Result of clustering analysis."""
    labels: np.ndarray
    n_clusters: int
    silhouette_score: float
    calinski_harabasz_score: float
    cluster_centers: Optional[np.ndarray]
    cluster_stats: Dict[int, Dict[str, float]]
    feature_importance: Optional[Dict[str, float]]


class StockClusterer:
    """Advanced stock clustering for portfolio optimization."""
    
    def __init__(self, config: ClusteringConfig):
        self.config = config
        self.scaler = None
        self.pca = None
        self.clusterer = None
        self.feature_names = None
        self.is_fitted = False
    
    def _prepare_features(self, data: pd.DataFrame, 
                         price_columns: List[str] = None,
                         volume_columns: List[str] = None,
                         technical_indicators: List[str] = None) -> np.ndarray:
        """Prepare features for clustering."""
        if price_columns is None:
            price_columns = ['open', 'high', 'low', 'close']
        
        if volume_columns is None:
            volume_columns = ['volume']
        
        if technical_indicators is None:
            technical_indicators = [
                'sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi', 'macd',
                'bb_upper', 'bb_lower', 'bb_middle', 'atr', 'stoch_k', 'stoch_d'
            ]
        
        # Collect all available features
        all_features = price_columns + volume_columns + technical_indicators
        available_features = [col for col in all_features if col in data.columns]
        
        if not available_features:
            raise ValueError("No valid features found in the data")
        
        # Calculate additional features
        features_df = data[available_features].copy()
        
        # Add price-based features
        if 'close' in features_df.columns:
            # Price volatility (rolling standard deviation)
            if len(features_df) > 20:
                features_df['price_volatility'] = features_df['close'].rolling(20).std()
            
            # Price momentum (rate of change)
            if len(features_df) > 5:
                features_df['price_momentum_5'] = features_df['close'].pct_change(5)
            if len(features_df) > 20:
                features_df['price_momentum_20'] = features_df['close'].pct_change(20)
        
        # Add volume-based features
        if 'volume' in features_df.columns:
            # Volume volatility
            if len(features_df) > 20:
                features_df['volume_volatility'] = features_df['volume'].rolling(20).std()
            
            # Volume momentum
            if len(features_df) > 5:
                features_df['volume_momentum'] = features_df['volume'].pct_change(5)
        
        # Add technical indicator features
        if 'rsi' in features_df.columns:
            # RSI momentum
            if len(features_df) > 5:
                features_df['rsi_momentum'] = features_df['rsi'].diff(5)
        
        if 'macd' in features_df.columns:
            # MACD momentum
            if len(features_df) > 5:
                features_df['macd_momentum'] = features_df['macd'].diff(5)
        
        # Fill NaN values
        features_df = features_df.ffill().bfill().fillna(0)
        
        # Store feature names
        self.feature_names = features_df.columns.tolist()
        
        return features_df.values
    
    def _create_clusterer(self, n_features: int):
        """Create clustering algorithm based on config."""
        if self.config.algorithm == 'kmeans':
            return KMeans(
                n_clusters=self.config.n_clusters,
                random_state=self.config.random_state,
                n_init=10
            )
        elif self.config.algorithm == 'dbscan':
            return DBSCAN(
                eps=self.config.eps,
                min_samples=self.config.min_samples
            )
        elif self.config.algorithm == 'hierarchical':
            return AgglomerativeClustering(
                n_clusters=self.config.n_clusters,
                linkage=self.config.linkage
            )
        else:
            raise ValueError(f"Unknown clustering algorithm: {self.config.algorithm}")
    
    def fit(self, data: pd.DataFrame, **kwargs) -> ClusteringResult:
        """Fit clustering model to data."""
        # Prepare features
        X = self._prepare_features(data, **kwargs)
        
        # Scale features
        if self.config.scaler == 'standard':
            self.scaler = StandardScaler()
        elif self.config.scaler == 'minmax':
            self.scaler = MinMaxScaler()
        else:
            self.scaler = None
        
        if self.scaler:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = X
        
        # Apply PCA if requested
        if self.config.use_pca:
            n_components = self.config.pca_components or min(X_scaled.shape[1], 10)
            self.pca = PCA(n_components=n_components)
            X_scaled = self.pca.fit_transform(X_scaled)
            logger.info(f"PCA explained variance ratio: {self.pca.explained_variance_ratio_}")
        
        # Create and fit clusterer
        self.clusterer = self._create_clusterer(X_scaled.shape[1])
        labels = self.clusterer.fit_predict(X_scaled)
        
        # Calculate metrics
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        if n_clusters > 1:
            silhouette_avg = silhouette_score(X_scaled, labels)
            calinski_harabasz = calinski_harabasz_score(X_scaled, labels)
        else:
            silhouette_avg = -1
            calinski_harabasz = 0
        
        # Calculate cluster statistics
        cluster_stats = self._calculate_cluster_stats(X, labels)
        
        # Calculate feature importance
        feature_importance = self._calculate_feature_importance(X_scaled, labels)
        
        self.is_fitted = True
        
        return ClusteringResult(
            labels=labels,
            n_clusters=n_clusters,
            silhouette_score=silhouette_avg,
            calinski_harabasz_score=calinski_harabasz,
            cluster_centers=getattr(self.clusterer, 'cluster_centers_', None),
            cluster_stats=cluster_stats,
            feature_importance=feature_importance
        )
    
    def _calculate_cluster_stats(self, X: np.ndarray, labels: np.ndarray) -> Dict[int, Dict[str, float]]:
        """Calculate statistics for each cluster."""
        stats = {}
        unique_labels = np.unique(labels)
        
        for label in unique_labels:
            if label == -1:  # Skip noise points in DBSCAN
                continue
            
            mask = labels == label
            cluster_data = X[mask]
            
            if len(cluster_data) == 0:
                continue
            
            stats[label] = {
                'size': len(cluster_data),
                'mean': np.mean(cluster_data, axis=0).tolist(),
                'std': np.std(cluster_data, axis=0).tolist(),
                'min': np.min(cluster_data, axis=0).tolist(),
                'max': np.max(cluster_data, axis=0).tolist()
            }
        
        return stats
    
    def _calculate_feature_importance(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """Calculate feature importance for clustering."""
        if self.feature_names is None:
            return None
        
        importance = {}
        unique_labels = np.unique(labels)
        
        for i, feature_name in enumerate(self.feature_names):
            if i >= X.shape[1]:
                break
            
            feature_values = X[:, i]
            feature_importance = 0
            
            for label in unique_labels:
                if label == -1:  # Skip noise points
                    continue
                
                mask = labels == label
                cluster_values = feature_values[mask]
                
                if len(cluster_values) > 1:
                    # Calculate variance within cluster
                    within_var = np.var(cluster_values)
                    # Calculate variance between clusters
                    between_var = np.var(feature_values)
                    
                    if between_var > 0:
                        feature_importance += (between_var - within_var) / between_var
            
            importance[feature_name] = feature_importance / max(1, len(unique_labels) - 1)
        
        return importance
    
    def predict(self, data: pd.DataFrame, **kwargs) -> np.ndarray:
        """Predict cluster labels for new data."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        X = self._prepare_features(data, **kwargs)
        
        if self.scaler:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X
        
        if self.pca:
            X_scaled = self.pca.transform(X_scaled)
        
        return self.clusterer.predict(X_scaled)
    
    def get_cluster_summary(self, result: ClusteringResult, 
                           data: pd.DataFrame) -> pd.DataFrame:
        """Get summary of clusters with original data."""
        summary_data = []
        
        for cluster_id in range(result.n_clusters):
            mask = result.labels == cluster_id
            cluster_data = data[mask]
            
            if len(cluster_data) == 0:
                continue
            
            summary = {
                'cluster_id': cluster_id,
                'size': len(cluster_data),
                'percentage': len(cluster_data) / len(data) * 100
            }
            
            # Add mean values for key features
            if 'close' in cluster_data.columns:
                summary['avg_close'] = cluster_data['close'].mean()
                summary['close_std'] = cluster_data['close'].std()
            
            if 'volume' in cluster_data.columns:
                summary['avg_volume'] = cluster_data['volume'].mean()
                summary['volume_std'] = cluster_data['volume'].std()
            
            if 'rsi' in cluster_data.columns:
                summary['avg_rsi'] = cluster_data['rsi'].mean()
            
            if 'macd' in cluster_data.columns:
                summary['avg_macd'] = cluster_data['macd'].mean()
            
            summary_data.append(summary)
        
        return pd.DataFrame(summary_data)
    
    def plot_clusters(self, result: ClusteringResult, 
                     data: pd.DataFrame,
                     feature1: str = 'close',
                     feature2: str = 'volume',
                     save_path: Optional[str] = None):
        """Plot clusters in 2D space."""
        if feature1 not in data.columns or feature2 not in data.columns:
            logger.warning(f"Features {feature1} or {feature2} not found in data")
            return
        
        plt.figure(figsize=(10, 8))
        
        unique_labels = np.unique(result.labels)
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_labels)))
        
        for label, color in zip(unique_labels, colors):
            if label == -1:  # Noise points
                mask = result.labels == label
                plt.scatter(data[feature1][mask], data[feature2][mask], 
                           c='black', marker='x', s=50, alpha=0.6, label='Noise')
            else:
                mask = result.labels == label
                plt.scatter(data[feature1][mask], data[feature2][mask], 
                           c=[color], s=50, alpha=0.7, label=f'Cluster {label}')
        
        plt.xlabel(feature1)
        plt.ylabel(feature2)
        plt.title(f'Stock Clustering ({self.config.algorithm.upper()})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()


def find_optimal_clusters(data: pd.DataFrame, 
                         max_clusters: int = 10,
                         algorithm: str = 'kmeans',
                         **kwargs) -> Dict[str, Union[int, float]]:
    """Find optimal number of clusters using elbow method and silhouette analysis."""
    config = ClusteringConfig(algorithm=algorithm, **kwargs)
    clusterer = StockClusterer(config)
    
    X = clusterer._prepare_features(data)
    
    if config.scaler == 'standard':
        scaler = StandardScaler()
    elif config.scaler == 'minmax':
        scaler = MinMaxScaler()
    else:
        scaler = None
    
    if scaler:
        X_scaled = scaler.fit_transform(X)
    else:
        X_scaled = X
    
    if config.use_pca:
        n_components = config.pca_components or min(X_scaled.shape[1], 10)
        pca = PCA(n_components=n_components)
        X_scaled = pca.fit_transform(X_scaled)
    
    inertias = []
    silhouette_scores = []
    k_range = range(2, min(max_clusters + 1, len(data) // 2))
    
    for k in k_range:
        if algorithm == 'kmeans':
            kmeans = KMeans(n_clusters=k, random_state=config.random_state, n_init=10)
            labels = kmeans.fit_predict(X_scaled)
            inertias.append(kmeans.inertia_)
        elif algorithm == 'hierarchical':
            hierarchical = AgglomerativeClustering(n_clusters=k, linkage=config.linkage)
            labels = hierarchical.fit_predict(X_scaled)
            inertias.append(0)  # Not applicable for hierarchical
        else:
            continue
        
        if k > 1:
            silhouette_avg = silhouette_score(X_scaled, labels)
            silhouette_scores.append(silhouette_avg)
        else:
            silhouette_scores.append(-1)
    
    # Find optimal k using silhouette score
    optimal_k = k_range[np.argmax(silhouette_scores)]
    max_silhouette = max(silhouette_scores)
    
    return {
        'optimal_clusters': optimal_k,
        'max_silhouette_score': max_silhouette,
        'k_range': list(k_range),
        'silhouette_scores': silhouette_scores,
        'inertias': inertias
    }


def create_clusterer(config: Optional[ClusteringConfig] = None) -> StockClusterer:
    """Factory function to create stock clusterer."""
    if config is None:
        config = ClusteringConfig()
    return StockClusterer(config)
