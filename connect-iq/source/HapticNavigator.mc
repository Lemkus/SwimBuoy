import Toybox.Application;
import Toybox.Lang;

class HapticNavigator {
    const MODE_OFF = "off";
    const MODE_CORRIDOR = "corridor_off_course";

    const DEF_CORRIDOR_HALF_WIDTH_M = 20.0;
    const DEF_CORRIDOR_HYSTERESIS_M = 5.0;
    const DEF_CORRIDOR_ENTER_SEC = 3;
    const DEF_CORRIDOR_CLEAR_SEC = 2;
    const DEF_APPROACH_WINDOW_SEC = 15;
    const DEF_APPROACH_PROGRESS_M = 3.0;
    const DEF_EMA_ALPHA = 0.3;
    const DEF_PULSE_MIN_INTERVAL_SEC = 6;
    const DEF_LEG_ENDPOINT_BUFFER_M = 50.0;

    var hapticMode as String = MODE_CORRIDOR;
    var corridorHalfWidthM as Float = DEF_CORRIDOR_HALF_WIDTH_M;
    var corridorHysteresisM as Float = DEF_CORRIDOR_HYSTERESIS_M;
    var corridorEnterSec as Number = DEF_CORRIDOR_ENTER_SEC;
    var corridorClearSec as Number = DEF_CORRIDOR_CLEAR_SEC;
    var approachWindowSec as Number = DEF_APPROACH_WINDOW_SEC;
    var approachProgressM as Float = DEF_APPROACH_PROGRESS_M;
    var emaAlpha as Float = DEF_EMA_ALPHA;
    var pulseMinIntervalSec as Number = DEF_PULSE_MIN_INTERVAL_SEC;
    var legEndpointBufferM as Float = DEF_LEG_ENDPOINT_BUFFER_M;

    var corridorClearWidthM as Float = 15.0;

    var smoothedDistM as Float? = null;
    var smoothedXteM as Float? = null;
    var smoothedSignedXteM as Float? = null;
    var distHistory as Array = [];
    var isOutside as Boolean = false;
    var isApproachingNow as Boolean = false;
    var outsideSec as Number = 0;
    var insideSec as Number = 0;
    var buoyChangedAtSec as Number = 0;
    var lastPulseSec as Number = -100;
    var pendingPulse as Boolean = false;

    function initialize() {
        loadSettings();
    }

    function loadSettings() as Void {
        hapticMode = readStringProp("hapticMode", MODE_CORRIDOR);
        corridorHalfWidthM = readFloatProp("hapticCorridorHalfWidthM", DEF_CORRIDOR_HALF_WIDTH_M);
        corridorHysteresisM = readFloatProp("hapticCorridorHysteresisM", DEF_CORRIDOR_HYSTERESIS_M);
        corridorEnterSec = readNumberProp("hapticCorridorEnterSec", DEF_CORRIDOR_ENTER_SEC);
        corridorClearSec = readNumberProp("hapticCorridorClearSec", DEF_CORRIDOR_CLEAR_SEC);
        approachWindowSec = readNumberProp("hapticApproachWindowSec", DEF_APPROACH_WINDOW_SEC);
        approachProgressM = readFloatProp("hapticApproachProgressM", DEF_APPROACH_PROGRESS_M);
        emaAlpha = readFloatProp("hapticEmaAlpha", DEF_EMA_ALPHA);
        pulseMinIntervalSec = readNumberProp("hapticPulseMinIntervalSec", DEF_PULSE_MIN_INTERVAL_SEC);
        legEndpointBufferM = readFloatProp("hapticLegEndpointBufferM", DEF_LEG_ENDPOINT_BUFFER_M);
        corridorClearWidthM = corridorHalfWidthM - corridorHysteresisM;
        if (corridorClearWidthM < 0.0) {
            corridorClearWidthM = 0.0;
        }
    }

    function readStringProp(key as String, fallback as String) as String {
        var value = Application.Properties.getValue(key);
        if (value != null && value instanceof String) {
            return value as String;
        }
        return fallback;
    }

    function readNumberProp(key as String, fallback as Number) as Number {
        var value = Application.Properties.getValue(key);
        if (value != null && value instanceof Number) {
            return value as Number;
        }
        return fallback;
    }

    function readFloatProp(key as String, fallback as Float) as Float {
        var value = Application.Properties.getValue(key);
        if (value != null) {
            if (value instanceof Float) {
                return value as Float;
            }
            if (value instanceof Number) {
                return (value as Number).toFloat();
            }
        }
        return fallback;
    }

