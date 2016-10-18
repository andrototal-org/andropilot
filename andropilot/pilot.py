import datetime
import logging
import time
import subprocess

from notification import NotificationManager
from controllers.monkey_controller import MonkeyController
from controllers.viewserver_controller import ViewServerController

SHORT_TIMEOUT = 60
MEDIUM_TIMEOUT = 120
LONG_TIMEOUT = 240

TIMEOUT = MEDIUM_TIMEOUT

DEFAULT_SLEEP_TIME = 0.5  # 500 mseconds

logger = logging.getLogger('andropilot')


class AndroPilotException(Exception):
    pass


class AndroPilot(object):

    def __init__(self, device_name="emulator-5554", device_address="127.0.0.1",
                 view_server_port=4939, monkey_server_port=12345):
        # set the device under test parameters
        self.device_name = device_name
        self.device_address = device_address
        self.view_server_port = view_server_port
        self.monkey_server_port = monkey_server_port

    def open(self):
        # set and initialize the monkey controller instance
        self.monkey_controller = MonkeyController(self)
        self.monkey_controller.open()
        # set and initialize the ViewServer controller instance
        self.viewserver_controller = ViewServerController(self)
        self.viewserver_controller.open()

        self.device_api_level = self.monkey_controller.get_api_level()
        logger.info("API level: %s", self.device_api_level)

        self.display_width = self.monkey_controller.get_display_width()
        self.display_height = self.monkey_controller.get_display_height()

        logger.info("Display size (width, height): %s, %s",
                    self.display_width, self.display_height)
        focus_activity = self.viewserver_controller.get_focus_activity()

        logger.info("Current focus activity: %s", focus_activity)
        # set the notification manager instance
        self.notification_manager = NotificationManager(self)

    # context management methods #
    def __delete__(self):
        self.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()
    ##############################

    def refresh(self):
        logger.debug("View tree refresh START")
        self.viewserver_controller.refresh_view()
        logger.debug("View tree refresh COMPLETE")

    def close(self):
        try:
            self.monkey_controller.close()
        except:
            pass
        try:
            self.viewserver_controller.close()
        except:
            try:
                # wait a sec and retry
                time.sleep(1)
                self.viewserver_controller.close()
            except:
                pass

    def install_package(self, package_name):
        cmd = ['install', '-r', package_name]
        ret_code = self.adb_command(cmd)
        if ret_code == 0:
            logger.info(
                'Package %s correctly installed on device', package_name)
        else:
            logger.warning("Package %s NOT installed on device", package_name)
            raise AndroPilotException("Package not installed correctly")

    def push_file(self, src, dst='/sdcard/'):
        cmd = ['push', src, dst]
        ret_code = self.adb_command(cmd)
        if ret_code == 0:
            logger.info('File %s correctly pushed to %s', src, dst)
        else:
            logger.warning("File %s NOT pushed to %s", src, dst)
            raise AndroPilotException("File not correctly copied")

    def start_activity(self, package_name, activity_name):
        cmd = ['shell', 'am', 'start', '-W', '-n',
               package_name + '/' + activity_name]
        output = self.adb_command(cmd, need_result=True)

        if 'Complete' in output:
            logger.debug('Activity %s/%s started', package_name, activity_name)
        else:
            logger.warning(
                'Activity %s/%s NOT started', package_name, activity_name)
            raise AndroPilotException('Activity not started')

# GETTERS ##
    def get_view_by_id(self, ident, prefix="id"):
        """
        Get the view node with the passed id.
        Returns None if a node with such id is not found.
        """
        real_id = prefix + '/' + ident
        return next((n for n in self.viewserver_controller.tree_nodes_list
                     if n.mId == real_id and n.isShown is True), None)

    def get_view_by_text(self, text, partial_matching=True):
        if partial_matching:
            check = lambda x, y: (y is not None) and (x in y)
        else:
            check = lambda x, y: (x == y)

        return next((n for n in self.viewserver_controller.tree_nodes_list
                     if n.isShown is True and check(text, n.mText)), None)

    def get_focus_activity(self):
        return self.viewserver_controller.get_focus_activity()

    def get_activity_list(self):
        activity_pairs = self.viewserver_controller.get_activity_list()
        view_list = [{'hashcode': a[0], 'classname': a[1]}
                     for a in activity_pairs]

        return view_list

# EXISTENCE CHECKING METHODS #
    def exist_view_by_classname(self, class_name):
        for node in self.viewserver_controller.tree_nodes_list:
            if class_name == node.mClassName:
                return True
        return False

    def exist_view_by_text(self, text, partial_matching=True):
        if self.get_view_by_text(text, partial_matching) is not None:
            return True
        return False

    def exist_view_by_id(self, id):
        if self.get_view_by_id(id) is not None:
            return True
        return False

# CLICK METHODS #
    def click_view_by_id(self, ident):
        if not ident:
            raise AndroPilotException("Identifier not valid")

        view = self.get_view_by_id(ident)
        # node not found
        if view is None:
            raise AndroPilotException("View not found")

        self.monkey_controller.tap(view.mLocation.x, view.mLocation.y)

    def click_view_by_text(self, text, partial_matching=True):
        if not text:
            raise AndroPilotException("Empty text is not valid")

        view = self.get_view_by_text(text, partial_matching)

        # node not found
        if view is None:
            raise AndroPilotException("View not found")
        self.monkey_controller.tap(view.mLocation.x, view.mLocation.y)

    def press_home(self):
        self.monkey_controller.press("home")

    def press_back(self):
        self.monkey_controller.press("back")

    def press_menu(self):
        self.monkey_controller.press("menu")

    def tap_on_coordinates(self, x, y):
        self.monkey_controller.tap(x, y)

