import datetime
import time
import logging

from controllers import viewserver_parser as vs_parser

SHORT_TIMEOUT = 60
MEDIUM_TIMEOUT = 120
LONG_TIMEOUT = 240

TIMEOUT = MEDIUM_TIMEOUT

logger = logging.getLogger(__name__)


STATUS_BAR_CLASSNAME_10 = "StatusBarExpanded"
STATUS_BAR_CLASSNAME_16 = "StatusBar"


class NotificationManager:

    def __init__(self, pilot):
        self.pilot = pilot

        self.status_bar_class_name = "com.android.systemui.statusbar.ExpandedView"
        self.carrierlabel_class_name = "com.android.systemui.statusbar.CarrierLabel"

        self.ongoing_text = "Ongoing"
        self.ongoing_class_name = "android.widget.TextView"
        self.ongoing_id = "id/ongoingTitle"

        self.NOTIFICATION_CLASS_NAME = "android.widget.TextView"
        self.notifications_id = "id/latestTitle"

        self.ITEM_CLASS_NAME = 'com.android.systemui.statusbar.LatestItemView'
        self.item_id = "id/content"

        self.ongoing_items = []
        self.notification_items = []

    def open_notification_bar(self):
        logger.info("Opening notification bar")
        start_x = self.pilot.display_width / 2
        start_y = 0
        end_x = start_x
        # drag till 3/4 of the screen height
        end_y = self.pilot.display_height * 3 / 4
        res = self.pilot.monkey_controller.drag(
            start_x, start_y, end_x, end_y, 0.5, 3)
        time.sleep(0.5)
        return True

    def _refresh10(self):
        view_list = self.pilot.get_activity_list()
        hashcode = next(
            v['hashcode'] for v in view_list if v['classname'] == STATUS_BAR_CLASSNAME_10)

        data = self.pilot.viewserver_controller.dump_view_by_hashcode(hashcode)
        # build the view notification bar view tree
        self.tree_nodes_list = vs_parser.build_tree(data)

        # now get all the notification items
        # self.notification_items is a list of dictionaries, each one containing the
        # the notification title, message and view node
        self.notification_items = []

        # retrieve all the "ongoing" notification items
        ongoing_items_root = next(
            (n for n in self.tree_nodes_list if n.mId == 'id/ongoingItems'),
            None)
        for node in ongoing_items_root.get_all_children():
            if node.mClassName == "com.android.systemui.statusbar.LatestItemView":
                n = {'title': node.get_children_by_id('title')[0].mText,
                     'message': node.get_children_by_id('text')[0].mText,
                     'node': node
                     }
                self.notification_items.append(n)

        # retrieve all the "default" notification items
        latest_items_root = next(
            (n for n in self.tree_nodes_list if n.mId == 'id/latestItems'),
            None)
        for node in latest_items_root.get_all_children():
            if node.mClassName == "com.android.systemui.statusbar.LatestItemView":
                n = {'title': node.get_children_by_id('title')[0].mText,
                     'message': node.get_children_by_id('text')[0].mText,
                     'node': node
                     }
                self.notification_items.append(n)

    def _refresh16(self):
        view_list = self.pilot.get_activity_list()
        hashcode = next(
            v['hashcode'] for v in view_list if v['classname'] == STATUS_BAR_CLASSNAME_16)

        data = self.pilot.viewserver_controller.dump_view_by_hashcode(hashcode)
        # build the view notification bar view tree
        self.tree_nodes_list = vs_parser.build_tree(data)
        # now get all the notification items
        self.notification_items = []

        # on the Android API 16 there is no difference between ongoing
        # and default notification view elements
        for node in self.tree_nodes_list:
            if node.mId == "id/status_bar_latest_event_content":
                n = {'title': node.get_children_by_id('title')[0].mText,
                     'message': node.get_children_by_id('text')[0].mText,
                     'node': node
                     }
                self.notification_items.append(n)

    def refresh(self):
        logger.debug("Notifications dump START.")
        # choose the right refresh method based on the
        # Android API level
        if self.pilot.device_api_level == 10:
            self._refresh10()
        elif self.pilot.device_api_level == 16:
            self._refresh16()
        logger.debug("Notifications dump COMPLETE.")

    def get_notifications_by_message(self, text, partial_matching=True):
        if partial_matching:
            check = lambda x, y: (x in y)
        else:
            check = lambda x, y: (x == y)

        return [n for n in self.notification_items if check(
            text, n['message'])]

    def get_notifications_by_title(self, text, partial_matching=True):
        if partial_matching:
            check = lambda x, y: (x in y)
        else:
            check = lambda x, y: (x == y)

        return [n for n in self.notification_items if check(text, n['title'])]

    def click_notification_by_id(self, id):
        notification_node = (
            n['node'] for n in self.notification_items if n['node'].mId == id
        ).next()
        if notification_node is None:
            return False

        location = self.__get_real_location(notification_node.mLocation)
        self.open_notification_bar()
        return self.pilot.monkey_controller.tap(location.x, location.y)

    def wait_for_notification_by_message(
            self, text, timeout=TIMEOUT, partial_matching=True):
        SLEEP_TIME = 0.2  # 200 mseconds
        end_time = datetime.datetime.now() + \
            datetime.timedelta(seconds=timeout)
        while datetime.datetime.now().time() <= end_time.time():
            self.refresh()

            if len(self.get_notifications_by_message(
                    text, partial_matching)) > 0:
                return True
            time.sleep(SLEEP_TIME)
        return False

    def wait_for_notification_by_title(
            self, text, timeout=TIMEOUT, partial_matching=True):
        SLEEP_TIME = 0.2  # 200 mseconds
        end_time = datetime.datetime.now() + \
            datetime.timedelta(seconds=timeout)
        while datetime.datetime.now().time() <= end_time.time():
            self.refresh()

            if len(self.get_notifications_by_title(
                    text, partial_matching)) > 0:
                return True
            time.sleep(SLEEP_TIME)
        return False

    def __get_real_location(self, location):
        real_location = vs_parser.Point()
        real_location.x = location.x
        real_location.y = location.y + self.statusbar_height

        return real_location
