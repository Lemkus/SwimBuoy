# Archive: water-activity-recording

**Task ID:** `water-activity-recording`  
**Archived:** 2026-06-08  
**Status:** completed (код готов; полевая проверка — в следующей задаче)

## Summary

При погружении в воду приложение SB_Toksovo закрывалось на FR955. Причина: `watch-app` без записи активности — система завершает такие CIQ-приложения при водоблокировке или конфликте с нативным Open Water Swim.

Добавлена автоматическая запись Open Water Swim через `ActivityRecording` при старте приложения.

## Changes

| Файл | Что сделано |
|------|-------------|
| `connect-iq/source/SwimBuoyView.mc` | `startActivityRecording()`, `finishActivityRecording()`; сессия `SPORT_SWIMMING` / `SUB_SPORT_OPEN_WATER`, `:recordLocation => true` |
| `connect-iq/source/SwimBuoyDelegate.mc` | Сохранение FIT при выходе (кнопка «назад») |
| `connect-iq/source/SwimBuoyApp.mc` | Delegate получает ссылку на view |
| `connect-iq/manifest.xml` | Разрешение `Fit` |

## Verification

- [x] Сборка `SB_Toksovo.prg` для fr955 — успешно
- [ ] Полевой тест: приложение не закрывается в воде (ожидает переустановки .prg на часы)
- [ ] FIT сохраняется в Garmin Connect после выхода из приложения

## User workflow (на воде)

1. Запускать **только SB_Toksovo**, не параллельно штатный «Open Water Swim»
2. Дождаться GPS на берегу
3. Водоблокировка — норма; разблокировка: удержать обе боковые кнопки
4. Выход — «назад» → тренировка сохраняется

## Reflection

Рефлексия не оформлялась (`/mb-reflect` пропущен). Итог зафиксирован в этом архиве.

## Related docs

- `docs/status.md` — известные ограничения и next steps
- `docs/dev-setup.md` — сборка и деплой

## Follow-up

Если после фикса приложение всё ещё закрывается при запуске **штатного** Open Water Swim — рассмотреть **data field** внутри нативной активности (отдельная задача).
