"""
统一文档读取层。
支持 MD/PDF/DOCX/HTML/TXT 格式，按需加载依赖。
"""
from __future__ import annotations

import re
from pathlib import Path


class UnsupportedFormatError(Exception):
    """文档格式不支持时抛出，携带安装提示。"""
    def __init__(self, format: str, hint: str = ""):
        self.format = format
        self.hint = hint or f"不支持的格式: .{format}"
        super().__init__(self.hint)


def read_document(filepath: str | Path) -> str:
    """
    自动检测格式，返回纯文本内容。
    抛出 UnsupportedFormatError 时，hint 携带 pip install 命令。
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    suffix = filepath.suffix.lower()

    if suffix in (".md", ".markdown", ".txt"):
        return _read_text(filepath)
    elif suffix in (".html", ".htm"):
        return _read_html(filepath)
    elif suffix == ".pdf":
        return _read_pdf(filepath)
    elif suffix == ".docx":
        return _read_docx(filepath)
    else:
        raise UnsupportedFormatError(
            suffix,
            f"不支持的文档格式: {suffix}\n支持的格式: .md / .txt / .html / .pdf / .docx",
        )


def list_supported_formats() -> dict[str, bool]:
    """返回 {格式: 是否可用}。"""
    formats = {
        "md": True,
        "txt": True,
        "html": True,
    }
    formats["pdf"] = _check_pdf_available()
    formats["docx"] = _check_docx_available()
    return formats


def check_dependency(format: str) -> bool:
    """检查特定格式的依赖是否已安装。"""
    checks = {
        "pdf": _check_pdf_available,
        "docx": _check_docx_available,
        "md": lambda: True,
        "txt": lambda: True,
        "html": lambda: True,
    }
    checker = checks.get(format, lambda: False)
    return checker()


# ── 内部实现 ──────────────────────────────────────────

def _read_text(filepath: Path) -> str:
    """读取纯文本文件，自动检测编码。"""
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return filepath.read_text(encoding="gbk")


def _read_html(filepath: Path) -> str:
    """从 HTML 文件中提取纯文本（去除标签）。"""
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
            self.skip_depth = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "noscript", "head"):
                self.skip_depth += 1

        def handle_endtag(self, tag):
            if tag in ("script", "style", "noscript", "head"):
                if self.skip_depth > 0:
                    self.skip_depth -= 1

        def handle_data(self, data):
            if self.skip_depth > 0:
                return
            text = data.strip()
            if text:
                self.parts.append(text)

    text = _read_text(filepath)
    extractor = TextExtractor()
    extractor.feed(text)
    return "\n".join(extractor.parts)


def _read_pdf(filepath: Path) -> str:
    """从 PDF 文件中提取文本。需要 PyPDF2。"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise UnsupportedFormatError(
            "pdf",
            "读取 PDF 需要 PyPDF2。请运行: pip install PyPDF2",
        )

    reader = PdfReader(str(filepath))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _read_docx(filepath: Path) -> str:
    """从 DOCX 文件中提取文本。需要 python-docx。"""
    try:
        from docx import Document
    except ImportError:
        raise UnsupportedFormatError(
            "docx",
            "读取 DOCX 需要 python-docx。请运行: pip install python-docx",
        )

    doc = Document(str(filepath))
    paragraphs: list[str] = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())
    return "\n".join(paragraphs)


# ── 文档结构检测与智能分块 ─────────────────────────

# 常见章节标记模式（中文 + 英文）
_SECTION_PATTERNS = [
    # Markdown 标题（H1-H6）
    re.compile(r"^#{1,6}\s+(.+)", re.MULTILINE),
    # 数字编号：1. / 1、/ 一、/ (1)
    re.compile(r"^(?:第[一二三四五六七八九十百千]+[章节]|（[一二三四五六七八九十百千]+）|[一二三四五六七八九十百千]+[、．.])", re.MULTILINE),
    re.compile(r"^(\d+)[、．.)]\s*(.+)", re.MULTILINE),
    # 英文编号：Chapter / Section / Part
    re.compile(r"^(?:Chapter|Section|Part|CHAPTER|SECTION|PART)\s+\d+", re.MULTILINE),
    # 全大写标题行（通常表示章节）
    re.compile(r"^[A-Z][A-Z\s\-]{5,}$", re.MULTILINE),
]

