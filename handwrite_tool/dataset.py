from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

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


def _normalize_gray_image(path: Path) -> Image.Image:
    img = Image.open(path).convert("L")
    img = ImageOps.autocontrast(img)
    # 若平均亮度偏暗，认为背景黑色，进行反色
    if sum(img.getdata()) / (img.width * img.height) < 127:
        img = ImageOps.invert(img)
    return img


def _crop_to_ink_bbox(img: Image.Image, threshold: int = 220) -> Image.Image:
    # 将深色像素视为墨迹，裁掉多余空白
    mask = img.point(lambda p: 255 if p < threshold else 0, mode="L")
    bbox = mask.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def _prepare_glyph_image(path: Path) -> Image.Image:
    img = _normalize_gray_image(path)
    return _crop_to_ink_bbox(img)


def _projection_runs(values: List[int], min_value: int = 1, min_run_width: int = 2) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
    start = None
    for i, v in enumerate(values):
        if v >= min_value and start is None:
            start = i
        elif v < min_value and start is not None:
            if i - start >= min_run_width:
                runs.append((start, i))
            start = None
    if start is not None and len(values) - start >= min_run_width:
        runs.append((start, len(values)))
    return runs


def _segment_rows_by_ink(img: Image.Image, threshold: int = 220) -> List[Tuple[int, int]]:
    px = img.load()
    rows = []
    for y in range(img.height):
        cnt = 0
        for x in range(img.width):
            if px[x, y] < threshold:
                cnt += 1
        rows.append(cnt)
    return _projection_runs(rows, min_value=1, min_run_width=3)


def _segment_cols_by_ink(img: Image.Image, threshold: int = 220) -> List[Tuple[int, int]]:
    px = img.load()
    cols = []
    for x in range(img.width):
        cnt = 0
        for y in range(img.height):
            if px[x, y] < threshold:
                cnt += 1
        cols.append(cnt)
    return _projection_runs(cols, min_value=1, min_run_width=2)


def _split_equal(width: int, n: int) -> List[Tuple[int, int]]:
    if n <= 0:
        return []
    out = []
    for i in range(n):
        x1 = int(round(i * width / n))
        x2 = int(round((i + 1) * width / n))
        if x2 <= x1:
            x2 = min(width, x1 + 1)
        out.append((x1, x2))
    return out


def _text_chars_for_learning(text: str) -> List[str]:
    # 学习时忽略空白字符，避免空格变成“空字形”污染训练
    return [ch for ch in text.replace("\r", "") if ch not in {"\n", "\t", " "}]


