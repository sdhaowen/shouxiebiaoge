from __future__ import annotations

import json
import random
from collections import deque
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


def _estimate_ink_threshold(img: Image.Image) -> int:
    """基于 Otsu 法估计墨迹阈值。"""
    hist = img.histogram()[:256]
    total = sum(hist)
    if total <= 0:
        return 180

    sum_all = 0
    for i, c in enumerate(hist):
        sum_all += i * c

    sum_bg = 0
    w_bg = 0
    best_thr = 180
    best_var = -1.0

    for t in range(256):
        w_bg += hist[t]
        if w_bg == 0:
            continue
        w_fg = total - w_bg
        if w_fg == 0:
            break

        sum_bg += t * hist[t]
        m_bg = sum_bg / w_bg
        m_fg = (sum_all - sum_bg) / w_fg
        between_var = w_bg * w_fg * (m_bg - m_fg) ** 2

        if between_var > best_var:
            best_var = between_var
            best_thr = t

    # 做夹紧，降低曝光极端图的误差
    return max(70, min(230, int(best_thr)))


def _ink_mask(img: Image.Image, threshold: int) -> Image.Image:
    # 255 表示墨迹，0 表示背景
    return img.point(lambda p: 255 if p <= threshold else 0, mode="L")


def _crop_to_ink_bbox(img: Image.Image, threshold: int | None = None) -> Image.Image:
    # 将深色像素视为墨迹，裁掉多余空白
    threshold = threshold if threshold is not None else _estimate_ink_threshold(img)
    mask = _ink_mask(img, threshold)
    bbox = mask.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def _crop_gray_and_mask_to_ink(gray: Image.Image, mask: Image.Image) -> Tuple[Image.Image, Image.Image]:
    bbox = mask.getbbox()
    if not bbox:
        return gray, mask
    return gray.crop(bbox), mask.crop(bbox)


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


def _segment_rows_by_ink_mask(mask: Image.Image) -> List[Tuple[int, int]]:
    px = mask.load()
    rows = []
    for y in range(mask.height):
        cnt = 0
        for x in range(mask.width):
            if px[x, y] > 0:
                cnt += 1
        rows.append(cnt)
    min_value = max(1, int(mask.width * 0.004))
    return _projection_runs(rows, min_value=min_value, min_run_width=3)


def _segment_cols_by_ink_mask(mask: Image.Image) -> List[Tuple[int, int]]:
    px = mask.load()
    cols = []
    for x in range(mask.width):
        cnt = 0
        for y in range(mask.height):
            if px[x, y] > 0:
                cnt += 1
        cols.append(cnt)
    min_value = max(1, int(mask.height * 0.05))
    return _projection_runs(cols, min_value=min_value, min_run_width=2)


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


def _connected_component_boxes(mask: Image.Image, min_area: int = 4) -> List[Tuple[int, int, int, int, int]]:
    """返回连通域包围盒 (x1,y1,x2,y2,area)。"""
    w, h = mask.size
    px = mask.load()
    visited = bytearray(w * h)
    boxes: List[Tuple[int, int, int, int, int]] = []

    for y in range(h):
        row_offset = y * w
        for x in range(w):
            idx = row_offset + x
            if visited[idx] or px[x, y] == 0:
                continue

            q = deque([(x, y)])
            visited[idx] = 1

            min_x = max_x = x
            min_y = max_y = y
            area = 0

            while q:
                cx, cy = q.popleft()
                area += 1
                if cx < min_x:
                    min_x = cx
                if cx > max_x:
                    max_x = cx
                if cy < min_y:
                    min_y = cy
                if cy > max_y:
                    max_y = cy

                for ny in range(max(0, cy - 1), min(h, cy + 2)):
                    ny_offset = ny * w
                    for nx in range(max(0, cx - 1), min(w, cx + 2)):
                        nidx = ny_offset + nx
                        if not visited[nidx] and px[nx, ny] > 0:
                            visited[nidx] = 1
                            q.append((nx, ny))

            if area >= min_area:
                boxes.append((min_x, min_y, max_x + 1, max_y + 1, area))

    return boxes


