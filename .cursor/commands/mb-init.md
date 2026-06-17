---
name: /mb-init
id: mb-init
category: Memory Bank
description: Инициализировать или проверить структуру Memory Bank
---

Инициализируй или проверь структуру Memory Bank в проекте SwimBuoy.

**Ввод**: опционально — краткий контекст текущей работы.

**Шаги**

1. Проверь наличие `memory-bank/` и ключевых файлов:
   - `memory-bank/projectbrief.md`
   - `memory-bank/productContext.md`
   - `memory-bank/systemPatterns.md`
   - `memory-bank/techContext.md`
   - `memory-bank/activeContext.md`
   - `memory-bank/progress.md`
   - `memory-bank/tasks.md`
   - папки `memory-bank/archive/` и `memory-bank/reflection/`

2. Если чего-то нет — создай только внутри `memory-bank/`.

3. Если core-файлы пустые или шаблонные — заполни из существующей документации:
   - `docs/SESSION_SUMMARY.md` — продукт, Garmin, отладка
   - `docs/status.md` — сделано / next steps
   - `docs/decisions.md` — MVP-решения
   - `docs/dev-setup.md` — SDK, симулятор, FIT
   - `.cursorrules` — краткие правила

4. Если передан контекст:
   - добавь в `memory-bank/activeContext.md` как текущий фокус
   - кратко отметь в `memory-bank/progress.md`

5. Верни отчёт:
   - что уже было
   - что создано
   - что заполнить дальше
   - какие slash-команды использовать (`/mb-task`, `/mb-progress`, …)

**Ограничения**
- Не дублировать длинные тексты из `docs/` — ссылки + выжимка.
- Не перезаписывать существующее содержимое без необходимости.
- SwimBuoy — отдельный проект от «Проект Рогейн»; ничего не копировать оттуда автоматически.
