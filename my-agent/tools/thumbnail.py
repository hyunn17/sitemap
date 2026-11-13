#!/usr/bin/env python3
"""쇼핑포유 시그니처 3D 팝 썸네일 (1080x1080 PNG).

사용:
  python3 tools/thumbnail.py "카본매트" "온수매트" "실사용비교" -o posts/thumb-carbon.png

- assets/thumb_template.png 가 있으면 그 위에 글자만 올립니다 (기존 템플릿 사용).
- 없으면 민트 배경 + 컨페티 + 크림 카드 + 선물상자 + 별점을 직접 그립니다.
- 폰트(Black Han Sans, OFL)는 fonts/ 에 없으면 자동으로 내려받습니다.
"""
import argparse
import os
import random
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONT_PATH = os.path.join(ROOT, "fonts", "BlackHanSans-Regular.ttf")
FONT_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/blackhansans/BlackHanSans-Regular.ttf"
TEMPLATE = os.path.join(ROOT, "assets", "thumb_template.png")

SIZE = 1080
CARD = (108, 170, 972, 905)  # left, top, right, bottom
LINE_COLORS = ["#B8F2E6", "#E8D7F1", "#FFAE33"]  # 민트 / 퍼플 / 옐로우
OUTLINE = (40, 15, 5)
SHADOW = (60, 20, 10)


def ensure_font():
    if not os.path.exists(FONT_PATH):
        os.makedirs(os.path.dirname(FONT_PATH), exist_ok=True)
        print("폰트 내려받는 중…")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    return FONT_PATH


def star(draw, cx, cy, r, fill):
    import math
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        a = math.pi / 2 + i * math.pi / 5
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    draw.polygon(pts, fill=fill, outline=OUTLINE)


def draw_background(font_path):
    img = Image.new("RGB", (SIZE, SIZE), "#9DE2D5")
    d = ImageDraw.Draw(img)
    rnd = random.Random(7)
    confetti = ["#FFD6E0", "#FFF1A8", "#C9E4FF", "#E8D7F1", "#FFFFFF", "#FFB4A2"]
    for _ in range(110):
        x, y = rnd.randrange(SIZE), rnd.randrange(SIZE)
        c = rnd.choice(confetti)
        if rnd.random() < 0.5:
            r = rnd.randrange(5, 11)
            d.ellipse((x - r, y - r, x + r, y + r), fill=c)
        else:
            w, h = rnd.randrange(8, 20), rnd.randrange(4, 8)
            d.rounded_rectangle((x, y, x + w, y + h), radius=2, fill=c)

    l, t, r, b = CARD
    d.rounded_rectangle((l + 10, t + 14, r + 10, b + 14), radius=48, fill="#7CC3B6")  # 카드 그림자
    d.rounded_rectangle(CARD, radius=48, fill="#FFF8DC", outline="#E9DDB5", width=4)

    # 우상단 선물상자
    gx, gy = 840, 70
    d.rounded_rectangle((gx, gy + 40, gx + 150, gy + 150), radius=12, fill="#FF8FAB", outline=OUTLINE, width=5)
    d.rounded_rectangle((gx - 10, gy + 15, gx + 160, gy + 55), radius=10, fill="#FFA6BE", outline=OUTLINE, width=5)
    d.rectangle((gx + 62, gy + 15, gx + 88, gy + 150), fill="#FFC94D", outline=OUTLINE, width=4)
    d.ellipse((gx + 25, gy - 25, gx + 75, gy + 22), fill="#FFC94D", outline=OUTLINE, width=5)
    d.ellipse((gx + 75, gy - 25, gx + 125, gy + 22), fill="#FFC94D", outline=OUTLINE, width=5)

    # 우하단 별점 + 로고
    for i in range(5):
        star(d, 650 + i * 62, 960, 26, "#FFC94D")
    logo = ImageFont.truetype(font_path, 44)
    d.text((120, 935), "쇼핑포유", font=logo, fill="#FFFFFF", stroke_width=5, stroke_fill=OUTLINE)
    return img


def fit_font(draw, font_path, text, max_w, max_size=155, min_size=65):
    size = max_size
    while size > min_size:
        f = ImageFont.truetype(font_path, size)
        b = draw.textbbox((0, 0), text, font=f, stroke_width=7)
        if b[2] - b[0] <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(font_path, min_size)


def draw_3d_pop(draw, text, font, y, fill):
    l, _, r, _ = CARD
    bbox = draw.textbbox((0, 0), text, font=font)
    x = l + (r - l) // 2 - (bbox[2] - bbox[0]) // 2 - bbox[0]
    for off in range(1, 15):  # 우하단 대각선 그림자 14px
        draw.text((x + off, y + off), text, font=font, fill=SHADOW, stroke_width=7, stroke_fill=SHADOW)
    draw.text((x, y), text, font=font, fill=fill, stroke_width=7, stroke_fill=OUTLINE)


def generate(lines, output):
    font_path = ensure_font()
    if os.path.exists(TEMPLATE):
        base = Image.open(TEMPLATE).convert("RGB").resize((SIZE, SIZE))
    else:
        base = draw_background(font_path)
    draw = ImageDraw.Draw(base)

    l, t, r, b = CARD
    max_w = (r - l) - 100
    fonts = [fit_font(draw, font_path, s, max_w) for s in lines]
    heights = []
    for s, f in zip(lines, fonts):
        bb = draw.textbbox((0, 0), s, font=f)
        heights.append(bb[3] - bb[1])
    gap = 40
    total = sum(heights) + gap * (len(lines) - 1)
    y = t + (b - t - total) // 2 - 8
    for s, f, h, c in zip(lines, fonts, heights, LINE_COLORS):
        top_off = draw.textbbox((0, 0), s, font=f)[1]
        draw_3d_pop(draw, s, f, y - top_off, c)
        y += h + gap

    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    base.save(output, "PNG")
    print(f"썸네일 생성: {output}")


def main():
    ap = argparse.ArgumentParser(description="쇼핑포유 3D 팝 썸네일")
    ap.add_argument("lines", nargs=3, help="1행 2행 3행 문구")
    ap.add_argument("-o", "--output", default="posts/thumb.png")
    a = ap.parse_args()
    generate(a.lines, a.output)


if __name__ == "__main__":
    main()
