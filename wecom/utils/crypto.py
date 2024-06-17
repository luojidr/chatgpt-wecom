from typing import Union
from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES


class AESCipher:
    KEY_SIZE = (16, 24, 32)
    SIV_SIZE = (32, 48, 64)

    def __init__(self, key, block_size=AES.block_size, mode=AES.MODE_ECB):
        key = self._to_bytes(key)

        if mode not in (AES.MODE_ECB, AES.MODE_CBC):
            raise ValueError("暂不支持该加密方式")

        self._mode = mode
        self._block_size = 32 if self._mode == AES.MODE_SIV else block_size

        # It must be 16, 24 or 32 bytes long (respectively for *AES-128*, *AES-192* or *AES-256*).
        # For ``MODE_SIV`` only, it doubles to 32, 48, or 64 bytes.
        # 简单计算: MODE_SIV模式取32的倍数，其他模式取16(不是倍数)
        key_size = self._mode == AES.MODE_SIV and self.SIV_SIZE or self.KEY_SIZE
        self._key = self.add_to_16(key)

        if len(self._key) not in key_size:
            raise ValueError("秘钥的长度(%d bytes)不正确" % len(self._key))

        self._iv = self._key  # 向量iv(CBC模式)

    def _to_bytes(self, s: Union[str, bytes]) -> bytes:
        if isinstance(s, str):
            s = s.encode("utf-8")
        return s

    def _get_crypto(self):
        crypto = None
        if self._mode == AES.MODE_ECB:
            crypto = AES.new(self._key, self._mode)

        if self._mode == AES.MODE_CBC:
            crypto = AES.new(self._key, self._mode, self._iv)

        return crypto

    def add_to_16(self, text):
        """ complements a multiple of string length 16 """
        if len(text) % self._block_size != 0:
            addition = self._block_size - len(text) % self._block_size
        else:
            addition = 0

        text = text + (b'\0' * addition)
        return text

    def encrypt(self, s):
        """ encrypt to raw by CBC or ECB """
        s = self._to_bytes(s)
        crypto = self._get_crypto()

        text = self.add_to_16(s)
        cipher_text = crypto.encrypt(text)

        return b2a_hex(cipher_text).decode("utf-8")

    def decrypt(self, text):
        """ decrypt to text by CBC or ECB """
        text = self._to_bytes(text)
        crypto = self._get_crypto()
        plain_text = crypto.decrypt(a2b_hex(text))

        plain_text = plain_text.rstrip(b'\0').decode("utf-8").strip()
        return plain_text.rstrip("\x06\x05\x07\b")
