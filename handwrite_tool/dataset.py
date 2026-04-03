from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageOps


SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class GlyphEntry:
    file: str
    w: int
    h: int


@dataclass
class StyleMeta:
    name: str
    source_dir: str
    total_images: int
    chars: Dict[str, int]


def _normalize_char_folder_name(name: str) -> str:
    """
    目录名即字符本身，例如：
    - '张' -> 张
    - 'A' -> A
    - 'space' 或 '_' -> 空格
    """
    lowered = name.strip().lower()
    if lowered in {"space", "blank", "_"}:
        return " "
    return name


def _prepare_glyph_image(path: Path) -> Image.Image:
    img = Image.open(path).convert("L")
    # 自动反色并清理边缘，统一黑字白底。
    img = ImageOps.autocontrast(img)
    # 若平均亮度偏暗，认为背景黑色，进行反色。
    if sum(img.getdata()) / (img.width * img.height) < 127:
        img = ImageOps.invert(img)
    # 去除多余空白边界。
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    return img


def build_style_dataset(input_dir: str | Path, output_dir: str | Path, style_name: str, seed: int = 42) -> Path:
    """
    从手写字符图片目录构建样式库。

    输入目录组织约定：
      input_dir/
        张/
          1.png
          2.png
        三/
          a.jpg
        space/
          1.png

    输出：
      output_dir/style_name/
        glyphs/<char>/<uuid>.png
        meta.json
    """
    random.seed(seed)

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    style_dir = output_dir / style_name
    glyph_root = style_dir / "glyphs"

    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    glyph_root.mkdir(parents=True, exist_ok=True)

    char_map: Dict[str, List[GlyphEntry]] = {}
    total_images = 0

    for char_folder in sorted(input_dir.iterdir()):
        if not char_folder.is_dir():
            continue

        ch = _normalize_char_folder_name(char_folder.name)
        bucket = char_map.setdefault(ch, [])

        out_char_dir = glyph_root / f"U+{ord(ch):04X}"
        out_char_dir.mkdir(parents=True, exist_ok=True)

        idx = 0
        for img_file in sorted(char_folder.iterdir()):
            if img_file.suffix.lower() not in SUPPORTED_IMAGE_EXT:
                continue
            idx += 1
            glyph_img = _prepare_glyph_image(img_file)
            out_file = out_char_dir / f"{idx:04d}.png"
            glyph_img.save(out_file)
            bucket.append(GlyphEntry(file=str(out_file.relative_to(style_dir)), w=glyph_img.width, h=glyph_img.height))
            total_images += 1

    if total_images == 0:
        raise ValueError("未发现可用图片，请检查输入目录结构和图片格式。")

    meta = {
        "name": style_name,
        "source_dir": str(input_dir),
        "total_images": total_images,
        "chars": {ch: [entry.__dict__ for entry in entries] for ch, entries in char_map.items()},
    }

    style_dir.mkdir(parents=True, exist_ok=True)
    meta_path = style_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


def load_style_meta(style_dir: str | Path) -> dict:
    style_dir = Path(style_dir)
    meta_path = style_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"找不到样式元数据: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def sample_glyph_file(style_dir: str | Path, meta: dict, ch: str) -> Tuple[Path, dict] | Tuple[None, None]:
    style_dir = Path(style_dir)
    entries = meta.get("chars", {}).get(ch)
    if not entries:
        return None, None
    picked = random.choice(entries)
    return style_dir / picked["file"], picked
