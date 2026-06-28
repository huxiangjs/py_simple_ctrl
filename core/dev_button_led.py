#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .simple_ctrl import simple_ctrl_control

class simple_ctrl_button_led(simple_ctrl_control):
    '''
    Button LED Control
    '''

    CLASS_ID = 0x02

    LED_CMD_SET_COLOR = 0x00
    LED_CMD_GET_COLOR = 0x01

    LED_RESULT_OK = 0x00
    LED_RESULT_FAIL = 0x01

    def __init__(self, info, passwd, on_change=None):
        def led_on_change(event, data):
            if not on_change:
                return
            if event == 'notify':
                b = int(data[0])
                g = int(data[1])
                r = int(data[2])
                on_change('color', (r, g, b))
            else:
                on_change(event, data)
        super().__init__(info, passwd, led_on_change)

    def _led_response_check(self, cmd, data):
        if data[0] != cmd[0]:
            raise Exception('Command does not match')
        if data[1] != simple_ctrl_button_led.LED_RESULT_OK:
            raise Exception('Operation Failed')

    def set_color(self, color):
        '''
        Set the LED Color
        '''
        cmd = simple_ctrl_button_led.LED_CMD_SET_COLOR.to_bytes(1, 'little')
        _r, _g, _b = color
        r = _r.to_bytes(1, 'little')
        g = _g.to_bytes(1, 'little')
        b = _b.to_bytes(1, 'little')
        response = self.request(cmd + b + g + r)
        self._led_response_check(cmd, response)

    def get_color(self):
        '''
        Get the LED Color
        '''
        cmd = simple_ctrl_button_led.LED_CMD_GET_COLOR.to_bytes(1, 'little')
        response = self.request(cmd)
        self._led_response_check(cmd, response)
        b = int(response[2])
        g = int(response[3])
        r = int(response[4])
        return (r, g, b)
