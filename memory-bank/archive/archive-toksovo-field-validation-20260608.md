# Archive: toksovo-field-validation (partial)

**Task ID:** `toksovo-field-validation`  
**Archived:** 2026-06-08  
**Status:** partial — закрыта с открытыми пунктами

## Summary

Подготовка и частичная валидация маршрута Аунеланлахти (Токсово): буи P1–P5 в JSON, сборка SB_Toksovo. Симуляторный прогон TCX/FIT и полевой тест на воде не выполнены на момент архивации.

## Checklist (final)

- [x] Полевой обход → TCX, буи P1–P5 в JSON
- [x] Сборка `SB_Toksovo.prg`
- [ ] Прогон TCX/FIT по Аунеланлахти в симуляторе (Activity Data → Play)
- [ ] Полевой тест на воде с FR955
- [ ] При необходимости — подправить координаты в JSON и пересобрать

## What was delivered

- Маршрут в `connect-iq/resources/jsonData/lake_demo.buoy_route.json`
- Документация: `routes/field_walk_2026-05-24.md`, `routes/toksovo_aunelanlahti.*`
- Рабочая сборка SB_Toksovo для fr955

## Verification (planned, not done)

- Симулятор: метры уменьшаются, стрелка к бую, dwell P1→…→P5
- Вода: FIT с GPS каждую секунду; сравнение с остановками на буях

## Warnings

- **3 пункта чеклиста не закрыты** — перенесены в следующую задачу
- **Рефлексия отсутствует** (`/mb-reflect` не выполнялся)

## Reflection

_(не создавалась)_

## Related docs

- `docs/new-route-and-app.md`
- `docs/status.md`
- `routes/field_walk_2026-05-24.md`

## Carry-over → next task

Открытые пункты вынести в новую задачу, например `toksovo-simulator-and-water-test`:

1. `scripts\build-and-run.bat` → Play TCX/FIT в симуляторе
2. Полевой тест с обновлённым .prg (в т.ч. ActivityRecording)
3. Уточнение координат буёв по FIT при необходимости
