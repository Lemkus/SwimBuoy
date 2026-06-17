import Toybox.Lang;
using Toybox.Math;

module GeoUtils {
    const EARTH_RADIUS_M = 6371000.0;

    function toRadians(degrees as Float) as Float {
        return degrees * Math.PI / 180.0;
    }

    function toDegrees(radians as Float) as Float {
        return radians * 180.0 / Math.PI;
    }

    function haversineDistanceM(
        lat1 as Float,
        lon1 as Float,
        lat2 as Float,
        lon2 as Float
    ) as Float {
        var dLat = toRadians(lat2 - lat1);
        var dLon = toRadians(lon2 - lon1);
        var a = Math.sin(dLat / 2.0) * Math.sin(dLat / 2.0)
            + Math.cos(toRadians(lat1)) * Math.cos(toRadians(lat2))
            * Math.sin(dLon / 2.0) * Math.sin(dLon / 2.0);
        var c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));
        return EARTH_RADIUS_M * c;
    }

    function bearingDegrees(
        lat1 as Float,
        lon1 as Float,
        lat2 as Float,
        lon2 as Float
    ) as Float {
        var phi1 = toRadians(lat1);
        var phi2 = toRadians(lat2);
        var dLon = toRadians(lon2 - lon1);
        var y = Math.sin(dLon) * Math.cos(phi2);
        var x = Math.cos(phi1) * Math.sin(phi2)
            - Math.sin(phi1) * Math.cos(phi2) * Math.cos(dLon);
        var bearing = toDegrees(Math.atan2(y, x));
        if (bearing < 0.0) {
            bearing += 360.0;
        }
        return bearing;
    }

    function normalizeAngleDegrees(angle as Float) as Float {
        var result = angle;
        while (result >= 360.0) {
            result -= 360.0;
        }
        while (result < 0.0) {
            result += 360.0;
        }
        return result;
    }

    function relativeBearingDegrees(
        bearingToTarget as Float,
        heading as Float?
    ) as Float {
        if (heading == null) {
            return bearingToTarget;
        }
        return normalizeAngleDegrees(bearingToTarget - heading);
    }
}
