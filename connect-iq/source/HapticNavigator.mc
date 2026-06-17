import Toybox.Application;
import Toybox.Lang;

class HapticNavigator {
    const MODE_OFF = "off";
    const MODE_BEACON = "beacon_off_course";

    const DEF_TREND_WINDOW_SEC = 15;
    const DEF_ON_SCALE = 3.0;
    const DEF_OFF_SCALE = 2.0;
    const DEF_OFF_CLEAR_SCALE = 1.2;
    const DEF_LEG_DRIFT_BUDGET_M = 15.0;
    const DEF_EMA_ALPHA = 0.3;
    const DEF_PULSE_MIN_INTERVAL_SEC = 6;
    const DEF_START_MISMATCH_M = 50.0;
    const DEF_START_PROGRESS_M = 5.0;
    const DEF_START_DRIFT_M = 5.0;

    var hapticMode as String = MODE_BEACON;
    var trendWindowSec as Number = DEF_TREND_WINDOW_SEC;
    var onScale as Float = DEF_ON_SCALE;
    var offScale as Float = DEF_OFF_SCALE;
    var offClearScale as Float = DEF_OFF_CLEAR_SCALE;
    var legDriftBudgetM as Float = DEF_LEG_DRIFT_BUDGET_M;
    var emaAlpha as Float = DEF_EMA_ALPHA;
    var pulseMinIntervalSec as Number = DEF_PULSE_MIN_INTERVAL_SEC;
    var startProgressM as Float = DEF_START_PROGRESS_M;
    var startDriftM as Float = DEF_START_DRIFT_M;

    var onThresholdM as Float = -4.5;
    var offThresholdM as Float = 3.0;
    var offClearM as Float = 1.8;

    var smoothedDistM as Float? = null;
    var distHistory as Array = [];
    var legMinDistM as Float = 0.0;
    var isDrifting as Boolean = false;
    var buoyChangedAtSec as Number = 0;
    var lastRecheckSec as Number = 0;
    var lastPulseSec as Number = -100;
    var pendingPulse as Boolean = false;

    var initialDistToActiveM as Float = 0.0;
    var hasSessionAnchor as Boolean = false;

    function initialize() {
        loadSettings();
    }

    function loadSettings() as Void {
        hapticMode = readStringProp("hapticMode", MODE_BEACON);
        trendWindowSec = readNumberProp("hapticTrendWindowSec", DEF_TREND_WINDOW_SEC);
        onScale = readFloatProp("hapticOnProgressScale", DEF_ON_SCALE);
        offScale = readFloatProp("hapticOffProgressScale", DEF_OFF_SCALE);
        offClearScale = readFloatProp("hapticOffClearScale", DEF_OFF_CLEAR_SCALE);
        legDriftBudgetM = readFloatProp("hapticLegDriftBudgetM", DEF_LEG_DRIFT_BUDGET_M);
        emaAlpha = readFloatProp("hapticEmaAlpha", DEF_EMA_ALPHA);
        pulseMinIntervalSec = readNumberProp("hapticPulseMinIntervalSec", DEF_PULSE_MIN_INTERVAL_SEC);
        startProgressM = readFloatProp("hapticStartProgressM", DEF_START_PROGRESS_M);
        startDriftM = readFloatProp("hapticStartDriftM", DEF_START_DRIFT_M);

        var windowFactor = trendWindowSec.toFloat() / 10.0;
        onThresholdM = -onScale * windowFactor;
        offThresholdM = offScale * windowFactor;
        offClearM = offClearScale * windowFactor;
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

    function resetForNewBuoy(rawDistM as Float, nowSec as Number) as Void {
        smoothedDistM = rawDistM;
        distHistory = [[nowSec, rawDistM]] as Array;
        legMinDistM = rawDistM;
        isDrifting = false;
        buoyChangedAtSec = nowSec;
        lastRecheckSec = nowSec;
        lastPulseSec = -100;
        pendingPulse = false;
    }

    function setSessionAnchor(initialDistM as Float) as Void {
        initialDistToActiveM = initialDistM;
        hasSessionAnchor = true;
    }

    function clearSessionAnchor() as Void {
        hasSessionAnchor = false;
        initialDistToActiveM = 0.0;
    }

    function update(
        nowSec as Number,
        rawDistM as Float,
        insideRadius as Boolean,
        sessionActive as Boolean,
        startAnchorActive as Boolean
    ) as Void {
        pendingPulse = false;

        if (!sessionActive || hapticMode.equals(MODE_OFF) || insideRadius) {
            return;
        }

        if (smoothedDistM == null) {
            resetForNewBuoy(rawDistM, nowSec);
            return;
        }

        smoothedDistM = (1.0 - emaAlpha) * smoothedDistM + emaAlpha * rawDistM;
        distHistory.add([nowSec, smoothedDistM]);

        trimHistory(nowSec);

        if (nowSec - buoyChangedAtSec < trendWindowSec) {
            return;
        }

        if (!isDrifting) {
            legMinDistM = rawDistM < legMinDistM ? rawDistM : legMinDistM;
        }

        if (nowSec - lastRecheckSec >= trendWindowSec) {
            lastRecheckSec = nowSec;
            var progress = computeProgress(nowSec);
            if (progress != null) {
                updateDriftState(progress, rawDistM, startAnchorActive);
            }
        }

        if (isDrifting && nowSec - lastPulseSec >= pulseMinIntervalSec) {
            pendingPulse = true;
            lastPulseSec = nowSec;
        }
    }

    function trimHistory(nowSec as Number) as Void {
        var cutoff = nowSec - trendWindowSec - 2;
        while (distHistory.size() > 2) {
            var oldest = distHistory[0] as Array;
            if ((oldest[0] as Number) >= cutoff) {
                break;
            }
            distHistory = distHistory.slice(1, distHistory.size());
        }
    }

    function computeProgress(nowSec as Number) as Float? {
        var targetSec = nowSec - trendWindowSec;
        var pastDist = findSmoothedAtSec(targetSec);
        if (pastDist == null || smoothedDistM == null) {
            return null;
        }
        return smoothedDistM - pastDist;
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
        if (bestDelta > trendWindowSec) {
            return null;
        }
        return bestDist;
    }

    function updateDriftState(
        progress as Float,
        rawDistM as Float,
        startAnchorActive as Boolean
    ) as Void {
        var budgetAlarm = rawDistM > legMinDistM + legDriftBudgetM;
        var trendAlarm = progress >= offThresholdM;
        var startDriftAlarm = startAnchorActive
            && rawDistM > initialDistToActiveM + startDriftM;

        if (isDrifting) {
            if (progress <= offClearM) {
                isDrifting = false;
                legMinDistM = rawDistM;
            }
        } else {
            var shouldDrift = trendAlarm || budgetAlarm || startDriftAlarm;
            if (startAnchorActive && !shouldDrift) {
                var madeProgress = rawDistM < initialDistToActiveM - startProgressM;
                var trendOk = progress <= offThresholdM;
                if (!madeProgress && trendOk && progress > onThresholdM) {
                    shouldDrift = false;
                }
            }
            if (shouldDrift) {
                isDrifting = true;
            }
        }
    }

    function shouldPulse() as Boolean {
        return pendingPulse;
    }

    function clearPulse() as Void {
        pendingPulse = false;
    }
}
