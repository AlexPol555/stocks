@echo off
echo Установка зависимостей News Pipeline...
echo.

echo Установка базовых зависимостей...
pip install streamlit pandas numpy pyyaml

echo.
echo Установка опциональных зависимостей...
echo Установить sentence-transformers? (y/n)
set /p choice1=
if /i "%choice1%"=="y" pip install sentence-transformers

echo Установить rapidfuzz? (y/n)
set /p choice2=
if /i "%choice2%"=="y" pip install rapidfuzz

echo Установить pymorphy3? (y/n)
set /p choice3=
if /i "%choice3%"=="y" pip install pymorphy3

echo Установить razdel? (y/n)
set /p choice4=
if /i "%choice4%"=="y" pip install razdel

echo Установить spacy? (y/n)
set /p choice5=
if /i "%choice5%"=="y" (
    pip install spacy
    python -m spacy download ru_core_news_sm
    python -m spacy download en_core_web_sm
)

echo.
echo Установка завершена!
echo Для запуска: streamlit run pages/9_🔍_News_Pipeline.py
pause
