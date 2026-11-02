import ast
import hashlib
import re

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
import yaml

VERSION = "notes-v2-1"
BUDGET = 320
CONTEXT_BUDGET = 1200
GENERIC = {"todo", "to do", "笔记", "杂记", "今天做了什么", "周会信息"}
MD = MarkdownIt("commonmark").enable(["table", "strikethrough"])


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def visible(node):
    if node.type in {"fence", "code_block"}:
        return node.content.rstrip()
    if node.type == "text":
        return clean_text(node.content)
    if node.type == "code_inline":
        return node.content
    if node.type in {"softbreak", "hardbreak"}:
        return "\n"
    if node.type == "html_inline":
        return ""
    if node.type == "image":
        return "[图片未读取]"
    separator = "\n" if node.type in {
        "list_item", "bullet_list", "ordered_list", "blockquote"
    } else ""
    text = separator.join(visible(child) for child in node.children)
    return f"[已划去：{text}]" if node.type == "s" else text


def clean_text(value):
    value = re.sub(r"!\[\[[^\]]+\]\]", "[嵌入未读取]", value)
    value = re.sub(
        r"\[\[([^\]]+)\]\]",
        lambda m: m.group(1).split("|")[-1], value,
    )
    return value.strip()


def gate(text):
    patterns = [
        r"(?i)\b\w*(?:password|passwd|auth[_-]?key|api[_-]?key|"
        r"access[_-]?token|refresh[_-]?token|authorization|secret)\w*[\"']?\s*[:=]",
        r"\b\d{2,5}@[^@\s]+@[^@\s]+@",
        r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)",
    ]
    if any(re.search(pattern, text) for pattern in patterns):
        return "suspected_sensitive"
    if re.match(r"\s*(?:<!doctype\s+html|<html\b)", text, re.I):
        return "unsupported_full_html"
    fence = None
    for line in text.splitlines():
        marker = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)
        if not marker:
            continue
        run, rest = marker.groups()
        if fence is None:
            fence = run
        elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
            fence = None
    return "unclosed_fence" if fence else None


def parse_note(text):
    """返回已清理的结构块、已有元数据、诊断；不读取任何文件。"""
    reason = gate(text)
    if reason:
        return [], {}, [reason]
    lines = text.splitlines(keepends=True)
    metadata, warnings = {}, []
    if lines and lines[0].strip() == "---":
        stop = next(
            (i for i in range(1, len(lines))
             if lines[i].strip() in {"---", "..."}), None
        )
        if stop is None:
            return [], {}, ["unclosed_frontmatter"]
        try:
            metadata = yaml.safe_load("".join(lines[1:stop])) or {}
            if not isinstance(metadata, dict):
                return [], {}, ["frontmatter_not_mapping"]
        except yaml.YAMLError:
            return [], {}, ["invalid_frontmatter"]
        lines[:stop + 1] = ["\n"] * (stop + 1)
    root = SyntaxTreeNode(MD.parse("".join(lines)))
    atoms, headings, section, depth = [], [], 0, 0
    can_global = True

    def add(node, kind=None, content=None, spans=None):
        raw = visible(node)
        code = node.type in {"fence", "code_block"}
        value = (raw if code else raw.strip()) if content is None else content.strip()
        if not value:
            return
        kind = kind or node.type
        original_inline = node.children[0].content if node.type == "paragraph" and node.children else raw
        if re.fullmatch(r"\[\[[^\]]+\]\]", original_inline.strip()):
            kind = "reference"
            warnings.append("link_target_not_read")
        if value in {"[图片未读取]", "[嵌入未读取]"}:
            kind = "reference"
            warnings.append("media_not_read")
        if node.type == "fence" and node.token.info.split()[:1] in [["dataview"], ["dataviewjs"]]:
            value, kind = "[插件查询未执行]", "reference"
            warnings.append("plugin_not_run")
        if value == "pass" and kind == "paragraph":
            warnings.append("placeholder")
            return
        heading = " / ".join(h for h in headings if h)
        atoms.append({
            "kind": kind, "text": value,
            "heading": heading, "section": section,
            "specific": bool(headings and headings[-1].casefold() not in GENERIC),
            "spans": spans or [[node.map[0] + 1, node.map[1]]],
            "language": (node.token.info or "").split()[0]
            if node.type == "fence" and node.token.info else "",
            "global_candidate": can_global and bool(re.search(
                r"(?:边界|适用范围|运行环境|版本说明|前提条件)\s*[:：]", value
            )),
        })

    for node in root.children:
        if node.type == "heading":
            depth = int(node.tag[1:])
            if not (depth == 1 and section == 0):
                can_global = False
            label = visible(node).strip()
            headings = (headings + [""] * depth)[:depth - 1] + [label]
            section += 1
        elif node.type in {"bullet_list", "ordered_list"}:
            for item in node.children:
                value = visible(item).strip()
                add(item, "task" if re.match(r"^\[[ xX]\]", value) else "list_item")
        elif node.type == "table":
            rows = [n for n in node.walk() if n.type == "tr"]
            headers = [visible(cell) for cell in rows[0].children]
            for row in rows[1:]:
                values = [visible(cell) for cell in row.children]
                content = " | ".join(
                    f"{key}: {value}" for key, value in zip(headers, values)
                )
                add(row, "table_row", content, [
                    [rows[0].map[0] + 1, rows[0].map[1]],
                    [row.map[0] + 1, row.map[1]],
                ])
        elif node.type == "html_block":
            warnings.append("unsupported_html_fragment")
            section += 1
        else:
            add(node)
    if not atoms:
        warnings.append("no_body")
    return atoms, metadata, warnings


