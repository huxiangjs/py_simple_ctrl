#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import netifaces  # pip install netifaces
import logging
from datetime import datetime
import threading
import time
import queue
from . import crypto

_log_name = 'simple_ctrl'
_broadcast_list = []
_simple_ctrl_host = '0.0.0.0'
_simple_ctrl_port = 54542

# Configure logger
logger = logging.getLogger(_log_name)
logger.setLevel(logging.INFO)
logger.propagate = False
console = logging.StreamHandler()
console.setFormatter(
        logging.Formatter(f'%(asctime)s [%(levelname)s] {_log_name}: %(message)s')
)
logger.addHandler(console)

# Get information about all network interfaces
for interface_name in netifaces.interfaces():
    addrs = netifaces.ifaddresses(interface_name)
    if netifaces.AF_INET not in addrs:
        continue
    for addr_info in addrs[netifaces.AF_INET]:
        ip = addr_info.get('addr')
        netmask = addr_info.get('netmask')
        if ip and netmask and ip.startswith('127.'):
            continue
        ip_split = ip.split('.')
        mask_split = netmask.split('.')
        broadcast = []
        for i in range(4):
            broadcast_part = int(ip_split[i]) | (~int(mask_split[i]) & 0xff)
            broadcast.append(str(broadcast_part))
        broadcast = '.'.join(broadcast)
        _broadcast_list.append(broadcast)
        logger.debug(f'find: ip:{ip} netmask:{netmask} broadcast:{broadcast}')

class discover_device_info:
    def __init__(self, id, ip, port, class_id, has_password,
                crypto_type, name, time):
        self.id = id
        self.ip = ip
        self.port = port
        self.class_id = class_id
        self.has_password = has_password
        self.crypto_type = crypto_type
        self.name = name
        self.time = time

    # def __str__(self):
    #     return str(self.__dict__)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'

class simple_ctrl_discover(threading.Thread):
    '''
    Discover Devices
    '''

    SAY = 'HOOZZ?'
    RESPOND = 'HOOZZ:'
    ID_LENGTH = 14
    INTERVAL = 10
    BUFSIZE = 1024
    PREFIX_LEN = len(RESPOND)

    def __init__(self, on_refresh=None):
        super().__init__()
        self._running = False
        self._socket = None
        self._hello_timer = None
        self._on_refresh = on_refresh if on_refresh else lambda _ : None
        # Create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set socket option to allow address reuse (useful for quick restarts)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Allow socket broadcasting
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Set timeout to avoid blocking indefinitely
        # This allows the server to check the running flag periodically
        self._socket.settimeout(1.0)
        # Bind to the specified address and port
        self._socket.bind((_simple_ctrl_host, _simple_ctrl_port))

    def start(self):
        self._running = True
        self._say_hello()
        super().start()

    def run(self):
        logger.info(f'Discover server started successfully')
        # recv loop
        while self._running:
            try:
                # Receive data from any client
                data, client_address = self._socket.recvfrom(simple_ctrl_discover.BUFSIZE)
                try:
                    message = data.decode('utf-8')
                except UnicodeDecodeError:
                    logger.error(f'Decode failed')
                    continue
                if not message:
                    continue
                if not message.startswith(simple_ctrl_discover.RESPOND):
                    continue

                ip = str(client_address[0])
                port = int(client_address[1])
                logger.debug(f'Received message from {ip}:{port}: {message}')
                # Process the received data
                id_length = simple_ctrl_discover.ID_LENGTH
                prefix_len = simple_ctrl_discover.PREFIX_LEN
                dev_info = discover_device_info(
                    message[11 : 11 + id_length],
                    ip, port, int(message[prefix_len : prefix_len + 2], 16),
                    True if message[prefix_len + 2 + 2 : prefix_len + 2 + 2 + 1] != '-' else False,
                    int(message[prefix_len + 2 : prefix_len + 2 + 2], 16),
                    message[prefix_len + 2 + 2 + 1 + id_length :],
                    datetime.now()
                )
                logger.debug(f'Device: {dev_info}')
                self._on_refresh(dev_info)
            except socket.timeout:
                # Timeout occurred, continue the loop to check running flag
                continue
            except Exception as e:
                logger.error(f'Discover error while receiving data: {e}')
                break
        self._running = False
        logger.info('Discover server stopped')

    def _say_hello(self):
        if not self._running:
            return
        logger.debug(f'Say hello!')
        try:
            if self._hello_timer:
                response = simple_ctrl_discover.SAY.encode('utf-8')
                for _ in range(5):
                    for item in _broadcast_list:
                        address = (item, _simple_ctrl_port)
                        self._socket.sendto(response, address)
                    time.sleep(0.1)
                next_interval = simple_ctrl_discover.INTERVAL
            else:
                next_interval = 0
            self._hello_timer = threading.Timer(next_interval, self._say_hello)
            self._hello_timer.start()
        except Exception as e:
            logger.error(f'Error processing data: {e}')

    def stop(self):
        self._running = False
        logger.info('Discover server is stopping...')
        if self._socket:
            self._socket.close()
        if self._hello_timer:
            self._hello_timer.cancel()
        self.join()
        if self._hello_timer:
            self._hello_timer.join()

