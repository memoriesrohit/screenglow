"""Turn raw screen colours into colours that look right on an LED strip."""

import numpy as np

# A WS2812B LED draws about 20 mA per colour channel at full brightness.
MA_PER_CHANNEL = 20.0


class ColourProcessor:
    """Saturation boost -> smoothing -> gamma -> brightness -> power limit.

    smoothing:  0 = instant, 0.9 = very slow and calm fades
    brightness: 0..1 overall scale
    gamma:      LEDs are linear but screens are gamma-encoded; 2.2 makes dark
                scenes stay dark instead of glowing grey
    saturation: >1 makes washed-out colours more vivid on the wall
    max_amps:   your power supply's limit; output is dimmed to stay under it
    """

    def __init__(self, smoothing=0.6, brightness=0.7, gamma=2.2, saturation=1.2, max_amps=None):
        self.smoothing = smoothing
        self.brightness = brightness
        self.gamma = gamma
        self.saturation = saturation
        self.max_amps = max_amps
        self._state = None

    def __call__(self, colours: np.ndarray) -> np.ndarray:
        c = np.asarray(colours, dtype=np.float32)

        if self.saturation != 1:
            grey = c.mean(axis=1, keepdims=True)
            c = grey + (c - grey) * self.saturation
        c = np.clip(c, 0, 255)

        if self._state is None or self._state.shape != c.shape:
            self._state = c
        else:
            self._state = self._state + (1 - self.smoothing) * (c - self._state)

        out = 255 * (self._state / 255) ** self.gamma * self.brightness

        if self.max_amps:
            amps = out.sum() / 255 * MA_PER_CHANNEL / 1000
            if amps > self.max_amps:
                out *= self.max_amps / amps

        return np.rint(out).clip(0, 255).astype(np.uint8)


def estimate_amps(colours: np.ndarray) -> float:
    """Rough current draw of a WS2812B strip showing these colours."""
    return float(np.asarray(colours, dtype=np.float32).sum() / 255 * MA_PER_CHANNEL / 1000)
