# Machine Learning & AI Guide

## Обзор

Модуль ML & AI предоставляет комплексные возможности машинного обучения для анализа рынка, прогнозирования цен и оптимизации торговых стратегий.

## Основные компоненты

### 1. Предиктивная аналитика (`core/ml/predictive_models.py`)

#### LSTM/GRU модели для прогнозирования цен
- **LSTMPredictor**: LSTM нейронная сеть для временных рядов
- **GRUPredictor**: GRU нейронная сеть для временных рядов
- **PricePredictor**: Базовый класс для предиктивных моделей

#### Использование:
```python
from core.ml import LSTMPredictor, ModelConfig

# Конфигурация модели
config = ModelConfig(
    sequence_length=60,
    hidden_size=50,
    epochs=100,
    batch_size=32
)

# Создание и обучение модели
predictor = LSTMPredictor(config)
training_result = predictor.train(data)
prediction = predictor.predict(data)
```

### 2. Анализ сентимента (`core/ml/sentiment_analysis.py`)

#### Анализ настроений новостей
- **NewsSentimentAnalyzer**: Анализатор сентимента новостей
- **LexiconSentimentAnalyzer**: Правило-основанный анализатор
- Поддержка transformer моделей

#### Использование:
```python
from core.ml import NewsSentimentAnalyzer, SentimentConfig

# Конфигурация
config = SentimentConfig(
    model_name="cardiffnlp/twitter-roberta-base-sentiment-latest",
    confidence_threshold=0.7
)

# Анализ сентимента
analyzer = NewsSentimentAnalyzer(config)
sentiment_result = analyzer.get_market_sentiment(news_data)
```

### 3. Кластеризация акций (`core/ml/clustering.py`)

#### Кластеризация для оптимизации портфеля
- **StockClusterer**: Кластеризация акций
- Поддержка K-means, DBSCAN, иерархической кластеризации
- Анализ важности признаков

#### Использование:
```python
from core.ml import StockClusterer, ClusteringConfig

# Конфигурация
config = ClusteringConfig(
    algorithm='kmeans',
    n_clusters=5,
    scaler='standard'
)

# Кластеризация
clusterer = StockClusterer(config)
result = clusterer.fit(data)
```

### 4. Генетические алгоритмы (`core/ml/genetic_optimization.py`)

#### Оптимизация торговых стратегий
- **GeneticOptimizer**: Генетический алгоритм
- **TradingStrategyFitness**: Функция приспособленности
- Поддержка различных стратегий

#### Использование:
```python
from core.ml import GeneticOptimizer, GeneticConfig, TradingStrategyFitness

# Параметры стратегии
parameters = {
    'sma_short': (5, 50),
    'sma_long': (20, 200),
    'rsi_threshold': (20, 40)
}

# Оптимизация
fitness_function = TradingStrategyFitness(data, 'sharpe_ratio')
optimizer = GeneticOptimizer(config, fitness_function)
result = optimizer.optimize(parameters, data)
```

### 5. Обучение с подкреплением (`core/ml/reinforcement_learning.py`)

#### RL агенты для торговли
- **TradingAgent**: DQN агент
- **TradingEnvironment**: Торговая среда
- **RLEnvironment**: Обертка для RL

#### Использование:
```python
from core.ml import TradingAgent, RLEnvironment, RLConfig

# Создание агента и среды
agent = TradingAgent(config)
env = RLEnvironment(data, config)

# Обучение
training_results = env.train_agent(agent)
evaluation = env.evaluate_agent(agent)
```

### 6. Ансамблевые методы (`core/ml/ensemble_methods.py`)

#### Комбинирование моделей
- **EnsemblePredictor**: Основной ансамбль
- **VotingEnsemble**: Голосование
- **StackingEnsemble**: Стекинг
- **AdaptiveEnsemble**: Адаптивный ансамбль

#### Использование:
```python
from core.ml import EnsemblePredictor, EnsembleConfig

# Конфигурация ансамбля
config = EnsembleConfig(
    base_models=['linear', 'ridge', 'rf', 'gb'],
    stacking_method='linear'
)

# Создание и обучение
ensemble = EnsemblePredictor(config)
ensemble.fit(X, y)
prediction = ensemble.predict(X_test)
```

## Интеграция (`core/ml/integration.py`)

### MLIntegrationManager
Центральный менеджер для интеграции всех ML компонентов:

```python
from core.ml.integration import create_ml_integration_manager

# Создание менеджера
ml_manager = create_ml_integration_manager(database_manager, news_processor)

# Получение рекомендаций
recommendations = ml_manager.get_ml_recommendations('AAPL')
```

