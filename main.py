#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from simple_ctrl import simple_ctrl_manager
from dev_button_led import simple_ctrl_button_led
from dev_smart_ir import simple_ctrl_smart_ir
from dev_sensor import simple_ctrl_sensor
from dev_voice_led import simple_ctrl_voice_led
import time

dev_password = { }
try:
    with open('devinfo.txt', 'r', encoding='utf-8') as f:
        _data = f.readlines()
        _data = [_.replace('\r', '').replace('\n', '') for _ in _data]
        dev_password = {_[:14]: _[14:] for _ in _data}
except Exception as e:
    print(e)
# print(dev_password)

def main():
    dev_list = { }
    try:
        def on_change(event, dev_info):
            dev_name = dev_info.name
            dev_id = dev_info.id
            print(f'[{event}] {dev_name} ({dev_id})')
            if dev_id not in dev_password:
                return
            if event == 'online':
                dev_passwd = dev_password[dev_id]
                try:
                    dev = server.device_factory(dev_id, dev_passwd, lambda x,y : print(x, y))
                    dev.connect()
                    dev_list[dev_id] = dev
                    # with dev:
                    print(f'name:{dev.info_get_name()}, type:{dev.info_get_type()}')
                    if isinstance(dev, simple_ctrl_button_led):
                        rgb = dev.get_color()
                        print('color:', rgb)
                        # dev.set_color((0, 0, 255))
                    elif isinstance(dev, simple_ctrl_voice_led):
                        rgb = dev.get_color()
                        print('color:', rgb)
                        # dev.set_color((0, 0, 255))
                    elif isinstance(dev, simple_ctrl_smart_ir):
                        key_count = dev.get_count()
                        print('key_count:', key_count)
                        key_list = [ ]
                        for i in range(key_count):
                            key = dev.get_item(i)
                            print(f'key_name: [{i}] {key}')
                            key_list.append(key)
                        # dev.tx_send(key_list[0]) # first key
                    elif isinstance(dev, simple_ctrl_sensor):
                        sensor_count = dev.get_count()
                        print('sensor_count:', sensor_count)
                        for i in range(sensor_count):
                            sensor = dev.get_item(i)
                            print(f'sensor: [{i}] {sensor}')
                except Exception as e:
                    print(e)
            elif event == 'offline':
                if dev_id in dev_list:
                    dev = dev_list[dev_id]
                    dev.disconnect()
                    del dev_list[dev_id]
        class_list = [
            simple_ctrl_button_led,
            simple_ctrl_smart_ir,
            simple_ctrl_sensor,
            simple_ctrl_voice_led
        ]
        server = simple_ctrl_manager(class_list, on_change)
        server.start()
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print('Program interrupted by user')
    except Exception as e:
        print(e)
    finally:
        if server:
            server.stop()
        for dev in dev_list.values():
            dev.disconnect()
    print('Main exited')

if __name__ == '__main__':
    main()
