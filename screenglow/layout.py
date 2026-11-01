"""Where each LED sits around the screen, and which part of the screen it copies.

Canonical order, as seen from the FRONT of the monitor: LED 0 is at the
bottom-left corner and the strip runs clockwise -- up the left side, across
the top, down the right side and back along the bottom. `offset` and
`reverse` adapt that to wherever your real strip starts and which way it runs.
"""

from dataclasses import dataclass

import numpy as np

SIDES = ("left", "top", "right", "bottom")


@dataclass(frozen=True)
class Layout:
    left: int
    top: int
    right: int
    bottom: int
    depth: float = 0.08  # how far into the screen each LED "looks", as a fraction
    offset: int = 0  # canonical index of the zone where your strip's first LED is
    reverse: bool = False  # strip runs counter-clockwise

    @property
    def count(self) -> int:
        return self.left + self.top + self.right + self.bottom

    def _arrange(self, items):
        """Apply reverse/offset so item i belongs to physical LED i."""
        items = list(items)
        if self.reverse:
            items.reverse()
        k = self.offset % len(items) if items else 0
        return items[k:] + items[:k]


def zones(layout: Layout) -> list[tuple[str, float, float]]:
    """(side, start, end) for every LED, in physical strip order.

    start/end are fractions along the side, measured left->right for top and
    bottom and top->bottom for left and right.
    """
    out = []
    for k in range(layout.left):  # bottom -> top
        out.append(("left", 1 - (k + 1) / layout.left, 1 - k / layout.left))
    for k in range(layout.top):  # left -> right
        out.append(("top", k / layout.top, (k + 1) / layout.top))
    for k in range(layout.right):  # top -> bottom
        out.append(("right", k / layout.right, (k + 1) / layout.right))
    for k in range(layout.bottom):  # right -> left
        out.append(("bottom", 1 - (k + 1) / layout.bottom, 1 - k / layout.bottom))
    return layout._arrange(out)


def _segment_means(line: np.ndarray, n: int) -> np.ndarray:
    """Split an edge (length L, 3 channels) into n segments and average each."""
    if n == 0:
        return np.empty((0, 3), dtype=np.float32)
    if n > len(line):
        raise ValueError(f"{n} LEDs on a side but only {len(line)} pixels to sample")
    bounds = np.linspace(0, len(line), n + 1).astype(int)
    sums = np.add.reduceat(line, bounds[:-1], axis=0)
    return sums / np.diff(bounds)[:, None]


def sample(frame: np.ndarray, layout: Layout) -> np.ndarray:
    """Average screen colour behind each LED.

    frame: H x W x 3 RGB image. Returns a (layout.count, 3) float array, 0-255.
    """
    h, w = frame.shape[:2]
    dy = max(1, round(h * layout.depth))
    dx = max(1, round(w * layout.depth))
    f = frame[..., :3].astype(np.float32)

    left = f[:, :dx].mean(axis=1)[::-1]  # bottom -> top
    top = f[:dy].mean(axis=0)  # left -> right
    right = f[:, -dx:].mean(axis=1)  # top -> bottom
    bottom = f[-dy:].mean(axis=0)[::-1]  # right -> left

    colours = np.concatenate([
        _segment_means(left, layout.left),
        _segment_means(top, layout.top),
        _segment_means(right, layout.right),
        _segment_means(bottom, layout.bottom),
    ])
    return np.array(layout._arrange(colours), dtype=np.float32).reshape(-1, 3)
