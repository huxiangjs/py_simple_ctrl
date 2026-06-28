#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .simple_ctrl import simple_ctrl_control

class simple_ctrl_smart_ir(simple_ctrl_control):
    '''
    Smart IR Control
    '''

    CLASS_ID = 0x03

    IR_CMD_GET_COUNT = 0x00
    IR_CMD_GET_ITEM = 0x01
    IR_CMD_TX_TEST = 0x02
    IR_CMD_SAVE = 0x03
    IR_CMD_REMOVE = 0x04
    IR_CMD_TX_SEND = 0x05

    IR_NOTIFY_TYPE_RX = 0x00
    IR_NOTIFY_TYPE_KEY = 0x01
    IR_NOTIFY_TYPE_TX = 0x02

    IR_RESULT_OK = 0x00
    IR_RESULT_FAIL = 0x01
    IR_RESULT_DONE = 0x02

    def __init__(self, info, passwd, on_change=None):
        def ir_on_change(event, data):
            if not on_change:
                return
            if event == 'notify':
                cmd = int(data[0])
                if cmd == simple_ctrl_smart_ir.IR_NOTIFY_TYPE_RX:
                    rx_count = int.from_bytes(data[1 : 5], 'little')
                    recv_len = int.from_bytes(data[5 : 7], 'little')
                    on_change('rx', (rx_count, recv_len))
                elif cmd == simple_ctrl_smart_ir.IR_NOTIFY_TYPE_KEY:
                    key_count = int.from_bytes(data[1 : 5], 'little')
                    on_change('key', key_count)
                elif cmd == simple_ctrl_smart_ir.IR_NOTIFY_TYPE_TX:
                    on_change('tx', None)
            else:
                on_change(event, data)
        super().__init__(info, passwd, ir_on_change)

    def _ir_response_check(self, cmd, data):
        if data[0] != cmd[0]:
            raise Exception('Command does not match')
        if data[1] != simple_ctrl_smart_ir.IR_RESULT_OK:
            raise Exception('Operation Failed')

    def get_count(self):
        '''
        Get the number of keys
        '''
        cmd = simple_ctrl_smart_ir.IR_CMD_GET_COUNT.to_bytes(1, 'little')
        response = self.request(cmd)
        self._ir_response_check(cmd, response)
        key_count = int.from_bytes(response[2 : 6], 'little')
        return key_count

    def get_item(self, index):
        '''
        Get the key information
        '''
        cmd = simple_ctrl_smart_ir.IR_CMD_GET_ITEM.to_bytes(1, 'little')
        i = index.to_bytes(4, 'little')
        response = self.request(cmd + i)
        self._ir_response_check(cmd, response)
        key_name = response[2 : ].decode('utf-8')
        return key_name

    def tx_test(self, rx_index):
        '''
        Send the key waveform you just learned
        '''
        cmd = simple_ctrl_smart_ir.IR_CMD_TX_TEST.to_bytes(1, 'little')
        i = rx_index.to_bytes(4, 'little')
        response = self.request(cmd + i)
        self._ir_response_check(cmd, response)

    def save(self, rx_index):
        '''
        Save the key waveforms you just learned
        '''
        cmd = simple_ctrl_smart_ir.IR_CMD_SAVE.to_bytes(1, 'little')
        i = rx_index.to_bytes(4, 'little')
        response = self.request(cmd + i)
        self._ir_response_check(cmd, response)

    def remove(self, key_name):
        '''
        Delete a key
        '''
        cmd = simple_ctrl_smart_ir.IR_CMD_REMOVE.to_bytes(1, 'little')
        name = key_name.encode('utf-8')
        response = self.request(cmd + name)
        self._ir_response_check(cmd, response)

    def tx_send(self, key_name):
        '''
        Send the key waveform
        '''
        cmd = simple_ctrl_smart_ir.IR_CMD_TX_SEND.to_bytes(1, 'little')
        name = key_name.encode('utf-8')
        response = self.request(cmd + name)
        self._ir_response_check(cmd, response)
