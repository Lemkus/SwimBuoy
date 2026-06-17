# Маршруты буёв

**Как добавить новое место и собрать приложение:** `docs/new-route-and-app.md`

В часах вшивается только один файл:

`connect-iq/resources/jsonData/lake_demo.buoy_route.json`

Остальные JSON здесь — **архивы**, их можно подставить в сборку в любой момент.

| Файл | Описание |
|------|----------|
| `field_walk_2026-05-24.buoy_route.json` | Полевой круг ~890 m (TCX 24.05.2026), P1 у 60.12001, 30.25903 |
| `tohkolodskoye_yukki.buoy_route.json` | Тохколодское озеро, Юкки (~1 km) |
| `toksovo_aunelanlahti.buoy_route.json` | Токсово, залив Аунеланлахти (~650 m) |
| `toksovo_aunelanlahti_buoys.gpx` | GPX точек Аунеланлахти для карт |
| `example.buoy_route.json` | То же, что field_walk (эталон формата) |
| `lake_demo_buoys.gpx` | GPX точек field_walk для карт |

## Переключить маршрут в приложении

PowerShell из корня проекта:

```powershell
Copy-Item routes\field_walk_2026-05-24.buoy_route.json connect-iq\resources\jsonData\lake_demo.buoy_route.json
# или:
Copy-Item routes\tohkolodskoye_yukki.buoy_route.json connect-iq\resources\jsonData\lake_demo.buoy_route.json
# или:
Copy-Item routes\toksovo_aunelanlahti.buoy_route.json connect-iq\resources\jsonData\lake_demo.buoy_route.json

.\scripts\build-and-run.bat
```

Сейчас в сборке **SB_Toksovo**: **Аунеланлахти** (`toksovo_aunelanlahti`).