def split_piece(value, prefix, count, code=False):
    """优先行/句末边界；最终重数 token，保持清理后文本不丢失。"""
    if count(prefix + value) <= BUDGET:
        return [value]
    if len(value) <= 1:
        raise ValueError("标题前缀过长，无法容纳正文。")
    midpoint = len(value) // 2
    pattern = r"\n" if code else r"\n|[。！？!?；;]|\.(?=\s|$)"
    points = [m.end() for m in re.finditer(pattern, value) if m.end() < len(value)]
    cut = min(points, key=lambda p: abs(p - midpoint)) if points else midpoint
    return (
        split_piece(value[:cut], prefix, count, code)
        + split_piece(value[cut:], prefix, count, code)
    )


def code_parts(atom):
    text = atom["text"]
    if atom["language"].casefold() not in {"python", "py"}:
        return [text]
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return [text]
    lines = text.splitlines(keepends=True)
    starts = {0, len(lines)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            starts.add(min(
                [node.lineno - 1] + [d.lineno - 1 for d in node.decorator_list]
            ))
            starts.add(node.end_lineno)
    points = sorted(starts)
    parts, pending = [], ""
    for a, b in zip(points, points[1:]):
        value = "".join(lines[a:b])
        if value.strip():
            parts.append(pending + value)
            pending = ""
        elif parts:
            parts[-1] += value
        else:
            pending += value
    return parts or [text]


def make_records(source, title, atoms, count):
    groups, current = [], []
    short_note = (
        atoms and not any(a["heading"] for a in atoms)
        and all(a["kind"] == "paragraph" for a in atoms)
        and count("\n\n".join(a["text"] for a in atoms)) <= BUDGET
    )
    cues = r"^(?:例如|执行|输出|结果|其中|因此|所以|注意|正确|错误|解决|前提|现象|结论)"
    for atom in atoms:
        previous = current[-1] if current else None
        dependent = bool(previous and (
            atom["kind"] in {"fence", "code_block"}
            or re.match(cues, atom["text"])
            or previous["text"].endswith(("：", ":"))
        ))
        same_section = bool(previous and previous["section"] == atom["section"])
        join = same_section and (
            short_note or dependent
            or (atom["specific"] and count("\n\n".join(
                a["text"] for a in current + [atom]
            )) <= CONTEXT_BUDGET)
        )
        if atom["kind"] in {"task", "table_row"}:
            join = False
        if not join and current:
            groups.append(current)
            current = []
        current.append(atom)
        if atom["kind"] in {"task", "table_row"}:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    parents, chunks, occurrences = {}, [], {}
    global_parts = [a for a in atoms if a["global_candidate"]]
    for number, group in enumerate(groups, 1):
        heading = group[0]["heading"]
        text = "\n\n".join(a["text"] for a in group)
        parent_id = digest(source + "\0" + heading + "\0" + text + "\0" + str(number))[:32]
        spans = [span for a in group for span in a["spans"]]
        global_text = "\n\n".join(a["text"] for a in global_parts)
        parents[parent_id] = {
            "source": source, "heading": heading, "text": text, "spans": spans,
            "global_context": global_text,
            "global_spans": [s for a in global_parts for s in a["spans"]],
            "context_tokens": count(
                (global_text + "\n\n" if global_text and global_text not in text else "") + text
            ),
        }
        prefix = f"笔记：{title}\n小节：{heading}\n\n"
        if count(prefix) >= BUDGET:
            raise ValueError(f"{source} 的标题上下文超过预算。")
        for atom in group:
            if atom["kind"] == "reference":
                continue
            code = atom["kind"] in {"fence", "code_block"}
            parts = code_parts(atom) if code and count(prefix + atom["text"]) > BUDGET else [atom["text"]]
            for part in parts:
                for piece in split_piece(part, prefix, count, code):
                    if not piece.strip():
                        continue
                    embedding_text = prefix + piece
                    key = digest(source + "\0" + embedding_text)
                    occurrence = occurrences.get(key, 0)
                    occurrences[key] = occurrence + 1
                    chunk_id = digest(key + str(occurrence))[:32]
                    chunks.append({
                        "id": chunk_id, "parent_id": parent_id,
                        "source": source, "heading": heading,
                        "kind": atom["kind"], "text": piece,
                        "embedding_text": embedding_text,
                        "line_start": atom["spans"][0][0],
                        "line_end": atom["spans"][-1][1],
                        "tokens": count(embedding_text),
                    })
    return parents, chunks