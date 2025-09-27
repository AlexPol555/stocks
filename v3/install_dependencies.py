#!/usr/bin/env python3
"""
Скрипт для установки зависимостей News Pipeline
Автоматически устанавливает зависимости в зависимости от доступности
"""

import subprocess
import sys
from pathlib import Path


def install_package(package_name: str, description: str = "") -> bool:
    """Установить пакет и вернуть True если успешно."""
    try:
        print(f"Установка {package_name}...")
        if description:
            print(f"  {description}")
        
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", package_name
        ], capture_output=True, text=True, check=True)
        
        print(f"✅ {package_name} установлен успешно")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки {package_name}: {e}")
        if e.stdout:
            print(f"  stdout: {e.stdout}")
        if e.stderr:
            print(f"  stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка при установке {package_name}: {e}")
        return False


def check_package(package_name: str) -> bool:
    """Проверить, установлен ли пакет."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def main():
    """Основная функция установки."""
    print("=== Установка зависимостей News Pipeline ===")
    print()
    
    # Базовые зависимости (обязательные)
    basic_packages = [
        ("streamlit", "Веб-интерфейс"),
        ("pandas", "Обработка данных"),
        ("numpy", "Численные вычисления"),
        ("pyyaml", "Конфигурационные файлы"),
    ]
    
    # Расширенные зависимости (опциональные)
    optional_packages = [
        ("sentence-transformers", "Эмбеддинги для семантического поиска"),
        ("rapidfuzz", "Нечёткое сравнение строк"),
        ("pymorphy3", "Русская морфология"),
        ("razdel", "Токенизация русского текста"),
        ("spacy", "Извлечение именованных сущностей"),
        ("faiss-cpu", "Быстрый векторный поиск"),
        ("psutil", "Мониторинг системы"),
    ]
    
    # Установка базовых пакетов
    print("📦 Установка базовых зависимостей...")
    basic_success = 0
    for package, description in basic_packages:
        if check_package(package.replace("-", "_")):
            print(f"✅ {package} уже установлен")
            basic_success += 1
        else:
            if install_package(package, description):
                basic_success += 1
        print()
    
    print(f"Базовые зависимости: {basic_success}/{len(basic_packages)} установлено")
    print()
    
    # Установка опциональных пакетов
    print("🔧 Установка опциональных зависимостей...")
    optional_success = 0
    for package, description in optional_packages:
        if check_package(package.replace("-", "_")):
            print(f"✅ {package} уже установлен")
            optional_success += 1
        else:
            print(f"Установить {package}? (y/n): ", end="")
            try:
                response = input().lower().strip()
                if response in ['y', 'yes', 'да', 'д']:
                    if install_package(package, description):
                        optional_success += 1
                else:
                    print(f"⏭️  Пропуск {package}")
            except KeyboardInterrupt:
                print("\n⏹️  Установка прервана пользователем")
                break
        print()
    
    print(f"Опциональные зависимости: {optional_success}/{len(optional_packages)} установлено")
    print()
    
    # Установка spaCy моделей (если spaCy установлен)
    if check_package("spacy"):
        print("🌍 Установка spaCy моделей...")
        spacy_models = [
            ("ru_core_news_sm", "Русская модель для NER"),
            ("en_core_web_sm", "Английская модель для NER (fallback)"),
        ]
        
        for model, description in spacy_models:
            try:
                print(f"Установка {model}...")
                subprocess.run([
                    sys.executable, "-m", "spacy", "download", model
                ], check=True, capture_output=True)
                print(f"✅ {model} установлен")
            except subprocess.CalledProcessError:
                print(f"❌ Ошибка установки {model}")
            except Exception as e:
                print(f"❌ Неожиданная ошибка: {e}")
            print()
    
    # Итоговый отчёт
    print("=== ИТОГОВЫЙ ОТЧЁТ ===")
    print(f"✅ Базовые зависимости: {basic_success}/{len(basic_packages)}")
    print(f"🔧 Опциональные зависимости: {optional_success}/{len(optional_packages)}")
    print()
    
    if basic_success == len(basic_packages):
        print("🎉 News Pipeline готов к работе!")
        print()
        print("Для запуска:")
        print("  python tests/demo_news_pipeline.py  # Демонстрация")
        print("  streamlit run pages/9_🔍_News_Pipeline.py  # Веб-интерфейс")
    else:
        print("⚠️  Некоторые базовые зависимости не установлены.")
        print("   News Pipeline может работать с ограниченной функциональностью.")
    
    print()
    print("Для установки всех зависимостей сразу:")
    print("  pip install -r requirements.txt")
    print()
    print("Для минимальной установки:")
    print("  pip install -r requirements-minimal.txt")


if __name__ == "__main__":
    main()