# WAITING METHODS #

    def wait_for_activity(self, activity_name, timeout=TIMEOUT, critical=True):
        """
            Wait for a given activity to show up.
        """
        SLEEP_TIME = 0.5  # 500 ms
        end_time = datetime.datetime.now() + \
            datetime.timedelta(seconds=timeout)
        while datetime.datetime.now() <= end_time:
            current_activity = self.get_focus_activity()
            if current_activity == activity_name:
                logger.debug("Activity found: %s.", current_activity)
                return True
            time.sleep(SLEEP_TIME)
        logger.debug("Activity %s not found.", activity_name)
        if critical is True:
            raise AndroPilotException(
                "Activity %s not found." % activity_name)
        else:
            return False

    def wait_for_dialog_to_close(self, timeout=SHORT_TIMEOUT):
        """
            Wait for a dialog window to close.
        """
        SLEEP_TIME = 0.2  # 200 mseconds
        views_count_before = len(self.get_activity_list())

        end_time = datetime.datetime.now() + \
            datetime.timedelta(seconds=timeout)

        while datetime.datetime.now().time() <= end_time.time():
            views_count_now = len(self.get_activity_list())

            if views_count_before < views_count_now:
                views_count_before = views_count_now

            if views_count_before > views_count_now:
                logger.debug("Detected dialog view closing.")
                return True
            time.sleep(SLEEP_TIME)

        return False

    def wait_for_text(
            self, text, timeout=TIMEOUT,
            sleep_time=DEFAULT_SLEEP_TIME):
        """
            Wait for a given text to appear in some view.
            Internally it keeps dumping the view hierarchy until the text
            is found or the timout is reached.
        """
        end_time = datetime.datetime.now() + \
            datetime.timedelta(seconds=timeout)
        while datetime.datetime.now().time() <= end_time.time():
            self.refresh()

            r = self.exist_view_by_text(text, True)
            if r is True:
                return True
            time.sleep(sleep_time)
        return False

    def wait_for_custom_event(
            self, event_checker,
            timeout=TIMEOUT, refresh=False):
        """
            Wait for a custom event passed by the user.
            event_checker is a boolean function which checks
            whether the event has occurred or not.
        """
        SLEEP_TIME = 0.2  # 200 mseconds
        end_time = datetime.datetime.now() + \
            datetime.timedelta(seconds=timeout)
        while datetime.datetime.now().time() <= end_time.time():
            if refresh:
                self.refresh()
            result = event_checker()
            if result:
                logger.debug("Custom event found")
                return result
            time.sleep(SLEEP_TIME)
        logger.debug("Custom event not found. Timeout reached")
        return False

    def get_logcat(self, filename, remove=False):
        """
        to get the logcat this function will in turn:
            - store logcat dump to data/user on Android
            - pull the resulting file into a temporary file
        this is quicker than just reading stdout
        of the adb tool

        args:
            remove: boolean which defines if the logcat
                    should be removed from the
                    device after reading it
        """
        LOGCAT_REMOTE_PATH = '/data/user/logcat.out'
        self.adb_command(
            ['shell', 'logcat', '-d', '-f', LOGCAT_REMOTE_PATH, '-v', 'brief',
             'Choreographer:S', 'WindowManager:S', 'MonkeyStub:S'
             'ViewServer:S', 'AndroTotal:S', 'dalvikvm:S'])
        self.adb_command(['pull', LOGCAT_REMOTE_PATH, filename])

        if remove:
            self.adb_command(['shell', 'rm', LOGCAT_REMOTE_PATH])

    def take_screenshot(self, filename, use_screencap=True):
        """
            on old android OS versions (< 3.0)  there's no screencap
            use_screencap can be set to false to use a fallback method
            with screenshot.jar
            [uses the same method as ddmlib, but sometimes the java process
            crashes so its better to stick to screencap as long as possible]
        """
        if use_screencap is False:
            import os
            pilot_path = os.path.dirname(__file__)
            screenshot_jar_path = os.path.join(pilot_path, 'screenshot.jar')

            logger.info(
                "Taking %s screenshot to %s", self.device_name, filename)
            cmd_screenshot = ['java', '-jar', screenshot_jar_path, '-s',
                              self.device_name, filename]
            res = subprocess.check_output(
                cmd_screenshot, stderr=subprocess.STDOUT)
            logger.debug(res)
        else:
            self.adb_command(
                'shell screencap -p /data/user/snapshot.png'.split())
            self.adb_command(
                ('pull /data/user/snapshot.png %s' % filename).split())
            self.adb_command('shell rm /data/user/snapshot.png'.split())
        return filename

    def adb_command(self, cmd, stdin=None, stdout=None, stderr=None,
                    blocking=True, need_result=False):

        adb_cmd = ['adb', '-s', self.device_name] + cmd
        logger.debug("Executing command: " + ' '.join(adb_cmd))

        if need_result:
            res = subprocess.check_output(adb_cmd, stdin=stdin, stderr=stderr)
            return res
        else:
            if blocking:
                res = subprocess.call(
                    adb_cmd, stdin=stdin, stdout=stdout, stderr=stderr)
                return res
            else:
                proc = subprocess.Popen(
                    adb_cmd, stdin=stdin, stdout=stdout, stderr=stderr)
                return proc

    def type(self, text):
        self.monkey_controller.type(text)
