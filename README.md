# shouxiebiaoge

一个可落地的工具原型：

1. 学习人类手写字体样式（支持**上传整张手写文字图片进行学习**）
2. 构建手写样式库
3. 使用该样式自动填写 Word 表格（`.docx`）

支持两种 Word 填写方式：

- **占位符模式**：单元格内容写成 `{{字段名}}`
- **坐标模式**：按 `(table,row,col)` 指定要填写的单元格

---

## 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. 学习手写字体（推荐：上传整张文字图片）

### 2.1 准备上传样本描述 JSON

你上传的每一张手写文字图片，都需要给一段对应文字（机器据此知道每个字是什么）。

示例 `examples/upload_samples.json`：

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

说明：

- `image`：上传图片路径（支持 png/jpg/jpeg/webp/bmp）
- `text`：该图片里写的内容（建议一行文字一张图，字符不要粘连太紧）

### 2.2 执行学习

```bash
python3 -m handwrite_tool.cli build-style-uploaded \
  --samples-json ./examples/upload_samples.json \
  --output-dir ./styles \
  --style-name zhangsan
```

生成结果：

```text
styles/
  zhangsan/
    meta.json
    glyphs/
      U+5F20/
      U+4E09/
      ...
```

---

## 3. （兼容）按字符目录学习

如果你已经有按字符切好的单字图片，也可继续使用：

```bash
python3 -m handwrite_tool.cli build-style \
  --input-dir ./samples \
  --output-dir ./styles \
  --style-name zhangsan
```

目录格式：

```text
samples/
  张/
    1.png
    2.png
  三/
    1.png
  A/
    1.jpg
  1/
    1.png
  space/
    1.png   # 可选，表示空格
```

---

## 4. 先渲染一张手写文本图片（可选测试）

```bash
python3 -m handwrite_tool.cli render-text \
  --style-dir ./styles/zhangsan \
  --text "张三 1990-01-01" \
  --out ./out/demo.png
```

---

## 5. 填写 Word 表格

> 注意：目前支持 `.docx`（Office Open XML）格式。

### 5.1 占位符模式

在 Word 表格单元格里写占位符（单元格内容仅写占位符），例如：

- `{{姓名}}`
- `{{身份证号}}`
- `{{地址}}`

准备数据文件 `examples/placeholder_data.json`：

```json
{
  "姓名": "张三",
  "身份证号": "110101199001011234",
  "地址": "北京市朝阳区示例路88号"
}
```

执行：

```bash
python3 -m handwrite_tool.cli fill-word-placeholder \
  --input ./template.docx \
  --output ./out/filled_placeholder.docx \
  --style-dir ./styles/zhangsan \
  --data-json ./examples/placeholder_data.json
```

### 5.2 坐标模式

准备坐标映射文件 `examples/cell_map_data.json`：

```json
{
  "0,1,1": "张三",
  "0,2,1": "1990-01-01",
  "0,3,1": "北京市朝阳区"
}
```

说明：`"0,1,1"` 表示第 0 个表格、第 1 行、第 1 列。

执行：

```bash
python3 -m handwrite_tool.cli fill-word-cellmap \
  --input ./template.docx \
  --output ./out/filled_cellmap.docx \
  --style-dir ./styles/zhangsan \
  --cell-map-json ./examples/cell_map_data.json
```

---

## 6. 参数说明

通用可调参数：

- `--height`：手写字高度（像素）
- `--char-gap`：字符间距
- `--image-width-mm`：插入 Word 单元格图片宽度（毫米）
- `--seed`：随机种子（可复现实验）

---

## 7. 当前能力与后续可扩展

当前原型已实现：

- 上传手写文字图片学习样式（自动切分字形）
- 按样式渲染文本
- 自动填 Word 表格

可继续扩展：

- 更强的字符分割（粘连字、复杂背景）
- 支持句子级连笔、笔画粗细扰动
- 更智能的单元格适配（自动换行、缩放）
- 支持 Excel 表格填写
