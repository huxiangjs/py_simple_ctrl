#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from Crypto.Cipher import AES # pip install pycryptodome
from Crypto.Random import get_random_bytes

CRYPTO_TYPE_NONE = 0x00
CRYPTO_TYPE_XOR = 0x01
CRYPTO_TYPE_AES128ECB = 0x02
CRYPTO_TYPE_AES128CBC = 0x03

class crypto:
    '''
    Encrypting and decrypting data
    '''

    HEAD_RESERVE = 0
    TAIL_RESERVE = 0

    def __init__(self, passwd):
        self._passwd = passwd

    def en(self, _):
        pass

    def de(self, _):
        pass

class crypto_none(crypto):
    '''
    No encryption or decryption is performed
    '''

    HEAD_RESERVE = 0
    TAIL_RESERVE = 0

    def __init__(self, passwd):
        self._passwd = passwd

    def en(self, data):
        return data

    def de(self, data):
        return data

class crypto_aes128cbc(crypto):
    '''
    Encryption and decryption using AES-128-CBC
    '''

    HEAD_RESERVE = AES.block_size
    TAIL_RESERVE = 0

    def __init__(self, passwd):
        if len(passwd) > AES.block_size:
            raise Exception(f'The password exceeds the maximum length: {len(passwd)}')
        self._passwd = passwd

    def _pad(self, data):
        data_len = len(data)
        if data_len % AES.block_size:
            data += bytes(AES.block_size - (data_len % AES.block_size))
        return data

    def en(self, data):
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(self._passwd, AES.MODE_CBC, iv)
        padded_data = self._pad(data)
        ciphertext = cipher.encrypt(padded_data)
        return iv + ciphertext

    def de(self, data):
        iv = data[:AES.block_size]
        ciphertext = data[AES.block_size:]
        cipher = AES.new(self._passwd, AES.MODE_CBC, iv)
        padded_data = cipher.decrypt(ciphertext)
        return padded_data

def get_crypto(type, passwd):
    if type == CRYPTO_TYPE_NONE:
        return crypto_none(passwd),
    elif type == CRYPTO_TYPE_AES128CBC:
        return crypto_aes128cbc(passwd)
    raise Exception(f'Unsupported encryption type: {type}')
