# shouxiebiaoge（Windows 10 使用说明）

这是一个“手写样式自动填表”工具。你需要知道的最重要结论：

## 主程序是哪个？

**主程序入口：**

```bat
py -m handwrite_tool.cli launch-ui --workspace-dir .\projects
```

也就是：`handwrite_tool/cli.py` 的 `launch-ui` 命令。  
你日常只要运行这一条，就会打开 Tkinter 桌面界面。

---

## 一、Windows 10 从零开始（推荐照抄）

下面命令请在项目根目录执行（有 `README.md`、`handwrite_tool` 文件夹的目录）。

### 1) 创建虚拟环境

```bat
py -m venv .venv
```

### 2) 激活虚拟环境

- **CMD:**

```bat
.venv\Scripts\activate
```

- **PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

### 3) 安装依赖

```bat
pip install -r requirements.txt
```

### 4) 检查 Tkinter 是否可用

```bat
py -c "import tkinter as tk; print('Tk OK', tk.TkVersion)"
```

如果这里报错，请看文末“常见问题 1”。

### 5) 启动主程序（UI）

```bat
py -m handwrite_tool.cli launch-ui --workspace-dir .\projects
```

---

## 二、UI 里怎么操作（三步）

### Step 1：上传手写校本并训练

1. 点击“选择样本图片（可多选）”
2. 在右侧文本框中输入每张图片对应的文字（**每行一条，顺序一致**）
3. 点击“执行 Step 1”

### Step 2：上传需要填写的表格

1. 选择 Word 表格文件（`.docx`）
2. 可填写表格别名（不填默认用文件名）
3. 点击“执行 Step 2”

### Step 3：输入内容并生成结果

1. 选择表格
2. 选择模式：
   - `placeholder`：按 `{{字段名}}` 填写
   - `cellmap`：按坐标填写
3. 粘贴 JSON（或从 JSON 文件导入）
4. 选择输出路径
5. 点击“执行 Step 3”

界面底部还有 **“一键执行三步”** 按钮。

---

## 三、JSON 示例

### 1) placeholder 模式

```json
{
  "姓名": "张三",
  "身份证号": "110101199001011234",
  "地址": "北京市朝阳区示例路88号"
}
```

### 2) cellmap 模式

```json
{
  "0,1,1": "张三",
  "0,2,1": "1990-01-01",
  "0,3,1": "北京市朝阳区"
}
```

---

## 四、如果你不想用 UI（可选 CLI 三步）

### Step 1

```bat
py -m handwrite_tool.cli step1-train --workspace-dir .\projects --project demo_project --samples-json .\examples\upload_samples.json
```

### Step 2

```bat
py -m handwrite_tool.cli step2-upload-form --workspace-dir .\projects --project demo_project --form .\template.docx --form-name contract_form
```

### Step 3

```bat
py -m handwrite_tool.cli step3-generate --workspace-dir .\projects --project demo_project --form-name contract_form --mode placeholder --data-json .\examples\placeholder_data.json --output .\out\filled.docx
```

---

## 五、常见问题（Windows）

### 1) `No module named tkinter` 或看不到 UI

你的 Python 缺少 Tk 组件。处理方法：

1. 打开 Python 安装程序
2. 选择 **Modify**
3. 确保安装 **tcl/tk and IDLE**
4. 安装后重开终端，再运行：

```bat
py -c "import tkinter as tk; print('Tk OK', tk.TkVersion)"
```

### 2) `source 不是内部命令`

这是因为你在 Windows 用了 Linux 命令。请改用：

```bat
.venv\Scripts\activate
```

### 3) 命令里 `python3` 不可用

Windows 推荐用：

```bat
py
```

例如：

```bat
py -m handwrite_tool.cli launch-ui --workspace-dir .\projects
```

---

## 六、当前支持范围

- 表格文件：`.docx`
- 已支持上传手写样本学习，并做了分割准确率增强
- UI 已改为 Tkinter 桌面界面，流程更简洁
