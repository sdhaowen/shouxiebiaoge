from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from .workflow import step1_train_uploaded, step2_upload_form, step3_generate_handwrite

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except Exception as exc:  # pragma: no cover - runtime environment dependent
    raise RuntimeError("Tkinter 不可用，请安装 python3-tk 后再运行 UI。") from exc


class HandwriteTkApp:
    def __init__(self, default_workspace: str = "./projects") -> None:
        self.root = tk.Tk()
        self.root.title("手写表格填写工具（Tkinter）")
        self.root.geometry("980x760")

        self.workspace_var = tk.StringVar(value=default_workspace)
        self.project_var = tk.StringVar(value="demo_project")

        self.step1_images: List[str] = []
        self.form_path_var = tk.StringVar(value="")
        self.form_name_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="placeholder")
        self.output_var = tk.StringVar(value="")

        self.step1_seed_var = tk.IntVar(value=42)
        self.step3_seed_var = tk.IntVar(value=42)
        self.height_var = tk.IntVar(value=56)
        self.char_gap_var = tk.IntVar(value=8)
        self.image_width_var = tk.DoubleVar(value=40.0)

        self._build_ui()

    def _build_ui(self) -> None:
        root = self.root

        top = ttk.LabelFrame(root, text="项目设置")
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="项目根目录:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(top, textvariable=self.workspace_var, width=55).grid(row=0, column=1, sticky="we", padx=6, pady=6)

        ttk.Label(top, text="项目名:").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(top, textvariable=self.project_var, width=24).grid(row=0, column=3, sticky="we", padx=6, pady=6)

        ttk.Button(top, text="刷新表格列表", command=self._refresh_forms).grid(row=0, column=4, padx=6, pady=6)
        top.columnconfigure(1, weight=1)

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, padx=10, pady=4)

        self._build_step1(body)
        self._build_step2(body)
        self._build_step3(body)

        action_bar = ttk.Frame(root)
        action_bar.pack(fill="x", padx=10, pady=6)
        ttk.Button(action_bar, text="一键执行三步", command=self._run_all_steps).pack(side="left")
        ttk.Label(action_bar, text="（需要先选择样本图、表格和填写 JSON）").pack(side="left", padx=8)

        log_box = ttk.LabelFrame(root, text="运行日志")
        log_box.pack(fill="both", expand=True, padx=10, pady=8)
        self.log_text = scrolledtext.ScrolledText(log_box, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_step1(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Step 1：上传手写校本并训练")
        box.pack(fill="x", pady=6)

        ttk.Button(box, text="选择样本图片（可多选）", command=self._pick_step1_images).grid(
            row=0, column=0, padx=6, pady=6, sticky="w"
        )
        self.step1_count_label = ttk.Label(box, text="已选 0 张")
        self.step1_count_label.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(box, text="每张图对应文字（每行一条，顺序一致）:").grid(
            row=1, column=0, columnspan=2, padx=6, pady=(4, 2), sticky="w"
        )
        self.step1_text = scrolledtext.ScrolledText(box, height=5, wrap="word")
        self.step1_text.grid(row=2, column=0, columnspan=4, padx=6, pady=4, sticky="we")

        ttk.Label(box, text="随机种子:").grid(row=3, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.step1_seed_var, width=10).grid(row=3, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(box, text="执行 Step 1", command=self._run_step1).grid(row=3, column=2, padx=6, pady=6, sticky="e")

        box.columnconfigure(3, weight=1)

    def _build_step2(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Step 2：上传需要填写的表格（.docx）")
        box.pack(fill="x", pady=6)

        ttk.Label(box, text="表格文件:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.form_path_var, width=70).grid(row=0, column=1, padx=6, pady=6, sticky="we")
        ttk.Button(box, text="选择文件", command=self._pick_form_file).grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(box, text="表格别名(可选):").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.form_name_var, width=28).grid(row=1, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(box, text="执行 Step 2", command=self._run_step2).grid(row=1, column=2, padx=6, pady=6)

        box.columnconfigure(1, weight=1)

    def _build_step3(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="Step 3：输入内容并生成手写填写结果")
        box.pack(fill="both", expand=True, pady=6)

        ttk.Label(box, text="选择表格:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.forms_combo = ttk.Combobox(box, state="readonly", width=24)
        self.forms_combo.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(box, text="模式:").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Radiobutton(box, text="占位符", variable=self.mode_var, value="placeholder").grid(
            row=0, column=3, padx=4, pady=6, sticky="w"
        )
        ttk.Radiobutton(box, text="坐标", variable=self.mode_var, value="cellmap").grid(
            row=0, column=4, padx=4, pady=6, sticky="w"
        )

        ttk.Label(box, text="填写 JSON:").grid(row=1, column=0, padx=6, pady=(6, 2), sticky="nw")
        self.step3_json_text = scrolledtext.ScrolledText(box, height=8, wrap="word")
        self.step3_json_text.grid(row=1, column=1, columnspan=4, padx=6, pady=(6, 2), sticky="nsew")

        ttk.Button(box, text="从 JSON 文件载入", command=self._load_json_to_text).grid(
            row=2, column=1, padx=6, pady=4, sticky="w"
        )

        ttk.Label(box, text="输出文件:").grid(row=3, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.output_var, width=70).grid(row=3, column=1, columnspan=3, padx=6, pady=6, sticky="we")
        ttk.Button(box, text="选择保存位置", command=self._pick_output_file).grid(row=3, column=4, padx=6, pady=6)

        ttk.Label(box, text="字高:").grid(row=4, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.height_var, width=8).grid(row=4, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(box, text="字间距:").grid(row=4, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.char_gap_var, width=8).grid(row=4, column=3, padx=6, pady=6, sticky="w")
        ttk.Label(box, text="图片宽(mm):").grid(row=4, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.image_width_var, width=8).grid(row=4, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(box, text="随机种子:").grid(row=5, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(box, textvariable=self.step3_seed_var, width=8).grid(row=5, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(box, text="执行 Step 3", command=self._run_step3).grid(row=5, column=5, padx=6, pady=6, sticky="e")

        box.columnconfigure(1, weight=1)
        box.rowconfigure(1, weight=1)

    def _project_context(self) -> tuple[str, str]:
        workspace = self.workspace_var.get().strip()
        project = self.project_var.get().strip()
        if not workspace:
            raise ValueError("项目根目录不能为空")
        if not project:
            raise ValueError("项目名不能为空")
        return workspace, project

    def _write_log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {message}\n")
        self.log_text.see("end")

    def _show_error(self, err: Exception | str) -> None:
        msg = str(err)
        self._write_log(f"错误: {msg}")
        messagebox.showerror("错误", msg)

    def _pick_step1_images(self) -> None:
        files = filedialog.askopenfilenames(
            title="选择手写样本图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if files:
            self.step1_images = list(files)
            self.step1_count_label.config(text=f"已选 {len(self.step1_images)} 张")
            self._write_log(f"已选择样本图片 {len(self.step1_images)} 张")

    def _pick_form_file(self) -> None:
        f = filedialog.askopenfilename(
            title="选择 Word 表格",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")],
        )
        if f:
            self.form_path_var.set(f)

    def _pick_output_file(self) -> None:
        f = filedialog.asksaveasfilename(
            title="选择输出文件",
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx")],
            initialfile="filled_result.docx",
        )
        if f:
            self.output_var.set(f)

    def _load_json_to_text(self) -> None:
        f = filedialog.askopenfilename(
            title="选择 JSON 文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not f:
            return
        content = Path(f).read_text(encoding="utf-8")
        self.step3_json_text.delete("1.0", "end")
        self.step3_json_text.insert("1.0", content)
        self._write_log(f"已载入 JSON: {f}")

    def _refresh_forms(self) -> None:
        try:
            workspace, project = self._project_context()
            manifest = Path(workspace) / project / "project.json"
            if not manifest.exists():
                self.forms_combo["values"] = []
                self.forms_combo.set("")
                return
            data = json.loads(manifest.read_text(encoding="utf-8"))
            forms = sorted((data.get("forms") or {}).keys())
            self.forms_combo["values"] = forms
            if forms:
                self.forms_combo.set(forms[0])
            self._write_log(f"已刷新表格列表，共 {len(forms)} 个")
        except Exception as exc:
            self._show_error(exc)

    def _build_samples_json(self, workspace: str, project: str) -> Path:
        if not self.step1_images:
            raise ValueError("请先选择至少一张样本图片")

        lines = [line.strip() for line in self.step1_text.get("1.0", "end").splitlines() if line.strip()]
        if len(lines) != len(self.step1_images):
            raise ValueError(f"文本行数({len(lines)})需与样本图片数量({len(self.step1_images)})一致")

        items = [{"image": p, "text": t} for p, t in zip(self.step1_images, lines)]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = Path(workspace) / project / "uploads" / f"ui_samples_{ts}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def _run_step1(self) -> None:
        try:
            workspace, project = self._project_context()
            samples_json = self._build_samples_json(workspace, project)
            meta_path, manifest = step1_train_uploaded(
                workspace_dir=workspace,
                project_name=project,
                samples_json_path=samples_json,
                seed=int(self.step1_seed_var.get()),
            )
            self._write_log(f"Step1 完成: {meta_path}")
            self._write_log(f"项目清单: {manifest}")
            self._refresh_forms()
            messagebox.showinfo("完成", "Step 1 训练完成")
        except Exception as exc:
            self._show_error(exc)

    def _run_step2(self) -> None:
        try:
            workspace, project = self._project_context()
            form_path = self.form_path_var.get().strip()
            if not form_path:
                raise ValueError("请先选择一个 .docx 表格文件")

            saved, manifest = step2_upload_form(
                workspace_dir=workspace,
                project_name=project,
                form_file=form_path,
                form_name=self.form_name_var.get().strip() or None,
            )
            self._write_log(f"Step2 完成: {saved}")
            self._write_log(f"项目清单: {manifest}")
            self._refresh_forms()
            messagebox.showinfo("完成", "Step 2 表格上传完成")
        except Exception as exc:
            self._show_error(exc)

    def _build_payload_json(self, workspace: str, project: str) -> Path:
        raw = self.step3_json_text.get("1.0", "end").strip()
        if not raw:
            raise ValueError("请先输入填写 JSON")
        payload = json.loads(raw)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = Path(workspace) / project / "inputs" / f"ui_payload_{ts}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def _run_step3(self) -> None:
        try:
            workspace, project = self._project_context()
            form_name = self.forms_combo.get().strip()
            if not form_name:
                raise ValueError("请先选择一个表格")

            payload_path = self._build_payload_json(workspace, project)

            output = self.output_var.get().strip()
            if not output:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                output = str(Path(workspace) / project / "outputs" / f"filled_{ts}.docx")

            result = step3_generate_handwrite(
                workspace_dir=workspace,
                project_name=project,
                form_name=form_name,
                data_json_path=payload_path,
                output_docx=output,
                mode=self.mode_var.get(),
                height=int(self.height_var.get()),
                char_gap=int(self.char_gap_var.get()),
                image_width_mm=float(self.image_width_var.get()),
                seed=int(self.step3_seed_var.get()),
            )

            self.output_var.set(str(result))
            self._write_log(f"Step3 完成: {result}")
            messagebox.showinfo("完成", f"Step 3 生成完成\n{result}")
        except Exception as exc:
            self._show_error(exc)

    def _run_all_steps(self) -> None:
        try:
            self._run_step1()
            self._run_step2()
            self._run_step3()
        except Exception:
            # 每个步骤内部已展示错误，这里不重复抛出
            return

    def run(self) -> None:
        self._refresh_forms()
        self.root.mainloop()


def launch_ui(default_workspace: str = "./projects", **_: object) -> None:
    """
    启动 Tkinter UI。
    通过 **_ 接受旧参数，保持 CLI 兼容（host/port/share 会被忽略）。
    """
    app = HandwriteTkApp(default_workspace=default_workspace)
    app.run()
