---
name: /mb-reflect
id: mb-reflect
category: Memory Bank
description: Написать рефлексию по задаче в memory-bank/reflection/
---

Создай или обнови рефлексию по активной задаче.

**Ввод**: опционально — task ID или имя. Без ввода — из активной задачи в `memory-bank/tasks.md`.

**Шаги**

1. Определи задачу:
   - по вводу, или из `memory-bank/tasks.md`
   - если неоднозначно — спроси пользователя

2. Создай/обнови файл:
   - `memory-bank/reflection/reflection-<task-id>.md`

3. Секции:
   - Context
   - What changed (файлы, координаты, сборка)
   - Decisions & trade-offs
   - Validation (симулятор FR955, TCX/FIT, поле)
   - Problems & mitigations
   - Follow-up

4. Добавь ссылку на рефлексию в секцию задачи в `memory-bank/tasks.md`.

5. Верни:
   - путь к рефлексии
   - главные выводы
   - готова ли задача к `/mb-archive`

**Ограничения**
- Рефлексия — про решения и проверку, не полный diff кода.
- Для продуктовых решений ссылайся на `docs/decisions.md`, не дублируй.
