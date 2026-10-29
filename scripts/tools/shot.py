#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""HTML -> 精确像素 PNG。

用本机 Chrome/Edge 无头模式截屏，不做二次缩放，
所以 900x383 / 1080x1080 是真正的精确像素，中文字一个不差。

用法：
    python shot.py in.html out.png 900 383
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CFG = __import__("json").loads((ROOT / "config.json").read_text(encoding="utf-8"))


def find_browser():
    for p in CFG["chrome"]:
        if Path(p).exists():
            return p
    raise SystemExit("找不到 Chrome/Edge，可在 config.json 的 chrome 里补路径")


def shot(html_path: Path, out_path: Path, w: int, h: int, timeout=60):
    """把 html 渲染成 w x h 的 png，返回实际尺寸。"""
    html_path = Path(html_path).resolve()
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    browser = find_browser()
    # Chrome 在 Windows 下对 file:// + 非 ASCII 路径偶发失败，复制到临时 ASCII 路径再截
    with tempfile.TemporaryDirectory() as td:
        tmp_html = Path(td) / "page.html"
        tmp_html.write_bytes(html_path.read_bytes())
        tmp_png = Path(td) / "shot.png"
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--default-background-color=00000000",
            f"--window-size={w},{h}",
            f"--screenshot={tmp_png}",
            tmp_html.as_uri(),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if not tmp_png.exists():
            raise SystemExit(f"截屏失败：{(r.stderr or r.stdout)[-600:]}")
        out_path.write_bytes(tmp_png.read_bytes())

    im = Image.open(out_path)
    if im.size != (w, h):
        im = im.convert("RGB").resize((w, h), Image.LANCZOS)
        im.save(out_path)
        print(f"[warn] 实际 {im.size}，已强制归位到 {w}x{h}")
    return Image.open(out_path).size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("w", type=int)
    ap.add_argument("h", type=int)
    a = ap.parse_args()
    size = shot(a.html, a.out, a.w, a.h)
    print(f"ok {a.out} {size[0]}x{size[1]} {os.path.getsize(a.out)//1024}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
