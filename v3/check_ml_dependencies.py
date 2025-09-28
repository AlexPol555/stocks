#!/usr/bin/env python3
"""Check ML dependencies and provide installation instructions."""

def check_dependencies():
    """Check which ML dependencies are available."""
    dependencies = {
        'numpy': 'numpy',
        'pandas': 'pandas', 
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'plotly': 'plotly',
        'scikit-learn': 'sklearn',
        'torch': 'torch',
        'transformers': 'transformers'
    }
    
    available = []
    missing = []
    
    for name, module in dependencies.items():
        try:
            __import__(module)
            available.append(name)
            print(f"✅ {name} - Available")
        except ImportError:
            missing.append(name)
            print(f"❌ {name} - Missing")
    
    print(f"\nSummary: {len(available)}/{len(dependencies)} dependencies available")
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("\nTo install missing dependencies, run:")
        print("pip install " + " ".join(missing))
        
        # Specific installation commands
        if 'seaborn' in missing:
            print("\nFor seaborn specifically:")
            print("pip install seaborn matplotlib")
        
        if 'torch' in missing:
            print("\nFor PyTorch specifically:")
            print("pip install torch torchvision torchaudio")
        
        if 'transformers' in missing:
            print("\nFor transformers specifically:")
            print("pip install transformers")
    
    return len(missing) == 0

def test_ml_imports():
    """Test ML module imports."""
    print("\n" + "="*50)
    print("Testing ML module imports...")
    
    try:
        from core.ml.fallback import create_fallback_ml_manager
        print("✅ Fallback ML modules - Available")
        
        # Test fallback functionality
        manager = create_fallback_ml_manager()
        sentiment = manager.analyze_market_sentiment()
        print(f"✅ Fallback sentiment analysis works: {sentiment['overall_sentiment']}")
        
    except ImportError as e:
        print(f"❌ Fallback ML modules - Missing: {e}")
    
    try:
        from core.ml import LSTMPredictor, ModelConfig
        print("✅ Full ML modules - Available")
    except ImportError as e:
        print(f"❌ Full ML modules - Missing: {e}")

if __name__ == "__main__":
    print("ML Dependencies Checker")
    print("="*50)
    
    all_available = check_dependencies()
    test_ml_imports()
    
    if all_available:
        print("\n🎉 All dependencies are available! ML modules should work correctly.")
    else:
        print("\n⚠️ Some dependencies are missing. ML modules will use fallback mode.")
