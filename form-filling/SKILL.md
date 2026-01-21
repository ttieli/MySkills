---
name: form-filling
description: 自动化填写 Word/Excel 表格模板，完全保留模板格式；用于批量填表、从结构化数据写入 docx/xlsx 时触发。
---

# 自动化填表 Skill

## 触发场景
- 批量或单份填写格式固定的登记表/申请表等
- 输入数据来自字典/CSV/JSON/其他文档
- 目标文件是 Word 表格（docx）或 Excel（xlsx/xls）
- 需求强调：替换文本但不改变模板的字体、字号、边框、对齐

## 依赖
- Python 3；`python-docx`（Word），`openpyxl`（Excel）
- 可选：`pandoc` 用于将样例 docx 转成 md 便于结构查看

## 快速使用
1) 先用模板生成“样例表”验证格式：把占位内容填满（尤其长文本）后人工检查换行/段落/边距。
2) 分析表格结构：打印单元格索引，确认合并单元格位置。
3) 准备数据：整理成 `{字段名: 值}`，建立字段到单元格索引的映射。
4) 填充并保存副本；先小样本验证，再批量生成。

## Word 工作流（保留格式）
- 读取表格并建立映射：`field_mapping = {'姓名': (1,1), '部门': (0,1)}`（行、列从 0 开始）。
- 只改文本保留格式：清空所有 run 文本，仅把首个 run 设为新文本。
- 填充示例（简版）：
```python
from docx import Document
import shutil

def replace_cell_text_only(cell, text):
    first = None
    for para in cell.paragraphs:
        for run in para.runs:
            first = first or run
            run.text = ""
    if first:
        first.text = text

def fill_docx(template, output, data, mapping):
    shutil.copy(template, output)
    doc = Document(output)
    table = doc.tables[0]
    for field, (r, c) in mapping.items():
        if field in data:
            replace_cell_text_only(table.rows[r].cells[c], data[field])
    doc.save(output)
```
- 合并单元格可能重复索引，靠打印内容确认正确坐标。

## Excel 工作流
- 映射：`(行号, 列号)` 从 1 开始；合并单元格只写左上角。
- 填充示例：
```python
from openpyxl import load_workbook
import shutil

def fill_xlsx(template, output, data, mapping):
    shutil.copy(template, output)
    wb = load_workbook(output)
    ws = wb.active
    for field, (r, c) in mapping.items():
        if field in data:
            ws.cell(row=r, column=c).value = data[field]
    wb.save(output)
```
- 公式单元格避免覆盖；日期用 `datetime`；长文本可启用 `wrap_text`。

## 分析表格结构的快速脚本
- Word：遍历 `table.rows` 打印 `row_idx`, `cell_idx`, 文本前 30 字符。
- Excel：`for row_idx, row in enumerate(ws.iter_rows(...), start=1):` 打印 `(row_idx, col_idx, value)`。

## 批量处理
- 循环 `data_list`，用某个字段（如姓名）命名输出文件。
- 先处理 1–2 份做人工检查，再跑全量。

## 常见问题
- 索引错乱：合并单元格导致重复内容，务必通过打印确认坐标。
- 格式丢失：必须使用"只改文本"逻辑（首 run 赋值，其他 run 清空）。
- 内容过长：可能溢出页数或行高，需缩减内容或调整模板。

## 与 docx skill 协作

本 skill 专注于**简单文本替换**场景。以下情况应调用 **docx skill** 获取更专业的处理能力：

### 结构分析阶段
当表格结构复杂或合并单元格难以定位时：
```
调用 docx skill 的「Raw XML access」：
- 解包文档查看 word/document.xml
- 使用 pandoc --track-changes=all 获取完整结构
```

### 复杂格式编辑
当需要修改段落样式、添加批注、处理嵌套表格时：
```
调用 docx skill 的「Document Library」：
- 使用 get_node() 精确定位 XML 节点
- 直接操作 OOXML 实现复杂格式控制
```

### 跟踪修改（Redlining）
当需要保留修订痕迹供审阅时：
```
调用 docx skill 的「Redlining workflow」：
- 生成带 <w:ins>/<w:del> 标记的修订版本
- 支持批量修改的分组实现
```

### 视觉验证
当需要自动化检查填充结果时：
```
调用 docx skill 的「Converting Documents to Images」：
- soffice --headless --convert-to pdf
- pdftoppm -jpeg -r 150 转为图片
- 可用于自动对比或人工抽查
```

### 调用示例
在 form-filling 流程中遇到上述场景时，提示用户：
> "检测到复杂表格结构，建议使用 docx skill 的 XML 分析功能进行精确定位。"

## 与 xlsx skill 协作

本 skill 的 Excel 部分专注于**简单值填充**。以下情况应调用 **xlsx skill** 获取更专业的处理能力：

### 公式处理
当表格包含公式需要重新计算时：
```
调用 xlsx skill 的「recalc.py」：
- python recalc.py output.xlsx
- 自动重新计算所有公式
- 返回 JSON 格式的错误报告
```

### 数据分析
当需要对源数据进行分析、统计或可视化时：
```
调用 xlsx skill 的「pandas workflow」：
- 批量数据处理和转换
- 统计分析和数据透视
- 大文件高效读取
```

### 财务模型
当填充财务相关表格需要遵循行业标准时：
```
调用 xlsx skill 的「Financial models」规范：
- 颜色编码：蓝色=输入，黑色=公式，绿色=跨表链接
- 数字格式：货币、百分比、倍数的标准格式
- 公式规范：使用单元格引用而非硬编码值
```

### 公式验证
当填充后需要验证公式正确性时：
```
调用 xlsx skill 的「Formula Verification Checklist」：
- 检查 #REF!, #DIV/0!, #VALUE! 等错误
- 验证单元格引用和行列偏移
- 测试边界情况（零值、负数）
```

### 复杂格式
当需要精细控制单元格样式时：
```
调用 xlsx skill 的「openpyxl formatting」：
- Font, PatternFill, Alignment 样式控制
- 条件格式和数据验证
- 列宽行高调整
```

## 参考
- Word 文档高级操作见 `docx skill`。
- Excel 文档高级操作见 `xlsx skill`。
