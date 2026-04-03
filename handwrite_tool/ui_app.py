from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

import gradio as gr

from .workflow import step1_train_uploaded, step2_upload_form, step3_generate_handwrite


def _manifest_path(workspace_dir: str, project: str) -> Path:
    return Path(workspace_dir) / project / "project.json"


def _load_forms(workspace_dir: str, project: str) -> List[str]:
    manifest = _manifest_path(workspace_dir, project)
    if not manifest.exists():
        return []
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return sorted((data.get("forms") or {}).keys())


def _step1_train(workspace_dir: str, project: str, image_files, text_lines: str, seed: int):
    if not image_files:
        return "请先上传至少一张手写样本图片。"

    lines = [line.strip() for line in (text_lines or "").splitlines() if line.strip()]
    if len(lines) != len(image_files):
        return f"文本行数({len(lines)})需与图片数量({len(image_files)})一致。"

    samples = []
    for f, text in zip(image_files, lines):
        path = f if isinstance(f, str) else getattr(f, "name", None)
        if not path:
            return "检测到无效图片文件，请重新上传。"
        samples.append({"image": str(path), "text": text})

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_json = Path(workspace_dir) / project / "uploads" / f"ui_samples_{ts}.json"
    temp_json.parent.mkdir(parents=True, exist_ok=True)
    temp_json.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")

    meta_path, manifest = step1_train_uploaded(
        workspace_dir=workspace_dir,
        project_name=project,
        samples_json_path=temp_json,
        seed=int(seed),
    )
    return f"训练完成\n样式: {meta_path}\n项目清单: {manifest}"


def _step2_upload_form(workspace_dir: str, project: str, form_file, form_name: str):
    if not form_file:
        return "请上传一个 Word 表格文件（.docx）。", gr.update(choices=[])

    form_path = form_file if isinstance(form_file, str) else getattr(form_file, "name", None)
    if not form_path:
        return "上传文件无效，请重试。", gr.update(choices=[])

    saved, _manifest = step2_upload_form(
        workspace_dir=workspace_dir,
        project_name=project,
        form_file=form_path,
        form_name=form_name.strip() if form_name else None,
    )

    forms = _load_forms(workspace_dir, project)
    return f"表格上传成功: {saved}", gr.update(choices=forms, value=forms[0] if forms else None)


def _step3_generate(
    workspace_dir: str,
    project: str,
    form_name: str,
    mode: str,
    data_json_text: str,
    data_json_file,
    output_name: str,
    height: int,
    char_gap: int,
    image_width_mm: float,
    seed: int,
):
    if not form_name:
        return "请先在步骤2上传表格并选择表格名称。", None

    payload_text = (data_json_text or "").strip()
    if data_json_file is not None:
        data_file_path = data_json_file if isinstance(data_json_file, str) else getattr(data_json_file, "name", None)
        if not data_file_path:
            return "上传的 JSON 文件无效。", None
        payload = json.loads(Path(data_file_path).read_text(encoding="utf-8"))
    else:
        if not payload_text:
            return "请填写 JSON 内容，或上传 JSON 文件。", None
        payload = json.loads(payload_text)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = output_name.strip() if (output_name or "").strip() else f"filled_{ts}.docx"
    if not output_base.endswith(".docx"):
        output_base += ".docx"

    payload_file = Path(workspace_dir) / project / "inputs" / f"ui_payload_{ts}.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    out_path = Path(workspace_dir) / project / "outputs" / output_base
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = step3_generate_handwrite(
        workspace_dir=workspace_dir,
        project_name=project,
        form_name=form_name,
        data_json_path=payload_file,
        output_docx=out_path,
        mode=mode,
        height=int(height),
        char_gap=int(char_gap),
        image_width_mm=float(image_width_mm),
        seed=int(seed),
    )

    return f"生成成功: {result}", str(result)


def _refresh_forms(workspace_dir: str, project: str):
    forms = _load_forms(workspace_dir, project)
    return gr.update(choices=forms, value=forms[0] if forms else None)