class simple_ctrl_control(threading.Thread):
    '''
    Device control
    '''

    LOAD_TYPE_PING = 0x00
    LOAD_TYPE_INFO = 0x01
    LOAD_TYPE_REQUEST = 0x02
    LOAD_TYPE_NOTIFY = 0x03

    INFO_TYPE_GET_NAME = 0x00
    INFO_TYPE_SET_NAME = 0x01
    INFO_TYPE_GET_CLASSID = 0x02
    INFO_TYPE_SET_PASSWD = 0x03

    RETURN_OK = 0x00
    RETURN_FAIL = 0x01
    LOAD_HEADER_SIZE = 16
    LOAD_MAGIC_STRING = 'HOOZZ'

    ACCESS_KEY_LENGTH = 16
    PING_INTERVAL = 5

    def __init__(self, info, passwd, on_change=None):
        super().__init__()
        self._running = False
        self._on_change = on_change if on_change else lambda _ : None
        self._dev_info = info
        self._host = info.ip
        self._port = info.port
        passwd_bytes = passwd.encode('utf-8')
        need_len = simple_ctrl_control.ACCESS_KEY_LENGTH
        actual_len = len(passwd_bytes)
        if actual_len % need_len:
            passwd_bytes += bytes(need_len - (actual_len % need_len))
        self._crypto = crypto.get_crypto(info.crypto_type, passwd_bytes)
        self._response = {
            'ping' : queue.Queue(maxsize=0),
            'info' : queue.Queue(maxsize=0),
            'request' : queue.Queue(maxsize=0)
        }
        self._ping_timer = None

    def _ping_check(self):
        if not self._running:
            return
        try:
            if self._ping_timer:
                ok = self._ping(simple_ctrl_control.PING_INTERVAL)
                if not ok:
                    raise Exception('Ping failed')
                logger.debug('Ping successfull')
                next_interval = simple_ctrl_control.PING_INTERVAL
            else:
                next_interval = simple_ctrl_control.PING_INTERVAL
            self._ping_timer = threading.Timer(next_interval, self._ping_check)
            self._ping_timer.start()
        except Exception as e:
            logger.info(e)
            self._socket.close()

    def connect(self, timeout=None):
        self._running = True
        # Create socket object (IPv4, TCP)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to the server
        logger.info(f'Connecting to {self._host}:{self._port}...')
        self._socket.settimeout(timeout)
        self._socket.connect((self._host, self._port))
        self._ping_check()
        super().start()
        logger.info('Connected')

    def _build(self, type, data):
        '''
        Build the data to be sent
        '''
        # |--Magic(6bytes)--|--Reserved(6bytes)--|--Data size(4bytes)--|
        playload = simple_ctrl_control.LOAD_MAGIC_STRING.encode('utf-8')
        playload += bytes(12 - len(playload))
        playload += len(data).to_bytes(4, 'little')
        playload += data
        playload = self._crypto.en(playload)
        # |--Playload type(1bytes)--|--Playload size(4bytes)--|
        head_data = type.to_bytes(1, 'little')
        head_data += len(playload).to_bytes(4, 'little')
        return head_data + playload

    def _response_check(self, data):
        '''
        Encrypt the data and verify that it is correct
        '''
        raw_data = self._crypto.de(data)
        magic_len = len(simple_ctrl_control.LOAD_MAGIC_STRING)
        magic = raw_data[:magic_len].decode('utf-8')
        if magic != simple_ctrl_control.LOAD_MAGIC_STRING:
            raise Exception(f'Magic does not match: {magic} ({len(magic)}bytes)')
        data_size = int.from_bytes(raw_data[12 : 16], byteorder='little')
        return raw_data[16 : 16 + data_size]

    def _state_check(self):
        if not self._running:
            raise Exception('The device is not connected or has been disconnected')

    def request(self, data, timeout=None):
        '''
        Data Request
        '''
        self._state_check()
        self._socket.send(self._build(simple_ctrl_control.LOAD_TYPE_REQUEST, data))
        response = self._response['request'].get(timeout=timeout)
        self._response['request'].task_done()
        if response is None:
            raise Exception('Command [REQUEST] received an unexpected response')
        return self._response_check(response)

    def _info(self, data, timeout=None):
        '''
        Info Request
        '''
        self._state_check()
        self._socket.send(self._build(simple_ctrl_control.LOAD_TYPE_INFO, data))
        response = self._response['info'].get(timeout=timeout)
        self._response['info'].task_done()
        if response is None:
            raise Exception('Command [INFO] received an unexpected response')
        return self._response_check(response)

    def info_get_name(self):
        '''
        Get the device name
        '''
        data = simple_ctrl_control.INFO_TYPE_GET_NAME.to_bytes(1, 'little')
        ret = self._info(data)
        if ret[0] != simple_ctrl_control.INFO_TYPE_GET_NAME:
            raise Exception(f'Error return command: {int(ret[0])}')
        if ret[1] != simple_ctrl_control.RETURN_OK:
            raise Exception(f'Error return state: {int(ret[1])}')
        name = ret[2:].decode('utf-8')
        return name

    def info_set_name(self, name):
        '''
        Set the device name
        '''
        data = simple_ctrl_control.INFO_TYPE_SET_NAME.to_bytes(1, 'little')
        data += name.encode('utf-8')
        ret = self._info(data)
        if ret[0] != simple_ctrl_control.INFO_TYPE_SET_NAME:
            raise Exception(f'Error return command: {int(ret[0])}')
        if ret[1] != simple_ctrl_control.RETURN_OK:
            raise Exception(f'Error return state: {int(ret[1])}')

    def info_get_type(self):
        '''
        Get the device type
        '''
        data = simple_ctrl_control.INFO_TYPE_GET_CLASSID.to_bytes(1, 'little')
        ret = self._info(data)
        if ret[0] != simple_ctrl_control.INFO_TYPE_GET_CLASSID:
            raise Exception(f'Error return command: {int(ret[0])}')
        if ret[1] != simple_ctrl_control.RETURN_OK:
            raise Exception(f'Error return state: {int(ret[1])}')
        class_id = int(ret[2])
        return class_id

    def info_set_passwd(self, passwd):
        '''
        Set the device password
        '''
        data = simple_ctrl_control.INFO_TYPE_SET_PASSWD.to_bytes(1, 'little')
        data += passwd.encode('utf-8')
        ret = self._info(data)
        if ret[0] != simple_ctrl_control.INFO_TYPE_SET_PASSWD:
            raise Exception(f'Error return command: {int(ret[0])}')
        if ret[1] != simple_ctrl_control.RETURN_OK:
            raise Exception(f'Error return state: {int(ret[1])}')

    def _ping(self, timeout=None):
        '''
        Keep alive
        '''
        self._state_check()
        ping_data = simple_ctrl_control.PING_INTERVAL.to_bytes(1, 'little')
        self._socket.send(self._build(simple_ctrl_control.LOAD_TYPE_PING, ping_data))
        response = self._response['ping'].get(timeout=timeout)
        self._response['ping'].task_done()
        if response is None:
            raise Exception('Command [PING] received an unexpected response')
        ret_data = self._response_check(response)
        if len(ret_data) == 1 and int(ret_data[0]) == simple_ctrl_control.RETURN_OK:
            return True
        return False

    def _notify(self, data):
        '''
        Receive notifications from the device
        '''
        self._on_change('notify', self._response_check(data))

    def run(self):
        self._on_change('state', 'ready')
        while self._running:
            try:
                head_data = self._socket.recv(5)
                if len(head_data) != 5:
                    raise Exception('Unable to receive enough head data')
                playload_type = int.from_bytes(head_data[0 : 1], byteorder='little')
                playload_len = int.from_bytes(head_data[1 : 5], byteorder='little')
                playload = self._socket.recv(playload_len)
                if len(playload) != playload_len:
                    raise Exception('Unable to receive enough playload data')
                logger.debug(f'Received: {len(playload)} bytes, type: {playload_type}')
                if playload_type == simple_ctrl_control.LOAD_TYPE_PING:
                    self._response['ping'].put(playload)
                elif playload_type == simple_ctrl_control.LOAD_TYPE_INFO:
                    self._response['info'].put(playload)
                elif playload_type == simple_ctrl_control.LOAD_TYPE_REQUEST:
                    self._response['request'].put(playload)
                elif playload_type == simple_ctrl_control.LOAD_TYPE_NOTIFY:
                    self._notify(playload)
                else:
                    raise Exception(f'Exception playload type: {playload_type}')
            except socket.timeout:
                # Timeout occurred, continue the loop to check running flag
                continue
            except Exception as e:
                logger.error(f'Control error while receiving data: {e}')
                break
        self._on_change('state', 'exit')
        for item in self._response.values():
            item.put(None)
        self._running = False
        host = self._dev_info.ip
        port = self._dev_info.port
        logger.info(f'{host}:{port} connection closed')

    def disconnect(self):
        self._running = False
        if self._socket:
            self._socket.close()
        if self._ping_timer:
            self._ping_timer.cancel()
        self.join()
        if self._ping_timer:
            self._ping_timer.join()
        logger.info(f'{self._host}:{self._port} disconnected')

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

