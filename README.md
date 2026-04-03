# shouxiebiaoge

手写表格填写工具，支持 **Tkinter 桌面界面** 与 CLI。

核心流程（三步）：

1. 上传手写校本，训练手写样式
2. 上传需要填写的表格文件（Word `.docx`）
3. 输入表格内容文字，生成手写样式填写结果

---

## 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Linux 若运行 Tkinter 报错，请安装系统包：`python3-tk`

---

## 2. 启动 Tkinter UI（推荐）

```bash
python3 -m handwrite_tool.cli launch-ui \
  --workspace-dir ./projects
```

打开后按三步操作：

### Step 1：上传手写校本并训练

- 点击“选择样本图片（可多选）”
- 在文本框按“每行一条”填写对应文字（顺序与图片一致）
- 点击“执行 Step 1”

### Step 2：上传需要填写的表格

- 选择 `.docx` 文件
- 可填写表格别名
- 点击“执行 Step 2”

### Step 3：输入内容并生成手写填写结果

- 选择表格
- 选择模式：
  - `placeholder`（按 `{{字段名}}`）
  - `cellmap`（按坐标）
- 粘贴 JSON（或从 JSON 文件载入）
- 选择输出路径并执行 Step 3

### 一键执行

界面底部提供“一键执行三步”按钮：

- 会依次执行 Step 1 -> Step 2 -> Step 3
- 适合固定模板的高频使用

---

## 3. JSON 示例

### placeholder 模式

```json
{
  "姓名": "张三",
  "身份证号": "110101199001011234",
  "地址": "北京市朝阳区示例路88号"
}
```

### cellmap 模式

```json
{
  "0,1,1": "张三",
  "0,2,1": "1990-01-01",
  "0,3,1": "北京市朝阳区"
}
```

---

## 4. CLI 三步命令（可选）

### Step 1 训练

```bash
python3 -m handwrite_tool.cli step1-train \
  --workspace-dir ./projects \
  --project demo_project \
  --samples-json ./examples/upload_samples.json
```

### Step 2 上传表格

```bash
python3 -m handwrite_tool.cli step2-upload-form \
  --workspace-dir ./projects \
  --project demo_project \
  --form ./template.docx \
  --form-name contract_form
```

### Step 3 生成结果

```bash
python3 -m handwrite_tool.cli step3-generate \
  --workspace-dir ./projects \
  --project demo_project \
  --form-name contract_form \
  --mode placeholder \
  --data-json ./examples/placeholder_data.json \
  --output ./out/filled.docx
```

---

## 5. 备注

- 当前表格格式支持 `.docx`
- 上传学习已做准确率增强（自适应阈值、连通域、噪点过滤、粘连切分/过分割合并）
- 保留旧命令兼容历史脚本
