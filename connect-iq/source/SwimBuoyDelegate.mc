import Toybox.WatchUi;
import Toybox.Lang;

class SkipConfirmDelegate extends WatchUi.ConfirmationDelegate {
    var view as SwimBuoyView;

    function initialize(swimView as SwimBuoyView) {
        ConfirmationDelegate.initialize();
        view = swimView;
    }

    function onResponse(response as WatchUi.Confirm) as Boolean {
        if (response == WatchUi.CONFIRM_YES) {
            view.onSkipBuoy();
        }
        WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        return true;
    }
}

class SwimBuoyDelegate extends WatchUi.BehaviorDelegate {
    var view as SwimBuoyView;

    function initialize(swimView as SwimBuoyView) {
        BehaviorDelegate.initialize();
        view = swimView;
    }

    function onBack() as Boolean {
        view.finishActivityRecording(true);
        WatchUi.popView(WatchUi.SLIDE_RIGHT);
        return true;
    }

    function onMenu() as Boolean {
        if (!view.routeEngine.isSessionActive()) {
            return true;
        }
        WatchUi.pushView(
            new WatchUi.Confirmation(WatchUi.loadResource(Rez.Strings.SkipConfirm) as String),
            new SkipConfirmDelegate(view),
            WatchUi.SLIDE_IMMEDIATE
        );
        return true;
    }
}
