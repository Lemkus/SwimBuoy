# Tech Context — SwimBuoy

Обновлено: 2026-06-08

## Платформа

- **Устройство**: Garmin Forerunner 955
- **Стек**: Connect IQ, Monkey C
- **ОС разработки**: Windows 10/11

## SDK и пути

- SDK: `%APPDATA%\Garmin\ConnectIQ\Sdks\...`
- Кириллица в пути пользователя → `connect-iq/setup-sdk-path.bat` монтирует SDK на **`X:\`**
- `current-sdk.cfg` = `X:\`
- `monkeyC.developerKeyPath`: `connect-iq/developer_key.der`

## Отладка

| Действие | Как |
|----------|-----|
| Сборка + симулятор | `.\scripts\build-and-run.bat` |
| Альтернатива | F5 (Run App fr955) |
| GPS в симуляторе | Simulation → Activity Data → Play |
| Полевой трек | FIT/TCX из Garmin Connect, `scripts/analyze_tcx.py` |

## Известные проблемы

- `Tasks: Run Task` — баг Cursor `r is not iterable`; использовать bat или F5
- После перезагрузки Windows — снова `setup-sdk-path.bat`

Подробнее: `docs/dev-setup.md`
