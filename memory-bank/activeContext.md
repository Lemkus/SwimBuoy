# Active Context — SwimBuoy

Обновлено: 2026-06-08

## Текущий фокус

Нет активной задачи. Следующий логичный шаг — валидация маршрута в симуляторе и на воде (carry-over из архива toksovo).

## Недавно заархивировано

- `water-activity-recording` — ActivityRecording для устойчивости в воде
- `toksovo-field-validation` (partial) — буи P1–P5, сборка; симулятор/вода — открыто

Архивы: `memory-bank/archive/archive-*-20260608.md`

## Следующий немедленный шаг

1. `/mb-task` → создать `toksovo-simulator-and-water-test`
2. `.\scripts\build-and-run.bat` — переустановить SB_Toksovo на часы
3. Симулятор: Activity Data → Play TCX/FIT по Аунеланлахти
4. Полевой тест на воде (только SB_Toksovo, без штатного Open Water Swim)

## Slash-команды Memory Bank

| Команда | Когда |
|---------|--------|
| `/mb-init` | Первый запуск / проверка структуры |
| `/mb-task` | Новая или обновление задачи |
| `/mb-progress` | Конец сессии |
| `/mb-reflect` | Итоги задачи |
| `/mb-archive` | Закрытие задачи |