def _filter_noise_boxes(boxes: List[Tuple[int, int, int, int, int]]) -> List[Tuple[int, int, int, int, int]]:
    if not boxes:
        return boxes

    areas = sorted(b[4] for b in boxes)
    median_area = areas[len(areas) // 2]
    min_keep = max(4, int(median_area * 0.12))

    filtered = []
    for b in boxes:
        x1, y1, x2, y2, area = b
        if area < min_keep:
            continue
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        filtered.append(b)

    # 过滤后不能全空，否则保留最大连通域
    if not filtered:
        biggest = max(boxes, key=lambda x: x[4])
        return [biggest]
    return filtered


def _segments_from_component_boxes(boxes: List[Tuple[int, int, int, int, int]]) -> List[Tuple[int, int]]:
    if not boxes:
        return []

    ranges = sorted([(x1, x2) for x1, _, x2, _, _ in boxes], key=lambda t: t[0])
    merged: List[List[int]] = []

    for x1, x2 in ranges:
        if not merged or x1 > merged[-1][1] + 1:
            merged.append([x1, x2])
        else:
            merged[-1][1] = max(merged[-1][1], x2)

    return [(a, b) for a, b in merged]


def _merge_closest_segments(segments: List[Tuple[int, int]], target_count: int) -> List[Tuple[int, int]]:
    segs = segments[:]
    while len(segs) > target_count and len(segs) >= 2:
        best_i = 0
        best_gap = None
        for i in range(len(segs) - 1):
            gap = max(0, segs[i + 1][0] - segs[i][1])
            if best_gap is None or gap < best_gap:
                best_gap = gap
                best_i = i
        x1 = segs[best_i][0]
        x2 = segs[best_i + 1][1]
        segs = segs[:best_i] + [(x1, x2)] + segs[best_i + 2 :]
    return segs


def _split_segment_with_valley(mask: Image.Image, seg: Tuple[int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    x1, x2 = seg
    width = x2 - x1
    if width <= 2:
        mid = x1 + max(1, width // 2)
        return (x1, mid), (mid, x2)

    px = mask.load()
    mid = (x1 + x2) // 2

    best_x = None
    best_score = None
    for x in range(x1 + 1, x2):
        cnt = 0
        for y in range(mask.height):
            if px[x, y] > 0:
                cnt += 1
        # 先按墨迹数最少，再按离中点近
        score = (cnt, abs(x - mid))
        if best_score is None or score < best_score:
            best_score = score
            best_x = x

    if best_x is None:
        best_x = mid

    if best_x <= x1:
        best_x = x1 + 1
    if best_x >= x2:
        best_x = x2 - 1

    return (x1, best_x), (best_x, x2)


def _fit_segments_to_target(mask: Image.Image, segments: List[Tuple[int, int]], target_count: int) -> List[Tuple[int, int]]:
    if target_count <= 0:
        return []

    if not segments:
        return _split_equal(mask.width, target_count)

    segs = sorted(segments, key=lambda t: t[0])
    if len(segs) > target_count:
        segs = _merge_closest_segments(segs, target_count)

    while len(segs) < target_count:
        widest_i = max(range(len(segs)), key=lambda i: segs[i][1] - segs[i][0])
        left, right = _split_segment_with_valley(mask, segs[widest_i])

        # 宽度过小时继续等宽切，避免死循环
        if left[1] - left[0] <= 0 or right[1] - right[0] <= 0:
            x1, x2 = segs[widest_i]
            mid = max(x1 + 1, min(x2 - 1, (x1 + x2) // 2))
            left, right = (x1, mid), (mid, x2)

        segs = segs[:widest_i] + [left, right] + segs[widest_i + 1 :]
        segs = sorted(segs, key=lambda t: t[0])

        # 极端情况下仍不稳定，直接回退等宽
        if any(s[1] - s[0] <= 0 for s in segs):
            return _split_equal(mask.width, target_count)

    # 再次裁剪确保数量一致
    if len(segs) != target_count:
        return _split_equal(mask.width, target_count)

    return segs


def _text_chars_for_learning(text: str) -> List[str]:
    # 学习时忽略空白字符，避免空格变成“空字形”污染训练
    return [ch for ch in text.replace("\r", "") if ch not in {"\n", "\t", " "}]


def extract_glyphs_from_text_image(image_path: str | Path, text: str) -> List[Tuple[str, Image.Image]]:
    """
    从“上传的整张手写文字图片 + 对应文本”中提取单字字形。

    增强策略：
    - Otsu 阈值二值化
    - 连通域分析 + 噪点过滤
    - 目标字符数驱动的“过分割合并/粘连字切分”
    - 分割不稳定时回退等宽切分
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"上传图片不存在: {image_path}")

    chars = _text_chars_for_learning(text)
    if not chars:
        raise ValueError("上传样本文本为空，无法学习。")

    gray = _normalize_gray_image(image_path)
    thr = _estimate_ink_threshold(gray)
    mask = _ink_mask(gray, thr)

    gray, mask = _crop_gray_and_mask_to_ink(gray, mask)

    text_lines = [line for line in text.splitlines() if line.strip()]
    if not text_lines:
        text_lines = [text]

    row_runs = _segment_rows_by_ink_mask(mask)
    if len(text_lines) == 1 or len(row_runs) != len(text_lines):
        # 行数不匹配时：单行直接整行处理；多行按等高分配
        if len(text_lines) > 1:
            row_runs = _split_equal(mask.height, len(text_lines))
        else:
            row_runs = [(0, mask.height)]
            text_lines = [text.replace("\n", "")]

    results: List[Tuple[str, Image.Image]] = []

    for (y1, y2), line_text in zip(row_runs, text_lines):
        line_chars = _text_chars_for_learning(line_text)
        if not line_chars:
            continue

        line_gray = gray.crop((0, y1, gray.width, y2))
        line_mask = mask.crop((0, y1, mask.width, y2))
        line_gray, line_mask = _crop_gray_and_mask_to_ink(line_gray, line_mask)

        comp_boxes = _connected_component_boxes(line_mask)
        comp_boxes = _filter_noise_boxes(comp_boxes)

        segments = _segments_from_component_boxes(comp_boxes)

        if not segments:
            segments = _segment_cols_by_ink_mask(line_mask)

        segments = _fit_segments_to_target(line_mask, segments, len(line_chars))

        for ch, (x1, x2) in zip(line_chars, segments):
            glyph = line_gray.crop((x1, 0, x2, line_gray.height))
            glyph = _crop_to_ink_bbox(glyph, threshold=thr)
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
