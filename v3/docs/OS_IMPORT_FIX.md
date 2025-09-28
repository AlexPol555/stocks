# Исправление ошибки NameError: name 'os' is not defined

## Проблема

**Ошибка**: `NameError: name 'os' is not defined`

**Местоположение**: `pages/14_🔍_System_Monitoring.py`, строка 243

**Причина**: В коде использовался `os.getenv()`, но модуль `os` не был импортирован.

## Решение

Добавлен импорт модуля `os` в начало файла:

```python
import asyncio
import os  # ← Добавлен этот импорт
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
```

## Измененный файл

**`pages/14_🔍_System_Monitoring.py`**:
- Добавлен `import os` в секцию импортов

## Проверка

- ✅ Линтер не показывает ошибок
- ✅ Модуль `os` теперь доступен для использования
- ✅ `os.getenv()` работает корректно

## Результат

Теперь страница System_Monitoring работает без ошибок и корректно отображает статус Telegram уведомлений.

**Статус**: ✅ **ИСПРАВЛЕНО**
