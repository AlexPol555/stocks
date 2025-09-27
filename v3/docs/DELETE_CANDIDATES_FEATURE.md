# ❌ Функция отклонения и восстановления кандидатов

## Добавленные возможности

### 1. Отклонение всех кандидатов

**Кнопка:** "❌ Reject All" (в разделе Batch Actions)

**Функциональность:**
- Помечает ВСЕ кандидаты как отклоненные (confirmed = -1)
- НЕ удаляет записи из базы данных
- Кандидаты скрываются из списка, но могут быть восстановлены
- Требует двойного подтверждения
- Показывает количество отклоненных кандидатов

**Процесс:**
1. Нажать "❌ Reject All"
2. Появится предупреждение: "⚠️ This will mark ALL candidates as rejected (they will be hidden from the list but can be reprocessed later)!"
3. Поставить галочку "I understand this action will hide all candidates"
4. Нажать "❌ CONFIRM REJECT ALL"
5. Кандидаты будут отклонены, кэш очищен, страница обновлена

### 2. Удаление отображаемых кандидатов

**Кнопка:** "🗑️ Delete Displayed" (в разделе Actions for Displayed Candidates)

**Функциональность:**
- Удаляет только кандидатов, отображаемых на текущей странице
- Учитывает примененные фильтры (min_score, only_unconfirmed, limit)
- Безопаснее, чем удаление всех кандидатов

**Процесс:**
1. Нажать "🗑️ Delete Displayed"
2. Появится предупреждение с количеством: "⚠️ This will permanently delete X displayed candidates!"
3. Поставить галочку "I understand this action cannot be undone"
4. Нажать "🗑️ CONFIRM DELETE DISPLAYED"
5. Отображаемые кандидаты будут удалены

### 3. Восстановление отклоненных кандидатов

**Кнопка:** "🔄 Restore Rejected (X)" (в разделе Actions for Displayed Candidates)

**Функциональность:**
- Восстанавливает все отклоненные кандидаты (confirmed = -1 → confirmed = 0)
- Показывает количество доступных для восстановления кандидатов
- Кандидаты снова становятся доступными для просмотра и валидации
- Требует подтверждения

**Процесс:**
1. Нажать "🔄 Restore Rejected (X)" (где X - количество отклоненных)
2. Появится информация: "This will restore X rejected candidates to unconfirmed status so they can be reviewed again."
3. Поставить галочку "I want to restore rejected candidates"
4. Нажать "🔄 CONFIRM RESTORE"
5. Кандидаты будут восстановлены, кэш очищен, страница обновлена

### 4. Статистика отображаемых кандидатов

**Кнопка:** "📊 Show Statistics" (в разделе Actions for Displayed Candidates)

**Функциональность:**
- Показывает детальную статистику по отображаемым кандидатам
- Включает количество, статусы, диапазон и средний score

**Информация:**
- Total displayed: общее количество
- Confirmed: подтвержденные
- Rejected: отклоненные
- Unconfirmed: неподтвержденные
- Score range: диапазон оценок
- Average score: средняя оценка

## Технические детали

### Методы в репозитории

```python
def reject_all_candidates(self, operator: Optional[str] = None) -> int:
    """Mark all candidates as rejected (confirmed = -1) instead of deleting them."""
    now = _utc_now()
    with self.connect() as conn:
        # Count candidates before update
        cursor = conn.execute("SELECT COUNT(*) FROM news_tickers")
        count_before = cursor.fetchone()[0]
        
        # Mark all candidates as rejected
        conn.execute(
            """
            UPDATE news_tickers 
            SET confirmed = -1, confirmed_by = ?, confirmed_at = ?
            WHERE confirmed != -1
            """,
            (operator or "system", now)
        )
        conn.commit()
        
        # Count updated candidates
        cursor = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = -1")
        count_after = cursor.fetchone()[0]
        
        return count_after

def reset_rejected_candidates(self, operator: Optional[str] = None) -> int:
    """Reset all rejected candidates to unconfirmed status (confirmed = 0)."""
    now = _utc_now()
    with self.connect() as conn:
        # Count rejected candidates before update
        cursor = conn.execute("SELECT COUNT(*) FROM news_tickers WHERE confirmed = -1")
        count_before = cursor.fetchone()[0]
        
        # Reset rejected candidates to unconfirmed
        conn.execute(
            """
            UPDATE news_tickers 
            SET confirmed = 0, confirmed_by = ?, confirmed_at = ?
            WHERE confirmed = -1
            """,
            (operator or "system", now)
        )
        conn.commit()
        
        return count_before
```