# 最小有意义块大小（字符数），小于此值尝试与相邻块合并
_MIN_CHUNK_SIZE = 200
# 默认最大块大小（字符数），超过此值尝试进一步拆分
_DEFAULT_MAX_CHUNK = 4000


def detect_structure(text: str) -> dict:
    """
    检测文档结构类型。
    返回 {"type": "hierarchical"|"flat"|"semi_structured", "sections": [...]}

    - hierarchical: 有 MD 标题层级 (H1/H2/H3)
    - semi_structured: 有编号/关键词等可识别分段
    - flat: 纯文本段落，无边界的结构标记
    """
    # 检测 MD 标题
    heading_re = re.compile(r"^#{1,6}\s+", re.MULTILINE)
    headings = heading_re.findall(text)
    if len(headings) >= 2:
        return {"type": "hierarchical", "section_count": len(headings)}

    # 检测编号分段
    num_re = re.compile(r"^\d+[、．.)]\s", re.MULTILINE)
    nums = num_re.findall(text)
    if len(nums) >= 3:
        return {"type": "semi_structured", "section_count": len(nums)}

    # 检测中文章节标记
    cn_re = re.compile(r"(?:第[一二三四五六七八九十百千]+[章节]|[一二三四五六七八九十百千]+[、．])", re.MULTILINE)
    cn_sections = cn_re.findall(text)
    if len(cn_sections) >= 2:
        return {"type": "semi_structured", "section_count": len(cn_sections)}

    # 按空行段落数判断
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 5:
        return {"type": "flat", "paragraph_count": len(paragraphs)}

    return {"type": "flat", "paragraph_count": len(paragraphs)}


def chunk_document(text: str, max_chars: int = _DEFAULT_MAX_CHUNK, source_filename: str = "") -> list[dict]:
    """
    将文本按语义边界分块，每块不超过 max_chars。
    返回列表，每项: {"label": "第N部分/章节标题", "content": "...", "char_count": N}

    分块策略（按优先级）：
    1. 如果有 MD 标题 → 按 H2/H3 切分
    2. 如果有编号 → 按编号切分
    3. 如果是长文本（> max_chars）→ 按段落组切分
    4. 短文本 → 单块
    """
    structure = detect_structure(text)

    if structure["type"] == "hierarchical":
        chunks = _chunk_by_headings(text, max_chars)
    elif structure["type"] == "semi_structured":
        chunks = _chunk_by_numbered_sections(text, max_chars)
    elif len(text) > max_chars:
        chunks = _chunk_by_paragraphs(text, max_chars)
    else:
        label = "全文" if source_filename else "正文"
        return [{"label": label, "content": text.strip(), "char_count": len(text)}]

    # 合并过小的尾部块
    chunks = _merge_small_chunks(chunks)

    return chunks


def _chunk_by_headings(text: str, max_chars: int) -> list[dict]:
    """按 H2/H3 标题切分。"""
    lines = text.split("\n")
    chunks: list[dict] = []
    current_label = ""
    current_lines: list[str] = []
    fence_depth = 0

    for line in lines:
        # 追踪代码块
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            fence_depth = 1 - fence_depth

        # H2 或 H3（不在代码块内）
        m = re.match(r"^(#{2,3})\s+(.+)", line)
        if m and fence_depth == 0:
            # 保存之前的块
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append({
                        "label": current_label or "开头",
                        "content": content,
                        "char_count": len(content),
                    })
            current_label = m.group(2).strip()
            current_lines = []
        elif m and m.group(1) == "#" and fence_depth == 0:
            # H1（文档标题）→ 跳过
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append({
                        "label": current_label or "开头",
                        "content": content,
                        "char_count": len(content),
                    })
            current_label = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 最后一个块
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append({
                "label": current_label or "结尾",
                "content": content,
                "char_count": len(content),
            })

    # 对大块进一步拆分
    return _split_large_chunks(chunks, max_chars)


