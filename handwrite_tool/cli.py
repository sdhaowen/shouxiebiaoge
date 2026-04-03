from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import build_style_dataset, build_style_dataset_from_uploaded_images
from .renderer import render_text_to_image
from .word_filler import RenderConfig, fill_word_table_by_cell_map, fill_word_table_by_placeholders
from .workflow import step1_train_uploaded, step2_upload_form, step3_generate_handwrite


def cmd_build_style(args: argparse.Namespace) -> None:
    meta = build_style_dataset(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        style_name=args.style_name,
        seed=args.seed,
    )
    print(f"样式库构建完成: {meta}")


def cmd_build_style_uploaded(args: argparse.Namespace) -> None:
    sample_file = Path(args.samples_json)
    samples_raw = json.loads(sample_file.read_text(encoding="utf-8"))

    samples = []
    for item in samples_raw:
        img = item.get("image")
        text = item.get("text", "")
        if not img:
            raise ValueError("samples_json 中每个对象都必须包含 image 字段。")
        samples.append((img, text))

    meta = build_style_dataset_from_uploaded_images(
        samples=samples,
        output_dir=args.output_dir,
        style_name=args.style_name,
        seed=args.seed,
    )
    print(f"上传图片样式学习完成: {meta}")


def cmd_step1_train(args: argparse.Namespace) -> None:
    meta, manifest = step1_train_uploaded(
        workspace_dir=args.workspace_dir,
        project_name=args.project,
        samples_json_path=args.samples_json,
        seed=args.seed,
    )
    print(f"步骤1完成：训练成功\n- 样式元数据: {meta}\n- 项目清单: {manifest}")


def cmd_step2_upload_form(args: argparse.Namespace) -> None:
    form_path, manifest = step2_upload_form(
        workspace_dir=args.workspace_dir,
        project_name=args.project,
        form_file=args.form,
        form_name=args.form_name,
    )
    print(f"步骤2完成：表格上传成功\n- 已保存: {form_path}\n- 项目清单: {manifest}")


def cmd_step3_generate(args: argparse.Namespace) -> None:
    out = step3_generate_handwrite(
        workspace_dir=args.workspace_dir,
        project_name=args.project,
        form_name=args.form_name,
        data_json_path=args.data_json,
        output_docx=args.output,
        mode=args.mode,
        height=args.height,
        char_gap=args.char_gap,
        image_width_mm=args.image_width_mm,
        seed=args.seed,
    )
    print(f"步骤3完成：已生成手写填写结果 {out}")


def cmd_render_text(args: argparse.Namespace) -> None:
    out = render_text_to_image(
        style_dir=args.style_dir,
        text=args.text,
        out_path=args.out,
        height=args.height,
        char_gap=args.char_gap,
        seed=args.seed,
    )
    print(f"渲染完成: {out}")


def cmd_fill_word_placeholder(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.data_json).read_text(encoding="utf-8"))
    out = fill_word_table_by_placeholders(
        input_docx=args.input,
        output_docx=args.output,
        style_dir=args.style_dir,
        data=data,
        render=RenderConfig(line_height=args.height, char_gap=args.char_gap),
        image_width_mm=args.image_width_mm,
        seed=args.seed,
    )
    print(f"Word 填写完成: {out}")


def _parse_cell_map(path: str) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    # 允许 key 为 "0,1,2"
    out = {}
    for k, v in raw.items():
        t, r, c = [int(x.strip()) for x in k.split(",")]
        out[(t, r, c)] = v
    return out


