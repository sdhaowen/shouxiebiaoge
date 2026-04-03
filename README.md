# shouxiebiaoge

手写表格填写工具，支持 **UI 操作界面** 与 CLI。

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

---

## 2. 启动 UI 操作界面（推荐）

```bash
python3 -m handwrite_tool.cli launch-ui \
  --host 0.0.0.0 \
  --port 7860 \
  --workspace-dir ./projects
```

浏览器打开提示地址（通常是 `http://127.0.0.1:7860`）。

### UI 中的三步操作

#### Step 1：上传手写校本并训练

- 上传多张手写样本图片
- 在右侧文本框按“每行一条”填写对应文字（顺序与图片一致）
- 点击「执行 Step 1 训练」

#### Step 2：上传表格文件

- 上传 `.docx` 表格文件
- 可选填写表格别名（比如 `contract_form`）
- 点击「执行 Step 2 上传表格」

#### Step 3：生成手写填写结果

- 选择 Step 2 上传的表格
- 选择模式：
  - `placeholder`：按 `{{字段名}}` 占位符填充
  - `cellmap`：按坐标 `"0,1,1"` 填充
- 粘贴 JSON 或上传 JSON 文件
- 点击「执行 Step 3 生成」，下载输出 `.docx`

---

## 3. JSON 示例

### 占位符模式（placeholder）

```json
{
  "姓名": "张三",
  "身份证号": "110101199001011234",
  "地址": "北京市朝阳区示例路88号"
}
```

### 坐标模式（cellmap）

```json
{
  "0,1,1": "张三",
  "0,2,1": "1990-01-01",
  "0,3,1": "北京市朝阳区"
}
```

---

## 4. CLI 三步命令（可选）

如果你不使用 UI，也可用 CLI：

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
- 已增强上传学习的切分准确率（阈值自适应、连通域、噪点过滤、粘连切分/过分割合并）
- 保留旧命令兼容历史脚本
