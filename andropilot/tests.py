import logging
import time
import unittest

from andrototal.andropilot import pilot


class TestAndroPilot(unittest.TestCase):

    def setUp(self):
        rl = logging.getLogger()
        rl.addHandler(logging.StreamHandler())
        rl.setLevel(logging.DEBUG)

    def test_get_properties(self):
        with pilot.AndroPilot('emulator-5554', 'localhost', 1223, 1224) as p:
            h = p.monkey_controller.get_display_height()
            w = p.monkey_controller.get_display_width()
            self.assertEqual(w, 240)
            self.assertEqual(h, 320)

            p.monkey_controller.swipe_left()
            time.sleep(1)
            p.monkey_controller.swipe_right()

    def test_monkey_restart(self):
        print "Enter test_get_properties"
        with pilot.AndroPilot() as p:
            p.monkey_controller.restart()
        print "Exit test_get_properties"

    def test_viewserver_get_activity_list(self):
        with pilot.AndroPilot() as p:
            activities = p.viewserver_controller.get_activity_list()
            print activities

    def test_viewserver_refresh(self):
        with pilot.AndroPilot() as p:
            p.refresh()

    def test_multiple(self):
        # with pilot.AndroPilot() as p:
        #     p.viewserver_controller.get_activity_list()
        # with pilot.AndroPilot() as p:
        #     p.monkey_controller.restart()
        with pilot.AndroPilot() as p:
            p.refresh()
            v = p.get_view_by_id('cling_dismiss')
            print v


if __name__ == '__main__':
    unittest.main()