def _chunk_by_numbered_sections(text: str, max_chars: int) -> list[dict]:
    """按编号分段（如 1. / 一、/ (1)）。"""
    pattern = re.compile(
        r"^((?:\d+[、．.)]\s)|(?:第[一二三四五六七八九十百千]+[章节])|(?:[一二三四五六七八九十百千]+[、．]))",
        re.MULTILINE,
    )
    parts = pattern.split(text)

    chunks: list[dict] = []
    # parts[0] 是第一个分隔符之前的内容
    if parts and parts[0].strip():
        chunks.append({"label": "前言", "content": parts[0].strip(), "char_count": len(parts[0])})

    # 后续成对出现：分隔符 + 内容
    i = 1
    while i + 1 < len(parts):
        label = parts[i].strip().rstrip("、．.")
        content = parts[i + 1].strip()
        if content:
            chunks.append({"label": label, "content": content, "char_count": len(content)})
        i += 2

    return _split_large_chunks(chunks, max_chars)


def _chunk_by_paragraphs(text: str, max_chars: int) -> list[dict]:
    """按空行段落组分块，控制每块大小。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[dict] = []
    current_label = ""
    current_parts: list[str] = []
    current_len = 0
    part_num = 1

    for para in paragraphs:
        para_len = len(para)

        if current_len + para_len > max_chars and current_parts:
            # 保存当前块
            content = "\n\n".join(current_parts)
            chunks.append({
                "label": current_label or f"第{part_num}部分",
                "content": content,
                "char_count": current_len,
            })
            part_num += 1
            current_parts = []
            current_len = 0

            # 新块的标签：尝试从段落开头提取
            first_line = para.split("\n")[0].strip()
            if len(first_line) < 60 and (
                first_line.isupper() or
                re.match(r"^[一二三四五六七八九十百千]+[、．]", first_line) or
                re.match(r"^\d+[、．.)]", first_line)
            ):
                current_label = first_line
            else:
                current_label = f"第{part_num}部分"

        current_parts.append(para)
        current_len += para_len

    # 最后一个块
    if current_parts:
        content = "\n\n".join(current_parts)
        chunks.append({
            "label": current_label or f"第{part_num}部分",
            "content": content,
            "char_count": current_len,
        })

    return chunks


def _split_large_chunks(chunks: list[dict], max_chars: int) -> list[dict]:
    """对超过 max_chars 的块按句子边界进一步拆分。"""
    result: list[dict] = []
    for chunk in chunks:
        if chunk["char_count"] <= max_chars:
            result.append(chunk)
            continue

        # 按句子边界拆分
        text = chunk["content"]
        sentences = re.split(r"(?<=[。！？.!?\n])\s*", text)
        sub_parts: list[str] = []
        sub_len = 0
        sub_idx = 0

        for sent in sentences:
            if sub_len + len(sent) > max_chars and sub_parts:
                sub_content = "".join(sub_parts)
                sub_idx += 1
                result.append({
                    "label": f"{chunk['label']}({sub_idx})",
                    "content": sub_content,
                    "char_count": sub_len,
                })
                sub_parts = []
                sub_len = 0
            sub_parts.append(sent)
            sub_len += len(sent)

        if sub_parts:
            sub_content = "".join(sub_parts)
            label_suffix = f"({sub_idx + 1})" if sub_idx > 0 else ""
            result.append({
                "label": f"{chunk['label']}{label_suffix}",
                "content": sub_content,
                "char_count": sub_len,
            })

    return result


def _merge_small_chunks(chunks: list[dict], min_size: int = _MIN_CHUNK_SIZE) -> list[dict]:
    """仅合并尾部孤立的过小块到前一块。保留有结构的分块。"""
    if len(chunks) <= 1:
        return chunks

    # 只检查最后一块是否孤立的过小块
    last = chunks[-1]
    if last["char_count"] < min_size and len(chunks) >= 2:
        # 合并到前一块
        chunks[-2]["content"] += "\n\n" + last["content"]
        chunks[-2]["char_count"] += last["char_count"]
        chunks[-2]["label"] += "+" + last["label"]
        chunks.pop()

    return chunks


def _check_pdf_available() -> bool:
    try:
        import PyPDF2  # noqa: F401
        return True
    except ImportError:
        return False


def _check_docx_available() -> bool:
    try:
        import docx  # noqa: F401
        return True
    except ImportError:
        return False
