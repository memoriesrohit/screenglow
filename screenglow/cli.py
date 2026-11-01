"""Command line entry point: capture the screen, light the LEDs, repeat."""

import argparse
import sys
import time

import numpy as np

from .colour import ColourProcessor, estimate_amps
from .layout import Layout, sample

SAMPLE_WIDTH = 480  # screen is downscaled to about this width before sampling


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="screenglow",
        description="Make an LED strip behind your monitor glow with the colours on screen.",
    )
    out = p.add_argument_group("where to send colours (pick one or more)")
    out.add_argument("--preview", action="store_true", help="show a virtual LED strip in a window (no hardware)")
    out.add_argument("--wled", metavar="IP", help="ESP32/ESP8266 running WLED, e.g. 192.168.1.50")
    out.add_argument("--adalight", metavar="PORT", help="Arduino running firmware/adalight, e.g. COM5")
    out.add_argument("--baud", type=int, default=115200, help="serial speed for --adalight")

    lay = p.add_argument_group("LED layout")
    lay.add_argument("--leds", nargs=4, type=int, default=[18, 32, 18, 32], metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                     help="LEDs on each side (default fits a 24\" monitor at 60 LEDs/m)")
    lay.add_argument("--offset", type=int, default=0, help="shift where LED 0 is (see --test)")
    lay.add_argument("--reverse", action="store_true", help="strip runs counter-clockwise (seen from the front)")
    lay.add_argument("--depth", type=float, default=0.08, help="how far into the screen each LED samples (0-0.5)")

    look = p.add_argument_group("look and feel")
    look.add_argument("--brightness", type=float, default=0.7, help="0-1")
    look.add_argument("--smoothing", type=float, default=0.6, help="0 = instant, 0.9 = slow fades")
    look.add_argument("--saturation", type=float, default=1.2, help="1 = true colours, >1 = more vivid")
    look.add_argument("--gamma", type=float, default=2.2)
    look.add_argument("--max-amps", type=float, default=3.5, help="dim to stay under your power supply's limit")

    p.add_argument("--monitor", type=int, default=1, help="which screen to capture (1 = primary)")
    p.add_argument("--fps", type=float, default=30)
    p.add_argument("--test", action="store_true",
                   help="wiring test: LED 0 red, last LED blue, a white dot running clockwise")
    args = p.parse_args(argv)

    if not (args.preview or args.wled or args.adalight):
        p.error("choose an output: --preview, --wled IP or --adalight PORT")
    if not 0 < args.depth <= 0.5:
        p.error("--depth must be between 0 and 0.5")
    return args


def test_pattern(n: int, step: int, brightness: float) -> np.ndarray:
    level = round(255 * brightness)
    c = np.zeros((n, 3), np.uint8)
    c[step % n] = level
    c[0] = (level, 0, 0)
    c[-1] = (0, 0, level)
    return c


def main(argv=None):
    args = parse_args(argv)
    layout = Layout(*args.leds, depth=args.depth, offset=args.offset, reverse=args.reverse)
    process = ColourProcessor(args.smoothing, args.brightness, args.gamma, args.saturation, args.max_amps)

    outputs, preview = [], None
    if args.wled:
        from .outputs import WLED
        outputs.append(WLED(args.wled))
    if args.adalight:
        from .outputs import Adalight
        outputs.append(Adalight(args.adalight, args.baud))
    if args.preview:
        from .preview import Preview
        preview = Preview(layout)

    import mss

    print(f"ScreenGlow: {layout.count} LEDs at {args.fps:g} fps. Ctrl+C to stop.")
    period = 1 / args.fps
    frames, last_report, step = 0, time.perf_counter(), 0
    try:
        with getattr(mss, "MSS", mss.mss)() as sct:
            if not 0 < args.monitor < len(sct.monitors):
                sys.exit(f"--monitor {args.monitor}: this PC has screens 1 to {len(sct.monitors) - 1}")
            mon = sct.monitors[args.monitor]
            stride = max(1, mon["width"] // SAMPLE_WIDTH)

            while preview is None or not preview.closed:
                start = time.perf_counter()

                if args.test:
                    frame = None
                    colours = test_pattern(layout.count, step, args.brightness)
                    step += 1
                else:
                    # mss gives BGRA; downscale and reorder to RGB
                    frame = np.asarray(sct.grab(mon))[::stride, ::stride, 2::-1]
                    colours = process(sample(frame, layout))

                for out in outputs:
                    out.send(colours)
                if preview:
                    preview.show(np.ascontiguousarray(frame) if frame is not None else None,
                                 colours, 1 if args.test else args.gamma)

                frames += 1
                now = time.perf_counter()
                if now - last_report >= 5:
                    print(f"  {frames / (now - last_report):5.1f} fps   ~{estimate_amps(colours):.2f} A")
                    frames, last_report = 0, now

                time.sleep(max(0.0, period - (time.perf_counter() - start)))
    except KeyboardInterrupt:
        pass
    finally:
        for out in outputs:
            out.close()
    print("ScreenGlow stopped.")


if __name__ == "__main__":
    main()