def extract_glyphs_from_text_image(image_path: str | Path, text: str) -> List[Tuple[str, Image.Image]]:
    """
    从“上传的整张手写文字图片 + 对应文本”中提取单字字形。

    说明：
    - 推荐一行文字一张图，字符间有一定间距
    - 若自动分割字符数与文本字符数不一致，会回退为等宽切分
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"上传图片不存在: {image_path}")

    chars = _text_chars_for_learning(text)
    if not chars:
        raise ValueError("上传样本文本为空，无法学习。")

    img = _normalize_gray_image(image_path)
    img = _crop_to_ink_bbox(img)

    # 支持简单多行：按文本行数尝试行分割；不一致时退化为单行处理
    text_lines = [line for line in text.splitlines() if line.strip()]
    if not text_lines:
        text_lines = [text]

    row_runs = _segment_rows_by_ink(img)
    if len(text_lines) == 1 or len(row_runs) != len(text_lines):
        row_runs = [(0, img.height)]
        text_lines = [text.replace("\n", "")]

    results: List[Tuple[str, Image.Image]] = []

    for (y1, y2), line_text in zip(row_runs, text_lines):
        line_chars = _text_chars_for_learning(line_text)
        if not line_chars:
            continue
        line_img = img.crop((0, y1, img.width, y2))
        line_img = _crop_to_ink_bbox(line_img)

        col_runs = _segment_cols_by_ink(line_img)
        if len(col_runs) != len(line_chars):
            col_runs = _split_equal(line_img.width, len(line_chars))

        for ch, (x1, x2) in zip(line_chars, col_runs):
            glyph = line_img.crop((x1, 0, x2, line_img.height))
            glyph = _crop_to_ink_bbox(glyph)
            if glyph.width <= 1 or glyph.height <= 1:
                continue
            results.append((ch, glyph))

    if not results:
        raise ValueError(
            "未从上传图片中提取到可用字符，请检查图片清晰度、背景对比度，或让文字更疏一些再上传。"
        )

    return results


def _save_glyph_entries(
    style_dir: Path,
    style_name: str,
    glyph_pairs: Iterable[Tuple[str, Image.Image]],
    source: str,
    seed: int,
) -> Path:
    random.seed(seed)

    glyph_root = style_dir / "glyphs"
    glyph_root.mkdir(parents=True, exist_ok=True)

    char_map: Dict[str, List[GlyphEntry]] = {}
    char_index: Dict[str, int] = {}
    total_images = 0

    for ch, glyph_img in glyph_pairs:
        bucket = char_map.setdefault(ch, [])
        out_char_dir = glyph_root / f"U+{ord(ch):04X}"
        out_char_dir.mkdir(parents=True, exist_ok=True)

        next_idx = char_index.get(ch, 0) + 1
        char_index[ch] = next_idx

        out_file = out_char_dir / f"{next_idx:04d}.png"
        glyph_img.save(out_file)

        bucket.append(
            GlyphEntry(
                file=str(out_file.relative_to(style_dir)),
                w=glyph_img.width,
                h=glyph_img.height,
            )
        )
        total_images += 1

    if total_images == 0:
        raise ValueError("未生成任何字形样本。")

    meta = {
        "name": style_name,
        "source": source,
        "total_images": total_images,
        "chars": {ch: [entry.__dict__ for entry in entries] for ch, entries in char_map.items()},
    }

    style_dir.mkdir(parents=True, exist_ok=True)
    meta_path = style_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


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
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    style_dir = output_dir / style_name

    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    pairs: List[Tuple[str, Image.Image]] = []
    for char_folder in sorted(input_dir.iterdir()):
        if not char_folder.is_dir():
            continue

        ch = _normalize_char_folder_name(char_folder.name)
        for img_file in sorted(char_folder.iterdir()):
            if img_file.suffix.lower() not in SUPPORTED_IMAGE_EXT:
                continue
            pairs.append((ch, _prepare_glyph_image(img_file)))

    if not pairs:
        raise ValueError("未发现可用图片，请检查输入目录结构和图片格式。")

    return _save_glyph_entries(
        style_dir=style_dir,
        style_name=style_name,
        glyph_pairs=pairs,
        source=f"folder_dataset:{input_dir}",
        seed=seed,
    )


def build_style_dataset_from_uploaded_images(
    samples: Sequence[Tuple[str | Path, str]],
    output_dir: str | Path,
    style_name: str,
    seed: int = 42,
) -> Path:
    """
    从“上传的手写文字图片 + 对应文本”构建样式库。

    samples: [(image_path, text), ...]
    """
    if not samples:
        raise ValueError("未提供上传样本。")

    output_dir = Path(output_dir)
    style_dir = output_dir / style_name

    pairs: List[Tuple[str, Image.Image]] = []
    source_items = []

    for image_path, text in samples:
        image_path = Path(image_path)
        if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXT:
            raise ValueError(f"不支持的图片格式: {image_path}")
        glyphs = extract_glyphs_from_text_image(image_path, text)
        pairs.extend(glyphs)
        source_items.append({"image": str(image_path), "text": text})

    return _save_glyph_entries(
        style_dir=style_dir,
        style_name=style_name,
        glyph_pairs=pairs,
        source=f"uploaded_images:{json.dumps(source_items, ensure_ascii=False)}",
        seed=seed,
    )


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
