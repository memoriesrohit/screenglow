import numpy as np
import pytest

from screenglow.layout import Layout, sample, zones

RED, BLUE = (255, 0, 0), (0, 0, 255)


def half_and_half(h=90, w=160):
    """Left half red, right half blue."""
    f = np.zeros((h, w, 3), np.uint8)
    f[:, : w // 2] = RED
    f[:, w // 2 :] = BLUE
    return f


def test_each_side_sees_its_own_edge():
    lay = Layout(left=3, top=4, right=3, bottom=4)
    c = sample(half_and_half(), lay)
    assert c.shape == (14, 3)
    assert np.allclose(c[0:3], RED)  # left side
    assert np.allclose(c[3:5], RED) and np.allclose(c[5:7], BLUE)  # top, left -> right
    assert np.allclose(c[7:10], BLUE)  # right side
    assert np.allclose(c[10:12], BLUE) and np.allclose(c[12:14], RED)  # bottom, right -> left


def test_left_side_runs_bottom_to_top():
    f = np.zeros((90, 160, 3), np.uint8)
    f[45:] = RED  # bottom half red
    c = sample(f, Layout(left=2, top=0, right=0, bottom=0))
    assert np.allclose(c[0], RED) and np.allclose(c[1], 0)


def test_offset_and_reverse_match_zones():
    for lay in [Layout(3, 4, 3, 4, offset=5), Layout(3, 4, 3, 4, reverse=True), Layout(3, 4, 3, 4, offset=-2, reverse=True)]:
        c = sample(half_and_half(), lay)
        z = zones(lay)
        assert len(z) == lay.count
        for (side, a, b), colour in zip(z, c):
            mid = (a + b) / 2
            on_left = side == "left" or (side in ("top", "bottom") and mid < 0.5)
            assert np.allclose(colour, RED if on_left else BLUE)


def test_offset_rotates_start():
    base = sample(half_and_half(), Layout(3, 4, 3, 4))
    shifted = sample(half_and_half(), Layout(3, 4, 3, 4, offset=3))
    assert np.allclose(shifted, np.roll(base, -3, axis=0))


def test_too_many_leds_for_the_image():
    with pytest.raises(ValueError):
        sample(np.zeros((10, 10, 3), np.uint8), Layout(20, 1, 1, 1))
