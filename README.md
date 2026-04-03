# shouxiebiaoge

手写表格填写工具，按你要求的**三步操作**：

1. 上传手写校本，训练手写样式
2. 上传需要填写的表格文件（Word `.docx`）
3. 输入符合表格内容的文字，自动生成手写样式填写结果

---

## 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. 三步操作（推荐）

> 下面示例项目名用 `demo_project`。

### Step 1：上传手写校本并训练

准备上传样本描述 JSON（示例：`examples/upload_samples.json`）：

```json
[
  {
    "image": "./uploads/page1.png",
    "text": "张三1990-01-01"
  },
  {
    "image": "./uploads/page2.png",
    "text": "北京市朝阳区"
  }
]
```

执行训练：

```bash
python3 -m handwrite_tool.cli step1-train \
  --workspace-dir ./projects \
  --project demo_project \
  --samples-json ./examples/upload_samples.json
```

执行后会在 `./projects/demo_project/` 下保存：

- 训练后的样式库
- 项目清单 `project.json`

---

### Step 2：上传需要填写的表格文件

```bash
python3 -m handwrite_tool.cli step2-upload-form \
  --workspace-dir ./projects \
  --project demo_project \
  --form ./template.docx \
  --form-name contract_form
```

说明：

- `--form-name` 是你给表格取的别名，后续 Step 3 用这个名字选表格。

---

### Step 3：把表格内容文字转成手写样式并填写

#### 方式 A：占位符模式（推荐）

Word 表格单元格中写占位符：`{{姓名}}`、`{{地址}}` 等。

准备 JSON（示例：`examples/placeholder_data.json`）：

```json
{
  "姓名": "张三",
  "身份证号": "110101199001011234",
  "地址": "北京市朝阳区示例路88号"
}
```

执行：

```bash
python3 -m handwrite_tool.cli step3-generate \
  --workspace-dir ./projects \
  --project demo_project \
  --form-name contract_form \
  --mode placeholder \
  --data-json ./examples/placeholder_data.json \
  --output ./out/filled.docx
```

#### 方式 B：坐标模式

JSON（示例：`examples/cell_map_data.json`）：

```json
{
  "0,1,1": "张三",
  "0,2,1": "1990-01-01",
  "0,3,1": "北京市朝阳区"
}
```

执行：

```bash
python3 -m handwrite_tool.cli step3-generate \
  --workspace-dir ./projects \
  --project demo_project \
  --form-name contract_form \
  --mode cellmap \
  --data-json ./examples/cell_map_data.json \
  --output ./out/filled_cellmap.docx
```

---

## 3. 参数说明

- `--height`：手写字高度（像素）
- `--char-gap`：字符间距
- `--image-width-mm`：插入 Word 单元格图片宽度（毫米）
- `--seed`：随机种子

示例（Step 3 调整效果）：

```bash
python3 -m handwrite_tool.cli step3-generate \
  --workspace-dir ./projects \
  --project demo_project \
  --form-name contract_form \
  --mode placeholder \
  --data-json ./examples/placeholder_data.json \
  --output ./out/filled_tuned.docx \
  --height 62 \
  --char-gap 10 \
  --image-width-mm 45
```

---

## 4. 兼容命令

仍保留旧命令（`build-style-uploaded` / `fill-word-placeholder` / `fill-word-cellmap`），
但建议优先使用上面的三步操作，更贴合实际业务流程。
