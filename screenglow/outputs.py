"""Send colours to real LEDs: an ESP32 running WLED (Wi-Fi) or an Arduino (USB)."""

import socket
import time

import numpy as np

WLED_PORT = 21324
DRGB, DNRGB = 2, 4  # WLED realtime UDP protocols
DRGB_MAX = 490  # LEDs per DRGB packet
DNRGB_MAX = 489  # LEDs per DNRGB packet


def wled_packets(colours: np.ndarray, timeout: int = 2) -> list[bytes]:
    """Encode colours as WLED realtime UDP packets.

    `timeout` is how many seconds WLED waits after the last packet before it
    goes back to its normal effect -- so closing ScreenGlow never leaves the
    strip stuck on one colour.
    """
    c = np.asarray(colours, dtype=np.uint8)
    if len(c) <= DRGB_MAX:
        return [bytes([DRGB, timeout]) + c.tobytes()]
    packets = []
    for start in range(0, len(c), DNRGB_MAX):
        header = bytes([DNRGB, timeout, start >> 8, start & 0xFF])
        packets.append(header + c[start:start + DNRGB_MAX].tobytes())
    return packets


def adalight_frame(colours: np.ndarray) -> bytes:
    """Encode colours in the Adalight serial protocol ("Ada" + count + checksum)."""
    c = np.asarray(colours, dtype=np.uint8)
    n = len(c) - 1
    hi, lo = (n >> 8) & 0xFF, n & 0xFF
    return b"Ada" + bytes([hi, lo, hi ^ lo ^ 0x55]) + c.tobytes()


class WLED:
    def __init__(self, host: str, port: int = WLED_PORT, timeout: int = 2):
        self.addr = (host, port)
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, colours):
        for packet in wled_packets(colours, self.timeout):
            self.sock.sendto(packet, self.addr)

    def close(self):
        self.sock.close()  # WLED returns to normal after `timeout` seconds


class Adalight:
    def __init__(self, port: str, baud: int = 115200):
        import serial  # only needed for the Arduino path

        self.ser = serial.Serial(port, baud, timeout=0, write_timeout=1)
        time.sleep(2)  # most Arduinos reset when the port opens
        self._count = 0

    def send(self, colours):
        self._count = len(colours)
        self.ser.write(adalight_frame(colours))

    def close(self):
        if self._count:
            self.ser.write(adalight_frame(np.zeros((self._count, 3), np.uint8)))
            self.ser.flush()
        self.ser.close()