    function resetForNewBuoy(rawDistM as Float, rawSignedXteM as Float, nowSec as Number) as Void {
        smoothedDistM = rawDistM;
        smoothedSignedXteM = rawSignedXteM;
        smoothedXteM = absXte(rawSignedXteM);
        distHistory = [[nowSec, rawDistM]] as Array;
        isOutside = false;
        isApproachingNow = false;
        outsideSec = 0;
        insideSec = 0;
        buoyChangedAtSec = nowSec;
        lastPulseSec = -100;
        pendingPulse = false;
    }

    function absXte(signedXteM as Float) as Float {
        return signedXteM < 0.0 ? -signedXteM : signedXteM;
    }

    function update(
        nowSec as Number,
        rawDistM as Float,
        rawSignedXteM as Float,
        alongValid as Boolean,
        insideRadius as Boolean,
        sessionActive as Boolean
    ) as Void {
        pendingPulse = false;

        if (!sessionActive || hapticMode.equals(MODE_OFF) || insideRadius) {
            return;
        }

        if (smoothedDistM == null || smoothedXteM == null || smoothedSignedXteM == null) {
            resetForNewBuoy(rawDistM, rawSignedXteM, nowSec);
            return;
        }

        if (nowSec - buoyChangedAtSec < corridorEnterSec) {
            return;
        }

        if (!alongValid) {
            return;
        }

        var rawAbsXte = absXte(rawSignedXteM);
        smoothedDistM = (1.0 - emaAlpha) * smoothedDistM + emaAlpha * rawDistM;
        smoothedSignedXteM = (1.0 - emaAlpha) * smoothedSignedXteM + emaAlpha * rawSignedXteM;
        smoothedXteM = (1.0 - emaAlpha) * smoothedXteM + emaAlpha * rawAbsXte;
        distHistory.add([nowSec, smoothedDistM]);

        trimHistory(nowSec);

        var approaching = isApproaching(nowSec);
        isApproachingNow = approaching;

        if (smoothedXteM > corridorHalfWidthM) {
            outsideSec += 1;
            insideSec = 0;
        } else if (smoothedXteM < corridorClearWidthM) {
            insideSec += 1;
            outsideSec = 0;
        } else {
            outsideSec = 0;
            insideSec = 0;
        }

        if (isOutside) {
            if (insideSec >= corridorClearSec || approaching) {
                isOutside = false;
                outsideSec = 0;
                insideSec = 0;
            }
        } else if (outsideSec >= corridorEnterSec && !approaching) {
            isOutside = true;
        }

        if (isOutside && nowSec - lastPulseSec >= pulseMinIntervalSec) {
            pendingPulse = true;
            lastPulseSec = nowSec;
        }
    }

    function trimHistory(nowSec as Number) as Void {
        var cutoff = nowSec - approachWindowSec - 2;
        while (distHistory.size() > 2) {
            var oldest = distHistory[0] as Array;
            if ((oldest[0] as Number) >= cutoff) {
                break;
            }
            distHistory = distHistory.slice(1, distHistory.size());
        }
    }

    function isApproaching(nowSec as Number) as Boolean {
        if (smoothedDistM == null) {
            return false;
        }
        var pastDist = findSmoothedAtSec(nowSec - approachWindowSec);
        if (pastDist == null) {
            return false;
        }
        return (smoothedDistM - pastDist) <= -approachProgressM;
    }

    function findSmoothedAtSec(targetSec as Number) as Float? {
        var bestDist = null as Float?;
        var bestDelta = 999999;
        for (var i = 0; i < distHistory.size(); i += 1) {
            var entry = distHistory[i] as Array;
            var entrySec = entry[0] as Number;
            var delta = entrySec - targetSec;
            if (delta < 0) {
                delta = -delta;
            }
            if (delta < bestDelta) {
                bestDelta = delta;
                bestDist = entry[1] as Float;
            }
        }
        if (bestDelta > approachWindowSec) {
            return null;
        }
        return bestDist;
    }

    function shouldPulse() as Boolean {
        return pendingPulse;
    }

    function clearPulse() as Void {
        pendingPulse = false;
    }

    function getSmoothedXteM() as Float? {
        return smoothedXteM;
    }

    function getSmoothedSignedXteM() as Float? {
        return smoothedSignedXteM;
    }

    function getCorridorUiState(nowSec as Number) as String {
        if (nowSec - buoyChangedAtSec < corridorEnterSec) {
            return "warming";
        }
        if (isOutside) {
            return "outside";
        }
        if (isApproachingNow) {
            return "approaching";
        }
        return "inside";
    }

    function isCorridorOutside() as Boolean {
        return isOutside;
    }
}