def launch_ui(host: str = "0.0.0.0", port: int = 7860, share: bool = False, default_workspace: str = "./projects") -> None:
    with gr.Blocks(title="手写表格填写 - 三步操作") as demo:
        gr.Markdown("""
# 手写表格填写工具（UI）
按三步操作：
1. 上传手写校本并训练
2. 上传要填写的表格文件（docx）
3. 输入填写内容，生成手写样式结果
""")

        with gr.Row():
            workspace_dir = gr.Textbox(label="项目根目录", value=default_workspace)
            project_name = gr.Textbox(label="项目名", value="demo_project")

        gr.Markdown("## Step 1：上传手写校本并训练")
        with gr.Row():
            step1_files = gr.File(
                label="上传手写样本图片（可多张）",
                file_count="multiple",
                file_types=["image"],
                type="filepath",
            )
            step1_text_lines = gr.Textbox(
                label="每张图对应的文字（每行一条，顺序与图片一致）",
                lines=8,
                placeholder="第1张对应文字\n第2张对应文字",
            )
        with gr.Row():
            step1_seed = gr.Number(label="随机种子", value=42, precision=0)
            step1_btn = gr.Button("执行 Step 1 训练", variant="primary")
        step1_status = gr.Textbox(label="Step 1 状态", lines=4)

        gr.Markdown("## Step 2：上传表格文件")
        with gr.Row():
            step2_form_file = gr.File(label="上传 Word 表格（.docx）", file_types=[".docx"], type="filepath")
            step2_form_name = gr.Textbox(label="表格别名（可选）", placeholder="例如：contract_form")
        with gr.Row():
            step2_btn = gr.Button("执行 Step 2 上传表格", variant="primary")
            refresh_btn = gr.Button("刷新表格列表")
        step2_status = gr.Textbox(label="Step 2 状态", lines=3)

        gr.Markdown("## Step 3：输入内容并生成手写填写结果")
        with gr.Row():
            step3_form_name = gr.Dropdown(label="选择表格", choices=[])
            step3_mode = gr.Radio(label="填写模式", choices=["placeholder", "cellmap"], value="placeholder")

        with gr.Row():
            step3_data_json_text = gr.Textbox(
                label="填写内容 JSON（可直接粘贴）",
                lines=10,
                placeholder='placeholder 示例: {"姓名":"张三"}\ncellmap 示例: {"0,1,1":"张三"}',
            )
            step3_data_json_file = gr.File(label="或上传 JSON 文件", file_types=[".json"], type="filepath")

        with gr.Row():
            step3_output_name = gr.Textbox(label="输出文件名（可选）", value="filled_result.docx")
            step3_height = gr.Number(label="字高(px)", value=56, precision=0)
            step3_char_gap = gr.Number(label="字间距", value=8, precision=0)
            step3_width = gr.Number(label="图片宽(mm)", value=40.0)
            step3_seed = gr.Number(label="随机种子", value=42, precision=0)

        step3_btn = gr.Button("执行 Step 3 生成", variant="primary")
        step3_status = gr.Textbox(label="Step 3 状态", lines=3)
        step3_download = gr.File(label="下载结果文件")

        step1_btn.click(
            _step1_train,
            inputs=[workspace_dir, project_name, step1_files, step1_text_lines, step1_seed],
            outputs=[step1_status],
        )

        step2_btn.click(
            _step2_upload_form,
            inputs=[workspace_dir, project_name, step2_form_file, step2_form_name],
            outputs=[step2_status, step3_form_name],
        )

        refresh_btn.click(
            _refresh_forms,
            inputs=[workspace_dir, project_name],
            outputs=[step3_form_name],
        )

        step3_btn.click(
            _step3_generate,
            inputs=[
                workspace_dir,
                project_name,
                step3_form_name,
                step3_mode,
                step3_data_json_text,
                step3_data_json_file,
                step3_output_name,
                step3_height,
                step3_char_gap,
                step3_width,
                step3_seed,
            ],
            outputs=[step3_status, step3_download],
        )

    demo.launch(server_name=host, server_port=port, share=share)