def cmd_fill_word_cellmap(args: argparse.Namespace) -> None:
    cell_map = _parse_cell_map(args.cell_map_json)
    out = fill_word_table_by_cell_map(
        input_docx=args.input,
        output_docx=args.output,
        style_dir=args.style_dir,
        cell_values=cell_map,
        render=RenderConfig(line_height=args.height, char_gap=args.char_gap),
        image_width_mm=args.image_width_mm,
        seed=args.seed,
    )
    print(f"Word 坐标填写完成: {out}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="手写字体学习 + Word 表格填写 工具")
    sp = p.add_subparsers(dest="command", required=True)

    # 三步操作（推荐）
    p_step1 = sp.add_parser("step1-train", help="步骤1：上传手写校本并训练")
    p_step1.add_argument("--workspace-dir", default="./projects", help="三步流程项目根目录")
    p_step1.add_argument("--project", required=True, help="项目名")
    p_step1.add_argument(
        "--samples-json",
        required=True,
        help='上传样本描述 JSON，格式: [{"image":"/path/a.png","text":"张三"}]',
    )
    p_step1.add_argument("--seed", type=int, default=42)
    p_step1.set_defaults(func=cmd_step1_train)

    p_step2 = sp.add_parser("step2-upload-form", help="步骤2：上传需要填写的表格文件")
    p_step2.add_argument("--workspace-dir", default="./projects", help="三步流程项目根目录")
    p_step2.add_argument("--project", required=True, help="项目名")
    p_step2.add_argument("--form", required=True, help="待填写表格（.docx）")
    p_step2.add_argument("--form-name", default=None, help="表格别名，不填默认用文件名")
    p_step2.set_defaults(func=cmd_step2_upload_form)

    p_step3 = sp.add_parser("step3-generate", help="步骤3：将表格文字转为手写样式并填写")
    p_step3.add_argument("--workspace-dir", default="./projects", help="三步流程项目根目录")
    p_step3.add_argument("--project", required=True, help="项目名")
    p_step3.add_argument("--form-name", required=True, help="步骤2中保存的表格别名")
    p_step3.add_argument("--data-json", required=True, help="填写内容 JSON")
    p_step3.add_argument("--output", required=True, help="输出 docx")
    p_step3.add_argument("--mode", choices=["placeholder", "cellmap"], default="placeholder")
    p_step3.add_argument("--height", type=int, default=56)
    p_step3.add_argument("--char-gap", type=int, default=8)
    p_step3.add_argument("--image-width-mm", type=float, default=40.0)
    p_step3.add_argument("--seed", type=int, default=42)
    p_step3.set_defaults(func=cmd_step3_generate)

    # 兼容旧命令
    p_build = sp.add_parser("build-style", help="从手写样本目录构建样式库（按字符子目录）")
    p_build.add_argument("--input-dir", required=True, help="输入目录，按字符子目录组织")
    p_build.add_argument("--output-dir", default="./styles", help="样式库输出根目录")
    p_build.add_argument("--style-name", required=True, help="样式名称")
    p_build.add_argument("--seed", type=int, default=42)
    p_build.set_defaults(func=cmd_build_style)

    p_build_uploaded = sp.add_parser(
        "build-style-uploaded",
        help="从上传的整张手写文字图片学习样式",
    )
    p_build_uploaded.add_argument(
        "--samples-json",
        required=True,
        help='样本描述 JSON 文件，格式: [{"image":"/path/a.png","text":"张三1990"}]',
    )
    p_build_uploaded.add_argument("--output-dir", default="./styles", help="样式库输出根目录")
    p_build_uploaded.add_argument("--style-name", required=True, help="样式名称")
    p_build_uploaded.add_argument("--seed", type=int, default=42)
    p_build_uploaded.set_defaults(func=cmd_build_style_uploaded)

    p_render = sp.add_parser("render-text", help="渲染文本为手写图片")
    p_render.add_argument("--style-dir", required=True, help="样式目录，例如 styles/zhangsan")
    p_render.add_argument("--text", required=True)
    p_render.add_argument("--out", required=True)
    p_render.add_argument("--height", type=int, default=56)
    p_render.add_argument("--char-gap", type=int, default=8)
    p_render.add_argument("--seed", type=int, default=42)
    p_render.set_defaults(func=cmd_render_text)

    p_fill_ph = sp.add_parser("fill-word-placeholder", help="按占位符填写 Word 表格")
    p_fill_ph.add_argument("--input", required=True, help="模板 docx")
    p_fill_ph.add_argument("--output", required=True, help="输出 docx")
    p_fill_ph.add_argument("--style-dir", required=True)
    p_fill_ph.add_argument("--data-json", required=True, help="字段值 JSON 文件")
    p_fill_ph.add_argument("--height", type=int, default=56)
    p_fill_ph.add_argument("--char-gap", type=int, default=8)
    p_fill_ph.add_argument("--image-width-mm", type=float, default=40.0)
    p_fill_ph.add_argument("--seed", type=int, default=42)
    p_fill_ph.set_defaults(func=cmd_fill_word_placeholder)

    p_fill_cm = sp.add_parser("fill-word-cellmap", help="按坐标填写 Word 表格")
    p_fill_cm.add_argument("--input", required=True, help="模板 docx")
    p_fill_cm.add_argument("--output", required=True, help="输出 docx")
    p_fill_cm.add_argument("--style-dir", required=True)
    p_fill_cm.add_argument("--cell-map-json", required=True, help='坐标映射 JSON，例如 {"0,1,2":"王五"}')
    p_fill_cm.add_argument("--height", type=int, default=56)
    p_fill_cm.add_argument("--char-gap", type=int, default=8)
    p_fill_cm.add_argument("--image-width-mm", type=float, default=40.0)
    p_fill_cm.add_argument("--seed", type=int, default=42)
    p_fill_cm.set_defaults(func=cmd_fill_word_cellmap)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