### Удаление отображаемых кандидатов

```python
deleted_count = 0
for idx, candidate in df.iterrows():
    candidate_dict = candidate.to_dict()
    candidate_id = candidate_dict.get('id', 0)
    if candidate_id > 0:
        with session_state.repository.connect() as conn:
            conn.execute("DELETE FROM news_tickers WHERE id = ?", (candidate_id,))
            conn.commit()
        deleted_count += 1
```

### Обновленный макет кнопок

**Было:** 3 колонки
```python
col1, col2, col3 = st.columns(3)
```

**Стало:** 4 колонки
```python
col1, col2, col3, col4 = st.columns(4)
```

**Кнопки:**
- col1: "✅ Confirm All High Score"
- col2: "❌ Reject All Low Score"
- col3: "🔄 Reset All"
- col4: "🗑️ Delete All"

## Безопасность

### Многоуровневая защита

1. **Предупреждения** - четкие сообщения о последствиях
2. **Чекбоксы подтверждения** - пользователь должен явно согласиться
3. **Двойное подтверждение** - две кнопки для критических действий
4. **Цветовая индикация** - красные кнопки для опасных действий

### Типы кнопок

- `type="secondary"` - для кнопок удаления (менее заметные)
- `type="primary"` - для финального подтверждения (яркие, красные)

## Примеры использования

### Сценарий 1: Очистка всех данных

1. Пользователь хочет начать с чистого листа
2. Нажимает "🗑️ Delete All"
3. Подтверждает действие
4. Все кандидаты удаляются из базы данных

### Сценарий 2: Удаление плохих кандидатов

1. Пользователь применяет фильтр (например, score < 0.3)
2. Видит только плохие кандидаты
3. Нажимает "🗑️ Delete Displayed"
4. Удаляются только отфильтрованные кандидаты

### Сценарий 3: Анализ данных

1. Пользователь применяет фильтры
2. Нажимает "📊 Show Statistics"
3. Видит детальную статистику по отображаемым кандидатам
4. Принимает решение о дальнейших действиях

## Интерфейс

### Batch Actions (4 кнопки)
```
[✅ Confirm All High Score] [❌ Reject All Low Score] [🔄 Reset All] [❌ Reject All]
```

### Actions for Displayed Candidates (3 кнопки)
```
[🗑️ Delete Displayed] [📊 Show Statistics] [🔄 Restore Rejected (X)]
```

### Статусы кандидатов (4 метрики)
```
[Confirmed] [Rejected] [Unconfirmed] [Total Rejected]
```

### Individual Validation
- Индивидуальные кнопки подтверждения/отклонения для каждого кандидата
- Остается без изменений

## Сообщения

### Предупреждения
- "⚠️ This will mark ALL candidates as rejected (they will be hidden from the list but can be reprocessed later)!"
- "⚠️ This will permanently delete X displayed candidates!"

### Подтверждения
- "I understand this action will hide all candidates"
- "I want to restore rejected candidates"

### Результаты
- "❌ Rejected X candidates! They are now hidden but can be reprocessed."
- "🔄 Restored X rejected candidates! They are now available for review."
- "🗑️ Deleted X displayed candidates!"

### Информация
- "This will restore X rejected candidates to unconfirmed status so they can be reviewed again."
- "No rejected candidates to restore"

### Ошибки
- "Error rejecting candidates: {error}"
- "Error restoring candidates: {error}"
- "Error deleting displayed candidates: {error}"

## Заключение

Добавлены мощные инструменты для управления кандидатами:

1. **Отклонение всех кандидатов** - скрытие всех кандидатов без удаления из БД
2. **Восстановление отклоненных** - возврат скрытых кандидатов для повторного просмотра
3. **Селективное удаление** - удаление только отображаемых кандидатов
4. **Анализ данных** - статистика по кандидатам
5. **Безопасность** - многоуровневая защита от случайных действий

### Преимущества нового подхода

- **Сохранение данных** - кандидаты не удаляются, а скрываются
- **Возможность восстановления** - можно вернуть скрытые кандидаты
- **Гибкость** - новости могут быть обработаны заново в будущем
- **Аудит** - все действия логируются с указанием оператора

Теперь пользователь может эффективно управлять кандидатами-тикерами с полным контролем над процессом и возможностью восстановления!