class simple_ctrl_manager:
    '''
    Device manager
    '''

    ALIVE_TIMEOUT = 30

    def __init__(self, class_list = [], on_change=None):
        self._running = False
        self._on_change = on_change if on_change else lambda _, __ : None
        self._dev_dict = { }
        self._dict_lock = threading.Lock()
        def on_refresh(info):
            with self._dict_lock:
                new_dev = info.id not in self._dev_dict
                self._dev_dict[info.id] = info
                if new_dev:
                    self._event_queue.put(['online', info]) # dev online
        self._discover = simple_ctrl_discover(on_refresh)
        self._alive_timer = None
        self._event_queue = queue.Queue(maxsize=0)
        self._event_thread = threading.Thread(target=self._event_caller)
        self._class_dict = { c.CLASS_ID : c for c in class_list }

    def _event_caller(self):
        '''
        Send events uniformly within the same thread
        '''
        while self._running:
            try:
                event = self._event_queue.get(timeout=None)
                if event is None:
                    break
                self._on_change(event[0], event[1])
                self._event_queue.task_done()
            except queue.Empty:
                continue
        logger.debug('Caller exited')

    def _alive_check(self):
        if not self._running:
            return
        if self._alive_timer:
            now = datetime.now()
            with self._dict_lock:
                del_list = []
                for k,v in self._dev_dict.items():
                    delta = (now - v.time).total_seconds()
                    if delta < simple_ctrl_manager.ALIVE_TIMEOUT:
                        continue
                    self._event_queue.put(['offline', v]) # dev offline
                    del_list.append(k)
                for k in del_list:
                    del self._dev_dict[k]
            logger.debug('Liveness check')
            next_interval = 1
        else:
            next_interval = 0
        self._alive_timer = threading.Timer(next_interval, self._alive_check)
        self._alive_timer.start()

    def device_is_online(self, id):
        '''
        Check if the device is online
        '''
        with self._dict_lock:
            alive = id in self._dev_dict
        return alive

    def device_factory(self, id, passwd, on_change=None):
        '''
        Create a device instance
        '''
        with self._dict_lock:
            if id not in self._dev_dict:
                raise Exception(f'The device is offline: {id}')
            dev_info = self._dev_dict[id]
            if dev_info.class_id in self._class_dict:
                dev_class = self._class_dict[dev_info.class_id]
                dev = dev_class(dev_info, passwd, on_change)
            else:
                # dev = simple_ctrl_control(dev_info, passwd, on_change)
                raise Exception('No class available for the device was found')
            return dev

    def start(self):
        '''
        Start server
        '''
        self._running = True
        self._event_thread.start()
        self._discover.start()
        self._alive_check()

    def stop(self):
        '''
        Stop server
        '''
        self._running = False
        self._discover.stop()
        self._event_queue.put(None)
        if self._alive_timer:
            self._alive_timer.cancel()
            self._alive_timer.join()
        self._event_thread.join()
