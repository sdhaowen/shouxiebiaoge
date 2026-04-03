from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

from .dataset import load_style_meta, sample_glyph_file


def _paste_dark_pixels(canvas: Image.Image, glyph: Image.Image, x: int, y: int) -> None:
    """仅把字形中的深色像素贴到画布，白色背景透明处理。"""
    glyph = glyph.convert("L")
    alpha = ImageOps.invert(glyph)
    ink = Image.new("L", glyph.size, color=0)
    canvas.paste(ink, (x, y), mask=alpha)


def render_text_to_image(
    style_dir: str | Path,
    text: str,
    out_path: str | Path,
    *,
    height: int = 64,
    char_gap: int = 8,
    left_padding: int = 8,
    top_padding: int = 8,
    fallback: str = "?",
    seed: Optional[int] = None,
) -> Path:
    """按样式库渲染一段文本为手写图片。"""
    if seed is not None:
        random.seed(seed)

    style_dir = Path(style_dir)
    out_path = Path(out_path)

    meta = load_style_meta(style_dir)

    glyphs = []
    total_width = left_padding

    for ch in text:
        use_ch = ch
        glyph_path, info = sample_glyph_file(style_dir, meta, use_ch)
        if glyph_path is None and fallback:
            glyph_path, info = sample_glyph_file(style_dir, meta, fallback)
        if glyph_path is None:
            # 无可用字形时按空白处理
            total_width += int(height * 0.45) + char_gap
            glyphs.append(None)
            continue

        glyph_img = Image.open(glyph_path).convert("L")
        ratio = max(info["h"], 1)
        new_h = max(1, height)
        new_w = max(1, int(info["w"] * (new_h / ratio)))
        glyph_img = glyph_img.resize((new_w, new_h))
        glyphs.append(glyph_img)
        total_width += new_w + char_gap

    total_width += left_padding
    canvas_h = height + top_padding * 2
    canvas = Image.new("L", (max(total_width, 32), max(canvas_h, 32)), color=255)

    x = left_padding
    baseline_jitter = max(1, height // 12)
    for glyph in glyphs:
        if glyph is None:
            x += int(height * 0.45) + char_gap
            continue
        jitter = random.randint(-baseline_jitter, baseline_jitter)
        y = top_padding + jitter
        _paste_dark_pixels(canvas, glyph, x, y)
        x += glyph.width + char_gap

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path
