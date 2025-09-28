@echo off
echo Installing ML dependencies...

echo Installing seaborn...
pip install seaborn

echo Installing matplotlib...
pip install matplotlib

echo Installing torch...
pip install torch

echo Installing transformers...
pip install transformers

echo Installing scikit-learn...
pip install scikit-learn

echo Installing plotly...
pip install plotly

echo.
echo Installation complete!
echo.
echo Testing imports...

python -c "import seaborn; print('seaborn OK')"
python -c "import matplotlib; print('matplotlib OK')"
python -c "import torch; print('torch OK')"
python -c "import transformers; print('transformers OK')"
python -c "import sklearn; print('sklearn OK')"
python -c "import plotly; print('plotly OK')"

echo.
echo All dependencies installed successfully!
pause
