import re
import subprocess
import socket
import logging

import time

logger = logging.getLogger('monkey_controller')


class MonkeyException(Exception):
    pass


class MonkeyController:

    '''
    This class can send events to monkey server in device
    '''

    def __init__(self, pilot):
        self.pilot = pilot

    def open(self):
        """
        Initialize the MonkeyController instance by performing
        all the required operations (starting monkey service,
        forwarding port on the emulator, opening socket connection).
        """
        self.__start_service()
        # sleep some time waiting for the monkey service to start
        time.sleep(3)
        self.__forward_port()
        self.monkey_socket = self.__open_socket_connection()

    def __start_service(self):
        """
        Start the monkey service on the emulator.
        """
        logger.info("Starting monkey service...")
        monkey_cmd = ['adb', '-s', self.pilot.device_name, 'shell',
                      'monkey', '--port', str(self.pilot.monkey_server_port)]
        # we store the monkey service process instance
        self.monkey_binder_process = subprocess.Popen(
            monkey_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        # best we can do sleep 1 second as the sdk monkey runner... that SUCKS!
        # https://android.googlesource.com/platform/sdk/+/fd836ebcd985b08baa85caad03f9ad86eb40ef83/monkeyrunner/src/com/android/monkeyrunner/adb/AdbMonkeyDevice.java
        time.sleep(1)
        if self.monkey_binder_process.poll() is not None:
            raise MonkeyException('Unable to start monkey server')

    def __forward_port(self):
        """
        Simply open the needed port on the running emulator
        by calling the 'abd forward' command.
        """
        forward_cmd = ['forward', 'tcp:' + str(self.pilot.monkey_server_port),
                       'tcp:' + str(self.pilot.monkey_server_port)]
        res = self.pilot.adb_command(forward_cmd)
        if res != 0:
            raise MonkeyException(
                'Some error occurred while forwarding the Monkey port')

    def __open_socket_connection(self):
        """
        Open a socket connection to the monkey service running
        on the emulator.
        """
        logger.info("Connecting to monkey through socket (%s:%s)",
                    self.pilot.device_address,
                    self.pilot.monkey_server_port)

        s = socket.socket()
        s.connect((self.pilot.device_address, self.pilot.monkey_server_port))
        # s.setblocking(0)

        return s

    def send_by_socket(self, command):
        """
        Send a command through the already open socket connection.

        Args:
            command (str): the string command to be sent.
        """

        MAX_ATTEMPTS = 3
        logger.debug("Sending command '%s' via socket %s:%s",
                     command, self.pilot.device_address,
                     self.pilot.monkey_server_port)

        # try sending the command twice (restart monkey connection if it
        #    does not work the first time)
        attempts = 0
        while attempts < MAX_ATTEMPTS:
            try:
                self.monkey_socket.sendall(command + "\n")
                res = self.monkey_socket.recv(1024)
                break
            except socket.error:
                logger.exception(
                    'Exception while sending command %s' % command)
                self.restart()
                attempts = attempts + 1
                if attempts >= MAX_ATTEMPTS:
                    raise

        return res

    def get_property_by_socket(self, property_name):
        """
        Get a property value through the already open telnet connection.

        Args:
            property_name (str): the name of the property to be retrieved.
        Returns:
            the retrieved value of the property
        """
        logger.debug(
            "Getting property %s via socket %s:%s",
            property_name, self.pilot.device_address,
            self.pilot.monkey_server_port)

        res = self.send_by_socket("getvar %s" % property_name)
        # sleep some time waiting for command execution
        if 'ERROR' in res:
            logging.warning('Error in data returned by monkey (%s)',
                            res.rstrip("\n"))
            raise MonkeyException('Bad data')

        return res.rstrip("\n").lstrip("OK:")

    def get_display_width(self):
        res = self.get_property_by_socket("display.width")
        if res:
            return int(res)
        else:
            return None

    def get_display_height(self):
        res = self.get_property_by_socket("display.height")
        if res:
            return int(res)
        else:
            return None

    def get_api_level(self):
        res = self.get_property_by_socket('build.version.sdk')
        if res:
            return int(res)
        else:
            return None

    def restart(self):
        logger.info("Restarting monkey service...")
        self.close()
        self.open()

    def close(self):
        logger.info("Closing monkey service...")
        try:
            self.monkey_socket.sendall("quit\n")
        except:
            logger.warning("Exception while sending command quit")
            pass
        try:
            self.monkey_binder_process.terminate()
        except:
            pass

    def done(self):
        # close current session, but it will not close socket binding
        self.send_by_socket("done")

    def wake(self):
        self.send_by_socket("wake")

    def tap(self, x, y):
        command = "tap %s %s" % (x, y)
        self.send_by_socket(command)

    def press(self, name):
        command = "press %s" % name
        self.send_by_socket(command)

    def _touch_down(self, x, y):
        command = "touch down %s %s" % (x, y)
        self.send_by_socket(command)

    def _touch_up(self, x, y):
        command = "touch up %s %s" % (x, y)
        self.send_by_socket(command)

    def _touch_move(self, x, y):
        command = "touch move %s %s" % (x, y)
        self.send_by_socket(command)

    def __drag_start(self, x, y):
        self._touch_down(x, y)
        self._touch_move(x, y)

    def __drag_end(self, x, y):
        self._touch_move(x, y)
        self._touch_up(x, y)

    def __drag_step(self, x, y):
        self._touch_move(x, y)

    def drag(self, fromX, fromY, toX, toY, duration=0.5, steps=10):
        sleep_time = duration / steps

        deltaX = (toX - fromX) / steps
        deltaY = (toY - fromY) / steps

        self.__drag_start(fromX, fromY)
        index = 1
        while steps > index:
            self.__drag_step(
                int(fromX + deltaX * index), int(fromY + deltaY * index))
            index += 1
            time.sleep(sleep_time)

        self.__drag_end(toX, toY)

    def swipe_left(self):
        start_x = self.pilot.display_width - 10
        end_x = 10
        start_y = self.pilot.display_height / 2
        end_y = self.pilot.display_height / 2
        self.drag(start_x, start_y, end_x, end_y, 0.5, 5)
        # time.sleep(0.5)

    def swipe_right(self):
        start_x = 10
        end_x = self.pilot.display_width - 10
        start_y = self.pilot.display_height / 2
        end_y = self.pilot.display_height / 2
        self.drag(start_x, start_y, end_x, end_y, 0.5, 5)
        # time.sleep(0.5)

    def swipe_up(self):
        start_x = end_x = self.pilot.display_width / 2

        start_y = self.pilot.display_height - 10
        end_y = 10

        self.drag(start_x, start_y, end_x, end_y, 0.5, 5)
        # time.sleep(0.5)

    def swipe_down(self):
        start_x = end_x = self.pilot.display_width / 2

        start_y = 10
        end_y = self.pilot.display_height - 10

        self.drag(start_x, start_y, end_x, end_y, 0.5, 5)
        # time.sleep(0.5)

#     def key_down(self, name):
#         command = "key down %s" % name
#         return self.send_by_socket(command)

#     def key_up(self, name):
#         command = "key up %s" % name
#         return self.send_by_socket(command)

    def type(self, text):
        words = re.split('(\s+)', text)
        words = [62 if w == ' ' else w for w in words]

        for w in words:
            if isinstance(w, (int, long)):
                cmd = "key down %s" % w
            else:
                cmd = "type %s" % w
            self.send_by_socket(cmd)
