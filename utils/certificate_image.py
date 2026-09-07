"""Generates a certificate PNG on the fly (no file storage needed).

Set LOGO_URL below to your logo's raw.githubusercontent.com URL once you've
uploaded one — falls back to a text wordmark if the logo can't be fetched.
"""

import io
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont

LOGO_URL = "https://raw.githubusercontent.com/karkavelrajaj-coder/dsiar-lms/main/assets/dsiar-logo.png"

WIDTH, HEIGHT = 1600, 1131  # A4-ish landscape
NAVY = (17, 34, 68)
GOLD = (196, 155, 62)
GRAY = (110, 110, 110)


def _font(size, bold=False):
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
        if bold
        else ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
    )
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _center_text(draw, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)


def _fetch_logo(max_width=260):
    try:
        resp = requests.get(LOGO_URL, timeout=5)
        resp.raise_for_status()
        logo = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        ratio = max_width / logo.width
        logo = logo.resize((max_width, int(logo.height * ratio)))
        return logo
    except Exception:
        return None


def build_certificate(student_name: str, course_title: str, cert_id: str, issued_at: datetime) -> bytes:
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    # Border
    border_margin = 30
    draw.rectangle(
        [border_margin, border_margin, WIDTH - border_margin, HEIGHT - border_margin],
        outline=GOLD,
        width=6,
    )
    inner_margin = 50
    draw.rectangle(
        [inner_margin, inner_margin, WIDTH - inner_margin, HEIGHT - inner_margin],
        outline=NAVY,
        width=2,
    )

    # Logo (or text wordmark fallback)
    logo = _fetch_logo()
    y_cursor = 110
    if logo:
        img.paste(logo, (int((WIDTH - logo.width) / 2), y_cursor), logo)
        y_cursor += logo.height + 40
    else:
        _center_text(draw, y_cursor, "D'SIAR TECH", _font(52, bold=True), NAVY)
        y_cursor += 100

    _center_text(draw, y_cursor, "CERTIFICATE OF COMPLETION", _font(44, bold=True), NAVY)
    y_cursor += 70

    # decorative divider
    div_w = 260
    draw.line([((WIDTH - div_w) / 2, y_cursor), ((WIDTH + div_w) / 2, y_cursor)], fill=GOLD, width=3)
    y_cursor += 70

    _center_text(draw, y_cursor, "This certifies that", _font(28), GRAY)
    y_cursor += 80

    _center_text(draw, y_cursor, student_name, _font(66, bold=True), GOLD)
    y_cursor += 110

    _center_text(draw, y_cursor, "has successfully completed the course", _font(28), GRAY)
    y_cursor += 80

    _center_text(draw, y_cursor, course_title, _font(42, bold=True), NAVY)
    y_cursor += 90

    div_w2 = 160
    draw.line([((WIDTH - div_w2) / 2, y_cursor), ((WIDTH + div_w2) / 2, y_cursor)], fill=GOLD, width=2)
    y_cursor += 60

    date_str = issued_at.strftime("%B %d, %Y")
    _center_text(draw, y_cursor, f"Issued on {date_str}", _font(24), GRAY)

    # Footer: certificate ID + signature line
    draw.text((inner_margin + 40, HEIGHT - inner_margin - 90), f"Certificate ID: {cert_id}", font=_font(18), fill=GRAY)

    sig_x = WIDTH - inner_margin - 400
    draw.line([(sig_x, HEIGHT - inner_margin - 110), (sig_x + 350, HEIGHT - inner_margin - 110)], fill=NAVY, width=2)
    draw.text((sig_x + 90, HEIGHT - inner_margin - 100), "D'siar Tech", font=_font(20, bold=True), fill=NAVY)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
