import socket
import time
import logging

import viewserver_parser as vs_parser

logger = logging.getLogger('viewserver')


class ViewServerException(Exception):
    pass


class ViewServerController:
    DUMP_ALL_CMD = "DUMP -1"
    GET_FOCUS_CMD = "GET_FOCUS"
    LIST_VIEW_CMD = "LIST"
    DUMP_VIEW_CMD = "DUMP"

    server_cmd = "SERVER"
    protocol_cmd = "PROTOCOL"
    autolist_cmd = "AUTOLIST"

    # ViewDebug Command
    capture_cmd = "CAPTURE"
    invalidate_cmd = "INVALIDATE"
    profile_cmd = "PROFILE"

    def __init__(self, pilot):
        self.pilot = pilot

    def open(self):
        self.__stop_service()
        self.__start_service()
        self.__forward_port()

    def close(self):
        self.__stop_service()

    def __start_service(self):
        logger.info("Starting ViewServer service...")
        start_cmd = ['shell', 'service', 'call', 'window',
                     '1', 'i32', '4939']

        self.pilot.adb_command(start_cmd)
        time.sleep(0.5)
        # the output of starting/stopping viewserver can be:
        # "Result: Parcel(00000000 00000001   '........')"
        # or
        # "Result: Parcel(00000000 00000000   '........')""

    def __stop_service(self):
        stop_cmd = ['shell', 'service', 'call', 'window', '2']
        self.pilot.adb_command(stop_cmd)
        time.sleep(0.5)

    def __forward_port(self):
        forward_cmd = ['forward', 'tcp:%s' % self.pilot.view_server_port,
                       'tcp:4939']

        res = self.pilot.adb_command(forward_cmd, blocking=True)
        if res != 0:
            raise ViewServerException('Could not forward port %s', forward_cmd)

    def get_data_by_socket(self, command):
        s = socket.socket()
        s.connect((self.pilot.device_address, self.pilot.view_server_port))
        # s.setblocking(0)
        sent = s.sendall(command + '\n')
        if sent is not None:
            raise ViewServerException("ViewServer data not sent")

        all_data = ''
        while True:
            data = s.recv(2048)
            if not data:
                break
            all_data += data
        s.close()
        return all_data.strip()

    def __dump_all(self):
        data = self.get_data_by_socket(self.DUMP_ALL_CMD)
        return data

    def dump_view_by_hashcode(self, hashcode):
        data = self.get_data_by_socket(self.DUMP_VIEW_CMD + ' ' + hashcode)
        return data

    def get_focus_activity(self):
        data = self.get_data_by_socket(self.GET_FOCUS_CMD)
        if len(data.split(' ')) < 2:
            return ''

        if not data:
            return ''

        focus_activity = data.split(' ')[1]
        if '/' in focus_activity:
            return focus_activity.split('/')[1]
        else:
            return focus_activity

    def get_activity_list(self):
        data = self.get_data_by_socket(self.LIST_VIEW_CMD)
        activity_list = data.split('\n')
        # pop the last element (it is the 'DONE' string)
        activity_list.pop()
        activity_list_pairs = [tuple(a.split(' ')) for a in activity_list]
        return activity_list_pairs

    def refresh_view(self):
        # dump the displayed views
        data = self.__dump_all()
        # rebuild the tree using the dumped data
        self.tree_nodes_list = vs_parser.build_tree(data)
