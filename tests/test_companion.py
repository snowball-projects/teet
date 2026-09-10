import io
import json
import threading
import unittest
from unittest.mock import Mock, patch
import companion

class CompanionTests(unittest.TestCase):
    def test_command_bounds(self):
        for v in [float('nan'), float('inf'), True, 0, 61, '1']:
            with self.assertRaises(ValueError): companion.validate_command({'mode':'repeat','key':'e','interval':v})
        for body in [{'mode':'shell','key':'e','interval':1}, {'mode':'repeat','key':'cmd','interval':1}, {}]:
            with self.assertRaises(ValueError): companion.validate_command(body)
        self.assertEqual(companion.validate_command({'mode':'repeat','key':'e','interval':1.1})['interval'],1.1)

    def request(self, headers, body=b'{}', path='/api/stop'):
        h=object.__new__(companion.Handler);h.headers=headers;h.path=path;h.rfile=io.BytesIO(body);h.reply=Mock();h.controller=Mock()
        h.controller.status.return_value={'running':False}
        h.do_POST()
        return h

    def test_cross_origin_and_rebinding_never_control_input(self):
        for headers in [ {'Host':companion.HOST,'Origin':'https://example.com'}, {'Host':'evil.example:8784','Origin':companion.ORIGIN}, {'Host':companion.HOST} ]:
            h=self.request(headers);self.assertEqual(h.reply.call_args.args[0],403);h.controller.stop.assert_not_called()

    def test_local_stop_and_request_size(self):
        good={'Host':companion.HOST,'Origin':companion.ORIGIN,'Content-Type':'application/json','Content-Length':'2'}
        h=self.request(good);h.controller.stop.assert_called_once();self.assertEqual(h.reply.call_args.args[0],200)
        h=self.request({**good,'Content-Length':'9999'});h.controller.stop.assert_not_called();self.assertEqual(h.reply.call_args.args[0],400)

    def test_foreground_required_and_escape_stops(self):
        c=companion.Controller();c.event=Mock();c.event.wait.return_value=False;c.event.is_set.side_effect=[False,False]
        keyboard=Mock();keyboard.is_pressed.side_effect=[False,True]
        mouse=Mock();windows=Mock();windows.getActiveWindow.return_value=Mock(title='Notes')
        c.repeat({'key':'e','interval':1},keyboard,mouse,windows)
        mouse.press.assert_not_called();self.assertEqual(c.message,'Stopped')

    def test_stop_before_countdown_sends_no_input(self):
        c=companion.Controller();c.event.set();mouse=Mock()
        c.repeat({'key':'e','interval':1},Mock(),mouse,Mock());mouse.press.assert_not_called()

    def test_non_windows_start_is_explicit(self):
        with patch('companion.sys.platform','darwin'):
            with self.assertRaises(ValueError): companion.Controller().start({'mode':'repeat','key':'e','interval':1})

if __name__=='__main__':unittest.main()
