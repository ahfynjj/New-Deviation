#!/usr/bin/env python3
"""Run a built emulator in capture mode and validate its real RGB framebuffer.

Use native Windows Python so the capture filename passed to fopen is native.
"""
import argparse
import os
from pathlib import Path
import subprocess
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=("tx15", "devo8"), default="tx15")
    parser.add_argument("--page", choices=("main", "mixer", "curve"), default="main")
    parser.add_argument("--native-root", type=Path,
                        default=Path(tempfile.gettempdir()) / "new-deviation-ucrt64")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="deviation-capture-") as tmp:
        capture = Path(tmp) / "screen.ppm"
        env = os.environ.copy()
        env["PATH"] = str(args.native_root / "bin") + os.pathsep + env["PATH"]
        env["DEVIATION_EMU_CAPTURE"] = str(capture)
        env["DEVIATION_EMU_CAPTURE_PAGE"] = args.page
        runtime = Path(tmp) / "filesystem"
        shutil.copytree(root / "src/filesystem" / args.target, runtime)
        env["DEVIATION_EMU_FILESYSTEM"] = str(runtime)
        startup = None
        if os.name == "nt":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        try:
            result = subprocess.run([str(root / "src" / ("emu_" + args.target + ".exe"))],
                                    cwd=root / "src", env=env, startupinfo=startup,
                                    capture_output=True, timeout=15)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"Capture timed out: {error.stdout!r} {error.stderr!r}") from error
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        data = capture.read_bytes()
        magic, size, maximum, pixels = data.split(b"\n", 3)
        expected = (480, 320) if args.target == "tx15" else (320, 240)
        assert magic == b"P6" and maximum == b"255", "Invalid PPM"
        assert tuple(map(int, size.split())) == expected, "Wrong canvas dimensions"
        assert len(pixels) == expected[0] * expected[1] * 3, "Incomplete framebuffer"
        assert len(set(pixels)) > 8, "Blank/near-blank framebuffer"
        if args.page == "curve":
            # The real curve plot occupies the right half. The error page has
            # only a flat background there; dimensions/colour count alone pass.
            width, height = expected
            plot = b"".join(pixels[(row * width + width // 2) * 3:(row * width + width - 20) * 3]
                            for row in range(60, height - 40))
            colours = {plot[i:i + 3] for i in range(0, len(plot), 3)}
            assert len(colours) > 2, "Curve plot missing (possibly invalid model)"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print(f"PASS {args.target}/{args.page}: {size.decode()}, {len(pixels)} RGB bytes -> {args.output}")


if __name__ == "__main__":
    main()
