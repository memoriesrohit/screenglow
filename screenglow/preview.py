"""A window that shows a mini copy of your screen with a virtual LED strip around it.

Lets you try ScreenGlow and tune its settings before buying any hardware.
"""

import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

from .layout import Layout, zones

MARGIN = 70  # the "wall" around the mini screen where the glow shows
DOT = 5


class Preview:
    def __init__(self, layout: Layout, width: int = 640, height: int = 360):
        self.w, self.h = width, height
        self.closed = False

        self.root = tk.Tk()
        self.root.title("ScreenGlow preview")
        self.root.configure(bg="#000")
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.canvas = tk.Canvas(
            self.root, width=width + 2 * MARGIN, height=height + 2 * MARGIN,
            bg="#000", highlightthickness=0,
        )
        self.canvas.pack()

        self.glows, self.dots = [], []
        for side, a, b in zones(layout):
            glow, dot = self._shapes(side, a, b)
            self.glows.append(self.canvas.create_rectangle(*glow, width=0, fill="#000"))
            self.dots.append(self.canvas.create_oval(*dot, width=0, fill="#000"))
        self.screen = self.canvas.create_image(MARGIN, MARGIN, anchor="nw")
        self._photo = None

    def _shapes(self, side, a, b):
        """Glow rectangle (out on the wall) and LED dot (on the screen's edge)."""
        m, w, h = MARGIN, self.w, self.h
        if side in ("left", "right"):
            y0, y1 = m + a * h, m + b * h
            ym = (y0 + y1) / 2
            if side == "left":
                return (0, y0, m, y1), (m - 2 * DOT, ym - DOT, m, ym + DOT)
            return (m + w, y0, 2 * m + w, y1), (m + w, ym - DOT, m + w + 2 * DOT, ym + DOT)
        x0, x1 = m + a * w, m + b * w
        xm = (x0 + x1) / 2
        if side == "top":
            return (x0, 0, x1, m), (xm - DOT, m - 2 * DOT, xm + DOT, m)
        return (x0, m + h, x1, 2 * m + h), (xm - DOT, m + h, xm + DOT, m + h + 2 * DOT)

    def show(self, frame: np.ndarray | None, colours: np.ndarray, gamma: float = 2.2):
        """Draw one frame. `colours` are the LED values actually sent to the strip."""
        if self.closed:
            return
        # Undo the LED gamma so the on-screen glow looks like the real light would.
        shown = (255 * (np.asarray(colours, np.float32) / 255) ** (1 / gamma)).astype(np.uint8)
        for glow, dot, (r, g, b) in zip(self.glows, self.dots, shown):
            hexc = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.itemconfigure(glow, fill=hexc)
            self.canvas.itemconfigure(dot, fill=hexc)
        if frame is not None:
            img = Image.fromarray(frame).resize((self.w, self.h), Image.BILINEAR)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.itemconfigure(self.screen, image=self._photo)
        self.root.update()

    def _close(self):
        self.closed = True
        self.root.destroy()
