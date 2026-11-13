#!/usr/bin/env python3
"""상세페이지 이미지(URL 또는 파일)에서 필요한 부분만 잘라 블로그용으로 저장.

상세페이지는 세로로 아주 긴 이미지인 경우가 많아, 세로 범위를 지정해 잘라냅니다.
  python3 tools/crop_image.py <URL|파일> -o posts/x/detail-1.jpg --top 2400 --bottom 3300
  python3 tools/crop_image.py <URL|파일> -o out.jpg --top 35% --bottom 48%
  python3 tools/crop_image.py <URL|파일> --info        # 크기만 확인
옵션: --left/--right 로 가로도 자를 수 있고, --width 로 결과 폭(기본 860px)을 맞춥니다.
"""
import argparse
import io
import os
import sys
import urllib.request

from PIL import Image

Image.MAX_IMAGE_PIXELS = None  # 상세페이지 긴 이미지 허용


def load(src):
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0", "Referer": src})
        with urllib.request.urlopen(req, timeout=30) as r:
            return Image.open(io.BytesIO(r.read()))
    return Image.open(src)


def pos(value, total):
    if value is None:
        return None
    value = value.strip()
    if value.endswith("%"):
        return int(total * float(value[:-1]) / 100)
    return int(value)


def main():
    ap = argparse.ArgumentParser(description="상세페이지 이미지 부분 자르기")
    ap.add_argument("src")
    ap.add_argument("-o", "--output")
    ap.add_argument("--top")
    ap.add_argument("--bottom")
    ap.add_argument("--left")
    ap.add_argument("--right")
    ap.add_argument("--width", type=int, default=860)
    ap.add_argument("--info", action="store_true")
    a = ap.parse_args()

    img = load(a.src)
    w, h = img.size
    if a.info:
        print(f"{w}x{h}")
        return
    if not a.output:
        sys.exit("-o 출력 경로가 필요해요")

    box = (pos(a.left, w) or 0, pos(a.top, h) or 0, pos(a.right, w) or w, pos(a.bottom, h) or h)
    if box[0] >= box[2] or box[1] >= box[3]:
        sys.exit(f"자를 범위가 잘못됐어요: {box} (원본 {w}x{h})")
    out = img.crop(box).convert("RGB")
    if a.width and out.width > a.width:
        out = out.resize((a.width, round(out.height * a.width / out.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    out.save(a.output, quality=90)
    print(f"저장: {a.output} ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
