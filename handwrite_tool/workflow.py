from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, Tuple

from .dataset import build_style_dataset_from_uploaded_images
from .word_filler import RenderConfig, fill_word_table_by_cell_map, fill_word_table_by_placeholders


def _project_dir(workspace_dir: str | Path, project_name: str) -> Path:
    return Path(workspace_dir) / project_name


def _manifest_path(workspace_dir: str | Path, project_name: str) -> Path:
    return _project_dir(workspace_dir, project_name) / "project.json"


def _load_manifest(workspace_dir: str | Path, project_name: str) -> dict:
    path = _manifest_path(workspace_dir, project_name)
    if not path.exists():
        raise FileNotFoundError(f"项目不存在，请先执行 step1-train: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(workspace_dir: str | Path, project_name: str, data: dict) -> Path:
    project_dir = _project_dir(workspace_dir, project_name)
    project_dir.mkdir(parents=True, exist_ok=True)
    path = _manifest_path(workspace_dir, project_name)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _parse_samples_json(samples_json_path: str | Path) -> list[tuple[str, str]]:
    path = Path(samples_json_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    samples = []
    for item in raw:
        image = item.get("image")
        text = item.get("text", "")
        if not image:
            raise ValueError("samples_json 中每项都必须包含 image 字段。")
        image_path = Path(image)
        if not image_path.is_absolute():
            image_path = (path.parent / image_path).resolve()
        samples.append((str(image_path), text))
    return samples


def step1_train_uploaded(
    workspace_dir: str | Path,
    project_name: str,
    samples_json_path: str | Path,
    seed: int = 42,
) -> Tuple[Path, Path]:
    """步骤1：上传手写样本并训练样式。"""
    workspace_dir = Path(workspace_dir)
    project_dir = _project_dir(workspace_dir, project_name)
    styles_root = project_dir / "styles"
    style_name = "trained_style"

    samples = _parse_samples_json(samples_json_path)
    meta_path = build_style_dataset_from_uploaded_images(
        samples=samples,
        output_dir=styles_root,
        style_name=style_name,
        seed=seed,
    )

    style_dir = styles_root / style_name

    old = {}
    manifest = _manifest_path(workspace_dir, project_name)
    if manifest.exists():
        old = json.loads(manifest.read_text(encoding="utf-8"))

    data = {
        "project_name": project_name,
        "workspace_dir": str(workspace_dir.resolve()),
        "style_dir": str(style_dir.resolve()),
        "forms": old.get("forms", {}),
        "source_samples": str(Path(samples_json_path).resolve()),
    }
    manifest_path = _save_manifest(workspace_dir, project_name, data)
    return meta_path, manifest_path


def step2_upload_form(
    workspace_dir: str | Path,
    project_name: str,
    form_file: str | Path,
    form_name: str | None = None,
) -> Tuple[Path, Path]:
    """步骤2：上传需要填写的表格文件。"""
    form_file = Path(form_file)
    if not form_file.exists():
        raise FileNotFoundError(f"表格文件不存在: {form_file}")
    if form_file.suffix.lower() != ".docx":
        raise ValueError("目前仅支持 .docx 表格文件。")

    data = _load_manifest(workspace_dir, project_name)

    resolved_name = form_name.strip() if form_name else form_file.stem
    forms_dir = _project_dir(workspace_dir, project_name) / "forms"
    forms_dir.mkdir(parents=True, exist_ok=True)

    dst = forms_dir / f"{resolved_name}.docx"
    shutil.copyfile(form_file, dst)

    forms: Dict[str, str] = data.get("forms", {})
    forms[resolved_name] = str(dst.resolve())
    data["forms"] = forms
    manifest_path = _save_manifest(workspace_dir, project_name, data)
    return dst, manifest_path


def _parse_cell_map_dict(raw: dict) -> Dict[Tuple[int, int, int], str]:
    out: Dict[Tuple[int, int, int], str] = {}
    for key, value in raw.items():
        t, r, c = [int(x.strip()) for x in key.split(",")]
        out[(t, r, c)] = str(value)
    return out


def step3_generate_handwrite(
    workspace_dir: str | Path,
    project_name: str,
    form_name: str,
    data_json_path: str | Path,
    output_docx: str | Path,
    *,
    mode: str = "placeholder",
    height: int = 56,
    char_gap: int = 8,
    image_width_mm: float = 40.0,
    seed: int = 42,
) -> Path:
    """步骤3：将表格内容文字转换为手写样式并写入表格。"""
    data = _load_manifest(workspace_dir, project_name)

    style_dir = data.get("style_dir")
    if not style_dir:
        raise ValueError("项目中缺少 style_dir，请先执行 step1-train。")

    forms = data.get("forms", {})
    if form_name not in forms:
        available = ", ".join(sorted(forms.keys())) if forms else "(空)"
        raise KeyError(f"未找到表格名 '{form_name}'，可用表格: {available}")

    form_path = Path(forms[form_name])
    payload = json.loads(Path(data_json_path).read_text(encoding="utf-8"))

    render = RenderConfig(line_height=height, char_gap=char_gap)

    if mode == "placeholder":
        return fill_word_table_by_placeholders(
            input_docx=form_path,
            output_docx=output_docx,
            style_dir=style_dir,
            data=payload,
            render=render,
            image_width_mm=image_width_mm,
            seed=seed,
        )

    if mode == "cellmap":
        return fill_word_table_by_cell_map(
            input_docx=form_path,
            output_docx=output_docx,
            style_dir=style_dir,
            cell_values=_parse_cell_map_dict(payload),
            render=render,
            image_width_mm=image_width_mm,
            seed=seed,
        )

    raise ValueError("mode 仅支持: placeholder 或 cellmap")
