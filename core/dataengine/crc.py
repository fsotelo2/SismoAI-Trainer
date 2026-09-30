"""CRC-32 IEEE over event payloads (spec section 9).

Polynomial 0xEDB88320, init 0xFFFFFFFF, final XOR 0xFFFFFFFF — exactly
what zlib.crc32 implements.
"""

import zlib


def crc32_ieee(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF
