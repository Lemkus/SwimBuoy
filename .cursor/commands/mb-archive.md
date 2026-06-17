---
name: /mb-archive
id: mb-archive
category: Memory Bank
description: Заархивировать завершённую задачу Memory Bank
---

Заархивируй завершённую задачу из Memory Bank.

**Ввод**: опционально — task ID или имя. Без ввода — из завершённой активной задачи.

**Шаги**

1. Выбери задачу:
   - по вводу, или из `memory-bank/tasks.md`
   - при нескольких кандидатах — спроси пользователя

2. Pre-check:
   - незакрытые пункты чеклиста
   - есть ли рефлексия (иначе предложи `/mb-reflect`)
   - при неполноте — предупреди и спроси подтверждение

3. Создай архив:
   - `memory-bank/archive/archive-<task-id>-<yyyymmdd>.md`
   - summary, что менялось, проверка, ссылки на reflection и `docs/`

4. Обнови трекеры:
   - пометь задачу archived в `memory-bank/tasks.md`
   - запись в `memory-bank/progress.md`
   - `memory-bank/activeContext.md` — следующий фокус
   - при значимых итогах — кратко `docs/status.md`

5. Верни:
   - путь к архиву
   - предупреждения (если архив с открытыми пунктами)
   - следующий шаг (`/mb-init` или `/mb-task`)

**Ограничения**
- Историю не удалять — только ссылки и перенос в archive.
- Архивы только в `memory-bank/archive/`.
