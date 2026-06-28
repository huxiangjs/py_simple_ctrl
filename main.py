#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from simple_ctrl import simple_ctrl_manager
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
                dev = server.device_factory(dev_id, dev_passwd, lambda x,y : print(x, y))
                dev.connect()
                print('name:', dev.info_get_name())
                print('type:', dev.info_get_type())
                dev_list[dev_id] = dev
            elif event == 'offline':
                dev = dev_list[dev_id]
                dev.disconnect()
                del dev_list[dev_id]
        server = simple_ctrl_manager(on_change)
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
