#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .simple_ctrl import simple_ctrl_control

class simple_ctrl_sensor(simple_ctrl_control):
    '''
    Sensor Control
    '''

    CLASS_ID = 0x04

    SENSOR_TYPE_BRIGHTNESS = 0x01
    SENSOR_TYPE_HUMIDITY = 0x02
    SENSOR_TYPE_TEMPERATURE = 0x03

    SENSOR_CMD_GET_COUNT = 0x00
    SENSOR_CMD_GET_ITEM = 0x01

    SENSOR_RESULT_OK = 0x00
    SENSOR_RESULT_FAIL = 0x01

    def __init__(self, info, passwd, on_change=None):
        self._type_dict = {
            simple_ctrl_sensor.SENSOR_TYPE_BRIGHTNESS : 'brightness',
            simple_ctrl_sensor.SENSOR_TYPE_HUMIDITY : 'humidity',
            simple_ctrl_sensor.SENSOR_TYPE_TEMPERATURE : 'temperature'
        }
        def led_on_change(event, data):
            if not on_change:
                return
            if event == 'notify':
                sensor_type = int(data[0])
                sensor_id = int(data[1])
                data = int.from_bytes(data[2 : 4], 'little')
                if sensor_type == simple_ctrl_sensor.SENSOR_TYPE_BRIGHTNESS:
                    type_str = self._type_dict[sensor_type]
                    data_unit = 'lx'
                    on_change(type_str, (sensor_id, data, data_unit))
                elif sensor_type == simple_ctrl_sensor.SENSOR_TYPE_HUMIDITY:
                    type_str = self._type_dict[sensor_type]
                    data /= 10
                    data_unit = '%RH'
                    on_change(type_str, (sensor_id, data, data_unit))
                elif sensor_type == simple_ctrl_sensor.SENSOR_TYPE_TEMPERATURE:
                    type_str = self._type_dict[sensor_type]
                    data /= 10
                    data_unit = '℃'
                    on_change(type_str, (sensor_id, data, data_unit))
            else:
                on_change(event, data)
        super().__init__(info, passwd, led_on_change)

    def _sensor_response_check(self, cmd, data):
        if data[0] != cmd[0]:
            raise Exception('Command does not match')
        if data[1] != simple_ctrl_sensor.SENSOR_RESULT_OK:
            raise Exception('Operation Failed')

    def get_count(self):
        '''
        Get the number of sensors
        '''
        cmd = simple_ctrl_sensor.SENSOR_CMD_GET_COUNT.to_bytes(1, 'little')
        response = self.request(cmd)
        self._sensor_response_check(cmd, response)
        sensor_count = int.from_bytes(response[2 : 6], 'little')
        return sensor_count

    def get_item(self, index):
        '''
        Get the sensor information
        '''
        cmd = simple_ctrl_sensor.SENSOR_CMD_GET_ITEM.to_bytes(1, 'little')
        i = index.to_bytes(4, 'little')
        response = self.request(cmd + i)
        self._sensor_response_check(cmd, response)
        sensor_type = int(response[2])
        if sensor_type not in self._type_dict:
            raise Exception(f'Unknown sensor type: {sensor_type}')
        sensor_id = int(response[3])
        sensor_name = response[4 : ].decode('utf-8')
        type_str = self._type_dict[sensor_type]
        return type_str, sensor_id, sensor_name