### Основные методы:
- `analyze_market_sentiment()`: Анализ сентимента рынка
- `predict_price_movement()`: Прогнозирование движения цен
- `cluster_stocks()`: Кластеризация акций
- `optimize_trading_strategy()`: Оптимизация стратегий
- `train_rl_agent()`: Обучение RL агента
- `create_ensemble_prediction()`: Ансамблевые прогнозы

## Streamlit интерфейс

### Страница ML & AI (`pages/15_🤖_ML_AI.py`)

Интерактивный интерфейс с вкладками:
1. **📊 Sentiment Analysis**: Анализ сентимента новостей
2. **🔮 Price Prediction**: Прогнозирование цен
3. **🎯 Strategy Optimization**: Оптимизация стратегий
4. **📈 Stock Clustering**: Кластеризация акций
5. **🧠 Reinforcement Learning**: Обучение с подкреплением
6. **🎭 Ensemble Methods**: Ансамблевые методы

## Зависимости

### Основные:
- `torch>=2.0.0`: PyTorch для нейронных сетей
- `transformers>=4.30.0`: Hugging Face transformers
- `scikit-learn>=1.3.0`: Машинное обучение
- `matplotlib>=3.7.0`: Визуализация
- `seaborn>=0.12.0`: Статистическая визуализация

### Опциональные:
- `faiss-gpu>=1.7.0`: GPU ускорение для векторного поиска

## Примеры использования

### Базовый пример:
```python
# Создание менеджера ML
ml_manager = create_ml_integration_manager()

# Анализ сентимента
sentiment = ml_manager.analyze_market_sentiment()

# Прогнозирование цен
prediction = ml_manager.predict_price_movement('AAPL')

# Получение рекомендаций
recommendations = ml_manager.get_ml_recommendations('AAPL')
```

### Расширенный пример:
```python
# Настройка конфигураций
sentiment_config = SentimentConfig(
    model_name="cardiffnlp/twitter-roberta-base-sentiment-latest",
    confidence_threshold=0.8
)

model_config = ModelConfig(
    sequence_length=60,
    hidden_size=100,
    epochs=200
)

# Создание компонентов
sentiment_analyzer = NewsSentimentAnalyzer(sentiment_config)
price_predictor = LSTMPredictor(model_config)

# Обучение и использование
sentiment_result = sentiment_analyzer.get_market_sentiment(news_data)
training_result = price_predictor.train(stock_data)
prediction = price_predictor.predict(stock_data)
```

## Конфигурация

### Настройки через файлы конфигурации:
- `config/analytics.yml`: Настройки аналитики
- `config/news_pipeline.yml`: Настройки новостного пайплайна
- `config/notifications.yml`: Настройки уведомлений

### Программная конфигурация:
```python
# Настройка всех компонентов
ml_manager.sentiment_config = SentimentConfig(...)
ml_manager.model_config = ModelConfig(...)
ml_manager.clustering_config = ClusteringConfig(...)
ml_manager.genetic_config = GeneticConfig(...)
ml_manager.rl_config = RLConfig(...)
ml_manager.ensemble_config = EnsembleConfig(...)
```

## Производительность

### Рекомендации:
1. **GPU**: Используйте GPU для обучения нейронных сетей
2. **Память**: Увеличьте размер батча для лучшей производительности
3. **Кэширование**: Кэшируйте обученные модели
4. **Параллелизация**: Используйте параллельную обработку для больших данных

### Мониторинг:
- Логирование через `logging` модуль
- Метрики производительности в результатах
- Визуализация в Streamlit интерфейсе

## Устранение неполадок

### Частые проблемы:
1. **Отсутствие PyTorch**: Установите `torch>=2.0.0`
2. **Ошибки CUDA**: Проверьте совместимость версий
3. **Недостаток памяти**: Уменьшите размер батча
4. **Медленное обучение**: Используйте GPU или уменьшите сложность модели

### Логирование:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('core.ml')
```

## Дальнейшее развитие

### Планируемые функции:
1. **Дополнительные модели**: Transformer, CNN для временных рядов
2. **Автоматическое ML**: AutoML для выбора лучших моделей
3. **Онлайн обучение**: Инкрементальное обучение
4. **Мультимодальность**: Объединение текста, изображений и данных
5. **Объяснимость**: SHAP, LIME для интерпретации моделей

### Интеграции:
1. **Внешние API**: Интеграция с внешними ML сервисами
2. **Облачные платформы**: AWS SageMaker, Google AI Platform
3. **Мониторинг**: MLflow, Weights & Biases
4. **Развертывание**: Docker, Kubernetes для продакшена
