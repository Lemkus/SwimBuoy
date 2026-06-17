---
name: /mb-progress
id: mb-progress
category: Memory Bank
description: Записать прогресс сессии в Memory Bank
---

Обнови Memory Bank после текущей сессии работы.

**Ввод**: опционально — краткое резюме сделанного.

**Шаги**

1. Прочитай:
   - `memory-bank/activeContext.md`
   - `memory-bank/progress.md`
   - `memory-bank/tasks.md`

2. Определи дельту сессии:
   - закрытые пункты чеклиста
   - что в работе
   - блокеры (если есть)

3. Обнови:
   - `memory-bank/activeContext.md` — текущее состояние и следующий шаг
   - `memory-bank/progress.md` — запись с датой
   - `memory-bank/tasks.md` — отметь выполненные `- [x]`

4. Если изменился общий статус проекта — кратко обнови `docs/status.md` (секции «Сделано» / «Следующий шаг»), без дублирования всего Memory Bank.

5. Верни:
   - что записано
   - сколько открытых пунктов осталось
   - рекомендуемую команду: `/mb-task`, `/mb-reflect` или `/mb-archive`

**Ограничения**
- Записи короткие и actionable.
- Не отмечай невыполненное как done.
- Сохраняй хронологию в `memory-bank/progress.md`.
