import numpy as np

from screenglow.colour import ColourProcessor, estimate_amps
from screenglow.outputs import adalight_frame, wled_packets


def test_black_stays_black_and_white_hits_brightness():
    p = ColourProcessor(smoothing=0, brightness=0.5, saturation=1)
    out = p(np.array([[0, 0, 0], [255, 255, 255]]))
    assert out.tolist() == [[0, 0, 0], [128, 128, 128]]


def test_gamma_keeps_dark_scenes_dark():
    out = ColourProcessor(smoothing=0, brightness=1, saturation=1)(np.array([[64, 64, 64]]))
    assert out[0, 0] < 20  # a dim grey on screen should be a faint glow, not 64


def test_smoothing_fades_towards_new_colour():
    p = ColourProcessor(smoothing=0.5, brightness=1, gamma=1, saturation=1)
    p(np.array([[0, 0, 0]]))
    steps = [int(p(np.array([[200, 200, 200]]))[0, 0]) for _ in range(6)]
    assert steps == sorted(steps) and steps[0] == 100 and steps[-1] > 190


def test_power_limit():
    p = ColourProcessor(smoothing=0, brightness=1, gamma=1, saturation=1, max_amps=2)
    out = p(np.full((100, 3), 255))  # 100 LEDs full white would be ~6 A
    assert estimate_amps(out) <= 2.01


def test_wled_drgb_for_small_strips():
    (pkt,) = wled_packets(np.array([[1, 2, 3], [4, 5, 6]]), timeout=2)
    assert pkt == bytes([2, 2, 1, 2, 3, 4, 5, 6])


def test_wled_dnrgb_chunks_for_big_strips():
    pkts = wled_packets(np.zeros((1000, 3)), timeout=1)
    assert [p[0] for p in pkts] == [4, 4, 4]
    starts = [p[2] << 8 | p[3] for p in pkts]
    assert starts == [0, 489, 978]
    assert sum((len(p) - 4) // 3 for p in pkts) == 1000


def test_adalight_header():
    frame = adalight_frame(np.zeros((100, 3)))
    assert frame[:6] == b"Ada" + bytes([0, 99, 0 ^ 99 ^ 0x55])
    assert len(frame) == 6 + 300
