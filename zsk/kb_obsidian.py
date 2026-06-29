"""
Obsidian Vault 生成器。
从 JSON 知识库生成完整 Obsidian vault：
  - 按分类文件夹组织 .md 笔记（YAML frontmatter + wikilinks）
  - JSON Canvas 图谱文件 (.canvas)
  - Obsidian Bases 数据库视图 (.base)
  - .obsidian/ 配置目录
  本体分类自适应：颜色、分组根据实际分类数量动态生成。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from kb_ontology import PRIORITY_LEVELS, get_ontology, get_domain_label

# 模块加载时获取当前本体
ONTOLOGY = get_ontology()

# 动态配色调色板（最多支持 20 个分类）
_DYNAMIC_COLORS = [
    "#d32f2f", "#f57c00", "#1976d2", "#388e3c", "#7b1fa2",
    "#0097a7", "#fbc02d", "#757575", "#e91e63", "#4caf50",
    "#2196f3", "#ff9800", "#9c27b0", "#00bcd4", "#ff5722",
    "#607d8b", "#8bc34a", "#3f51b5", "#cddc39", "#795548",
]


def _get_color_for_category(cat_index: int) -> str:
    return _DYNAMIC_COLORS[cat_index % len(_DYNAMIC_COLORS)]


def generate_vault(kb, vault_dir: str | Path, incremental: bool = False) -> dict:
    """
    从 KnowledgeBase 生成完整 Obsidian vault。
    返回 {"created": N, "updated": N, "skipped": N}。
    """
    global ONTOLOGY
    ONTOLOGY = get_ontology()

    vault_dir = Path(vault_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)
    stats = {"created": 0, "updated": 0, "skipped": 0}

    # 清理旧分类文件夹和索引文件（防止本体切换后残留）
    if not incremental:
        _clean_old_folders(vault_dir)

    _ensure_obsidian_config(vault_dir)

    for node in kb.nodes.values():
        if node.id == "kb-root" or node.id.startswith("cat-"):
            continue
        note_path = _note_path(node, vault_dir)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        if note_path.exists():
            if incremental:
                stats["skipped"] += 1
                continue
            else:
                stats["updated"] += 1
        else:
            stats["created"] += 1
        _write_note(node, kb, note_path, vault_dir)

    for cat_id in ONTOLOGY:
        _write_category_index(kb, cat_id, vault_dir)

    _write_moc(kb, vault_dir)
    _write_canvas(kb, vault_dir)
    _write_base(kb, vault_dir)

    return stats


def _ensure_obsidian_config(vault_dir: Path):
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    app_config = obsidian_dir / "app.json"
    if not app_config.exists():
        config = {"showLineNumber": False, "defaultViewMode": "preview", "livePreview": True}
        app_config.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    graph_config = obsidian_dir / "graph.json"
    groups = []
    for idx, (cat_id, cat_info) in enumerate(ONTOLOGY.items()):
        color = _get_color_for_category(idx)
        groups.append({
            "query": f"path:{idx + 1:02d}-",
            "color": color,
            "label": cat_info["label"],
        })
    graph = {
        "collapse-filter": False,
        "search": "",
        "showTags": True,
        "showAttachments": False,
        "hideUnresolved": False,
        "colorGroups": groups,
        "lineSizeMultiplier": 1.5,
    }
    graph_config.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_old_folders(vault_dir: Path):
    """删除旧本体生成的分类文件夹和索引文件。"""
    import shutil
    # 清理编号文件夹（XX-分类名）
    for item in vault_dir.iterdir():
        if item.is_dir() and re.match(r"^\d{2}-", item.name):
            shutil.rmtree(item)
    # 清理旧索引
    index_dir = vault_dir / "_index"
    if index_dir.exists():
        shutil.rmtree(index_dir)
    # 清理旧的 canvas 和 base
    for stale in ("知识图谱.canvas", "知识库.base"):
        p = vault_dir / stale
        if p.exists():
            p.unlink()


def _safe_filename(title: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]', "-", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe[:80] if len(safe) > 80 else safe


def _category_order(cat_id: str) -> int:
    keys = list(ONTOLOGY.keys())
    return keys.index(cat_id) + 1 if cat_id in keys else 99


def _note_path(node, vault_dir: Path) -> Path:
    if node.category and node.category in ONTOLOGY:
        idx = _category_order(node.category)
        cat_label = ONTOLOGY[node.category]["label"]
        folder = f"{idx:02d}-{cat_label}"
    else:
        folder = "99-未分类"
    return vault_dir / folder / (_safe_filename(node.title) + ".md")


def _write_note(node, kb, note_path: Path, vault_dir: Path):
    pri_info = PRIORITY_LEVELS.get(node.priority, PRIORITY_LEVELS[5])
    cat_label = ONTOLOGY.get(node.category, {}).get("label", "") if node.category else ""

    tags_lines = "\n  - ".join(node.tags) if node.tags else ""
    fm_parts = [
        "---",
        f"id: {node.id}",
        f"title: {node.title}",
        f"category: {node.category}",
        f"category_label: {cat_label}",
        f"priority: {node.priority}",
    ]
    fm_parts.append("tags:\n  - " + tags_lines if tags_lines else "tags: []")
    fm_parts.extend([
        f"source_file: {node.source_file}",
        f"source_section: {node.source_section}",
        f"created: {node.created_at[:10] if node.created_at else ''}",
        f"updated: {node.updated_at[:10] if node.updated_at else ''}",
        "---",
    ])

    stars = "⭐" * node.priority
    meta = f"> **优先级**: {stars} P{node.priority} {pri_info['label']}"
    if cat_label:
        meta += f"  |  **分类**: {cat_label}"
    if node.source_file:
        meta += f"  |  **来源**: {node.source_file}"

    body = [*fm_parts, "", f"# {node.title}", "", meta, ""]
    if node.abstract:
        body.append(f"> {node.abstract}")
        body.append("")
    if node.content:
        body.append(node.content)
        body.append("")

    children = kb.get_children(node.id)
    if children:
        body.append("## 📂 子概念")
        for child in children:
            body.append(f"- [[{child.title}]]")
        body.append("")

    siblings = kb.get_siblings(node.id)
    if siblings:
        body.append("## 🔗 相关概念")
        for sib in siblings:
            body.append(f"- [[{sib.title}]]")
        body.append("")

    if node.references:
        body.append("## 📚 参考文献")
        for ref in node.references:
            body.append(f"- {ref}")
        body.append("")

    note_path.write_text("\n".join(body), encoding="utf-8")


def _write_category_index(kb, cat_id: str, vault_dir: Path):
    if cat_id not in ONTOLOGY:
        return
    cat_info = ONTOLOGY[cat_id]
    idx = _category_order(cat_id)
    folder = vault_dir / f"{idx:02d}-{cat_info['label']}"
    folder.mkdir(parents=True, exist_ok=True)

    cat_node = kb.get(f"cat-{cat_id}")
    concepts = [kb.get(cid) for cid in cat_node.children if kb.get(cid)] if cat_node else []

    lines = [
        "---", f"category: {cat_id}", f"category_label: {cat_info['label']}",
        "type: index", "---", "",
        f"# {cat_info['label']}", "",
        cat_info["description"], "",
        f"## 概念列表（{len(concepts)} 个）", "",
    ]
    for node in concepts:
        if node:
            stars = "⭐" * node.priority
            a = (node.abstract[:80] + "…") if node.abstract and len(node.abstract) > 80 else (node.abstract or "")
            lines.append(f"- {stars} [[{node.title}]] — {a}")
    if cat_info.get("l2"):
        lines.append("")
        lines.append("## 二级分类")
        for l2 in cat_info["l2"]:
            lines.append(f"- `{l2}`")
    (folder / f"_{cat_info['label']}.md").write_text("\n".join(lines), encoding="utf-8")


def _write_moc(kb, vault_dir: Path):
    index_dir = vault_dir / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)
    s = kb.stats()
    domain = get_domain_label() or "知识库"

    lines = [
        "---", "type: moc", "---", "",
        f"# 🧠 {domain}", "",
        f"> 节点总数: **{s['node_count']}**  |  最大深度: **{s['max_depth']}** 层",
        "", "## 📂 分类导航", "",
    ]
    for cat_id, cat_info in ONTOLOGY.items():
        cat_node = kb.get(f"cat-{cat_id}")
        count = len(cat_node.children) if cat_node else 0
        lines.append(f"- **[[{cat_info['label']}|{cat_info['label']}]]** ({count} 个概念)")
        lines.append(f"  {cat_info['description']}")
        lines.append("")

    if s.get("by_priority"):
        lines.append("## 📊 优先级分布")
        lines.append("")
        for level, count in s["by_priority"].items():
            pri_info = PRIORITY_LEVELS.get(level, {})
            lines.append(f"- P{level} {pri_info.get('label', '')}: **{count}** 个节点")
        lines.append("")

    if s.get("top_tags"):
        top = list(s["top_tags"].items())[:15]
        lines.append("## 🏷 热门标签")
        lines.append("")
        lines.append("  ".join([f"`{tag}`({count})" for tag, count in top]))
        lines.append("")

    (index_dir / f"{domain}总览.md").write_text("\n".join(lines), encoding="utf-8")


def _write_canvas(kb, vault_dir: Path):
    canvas = {"nodes": [], "edges": []}
    root = kb.get("kb-root")
    if not root:
        return

    cat_ids = list(ONTOLOGY.keys())
    col_width = 420
    row_height = 260
    node_width = 320
    node_height = 60
    root_x = (len(cat_ids) * col_width) // 2 - node_width // 2

    canvas["nodes"].append({
        "id": "kb-root", "type": "text",
        "x": root_x, "y": -120, "width": node_width, "height": node_height, "color": "1",
    })

    for col, cat_id in enumerate(cat_ids):
        cat_node = kb.get(f"cat-{cat_id}")
        if not cat_node:
            continue
        cat_info = ONTOLOGY[cat_id]
        x = col * col_width
        cat_file = f"{_category_order(cat_id):02d}-{cat_info['label']}/_{cat_info['label']}.md"
        canvas["nodes"].append({
            "id": cat_node.id, "type": "text",
            "x": x, "y": 0, "width": node_width, "height": node_height,
            "file": cat_file, "color": "2",
        })
        canvas["edges"].append({
            "id": f"edge-root-{cat_id}", "fromNode": "kb-root", "toNode": cat_node.id,
        })

        concepts = kb.get_children(cat_node.id)
        for row, concept in enumerate(concepts):
            cy = 0 + (row + 1) * row_height
            note_path = _note_path(concept, vault_dir)
            rel_path = str(note_path.relative_to(vault_dir))
            canvas["nodes"].append({
                "id": concept.id, "type": "text",
                "x": x, "y": cy, "width": node_width, "height": node_height,
                "file": rel_path, "color": "3",
            })
            canvas["edges"].append({
                "id": f"edge-{cat_id}-{concept.id}",
                "fromNode": cat_node.id, "toNode": concept.id,
            })

    (vault_dir / "知识图谱.canvas").write_text(
        json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_base(kb, vault_dir: Path):
    base = {
        "name": "知识库",
        "views": [
            {
                "type": "table", "name": "全部节点",
                "columns": [
                    {"field": "title", "label": "标题"},
                    {"field": "category_label", "label": "分类"},
                    {"field": "priority", "label": "优先级"},
                    {"field": "tags", "label": "标签"},
                    {"field": "source_file", "label": "来源"},
                ],
                "sorts": [{"field": "priority", "direction": "asc"}],
            },
            {
                "type": "card", "name": "按分类",
                "columns": [
                    {"field": "title", "label": "标题"},
                    {"field": "priority", "label": "优先级"},
                ],
                "groupBy": "category_label",
            },
            {
                "type": "table", "name": "按优先级",
                "columns": [
                    {"field": "title", "label": "标题"},
                    {"field": "category_label", "label": "分类"},
                    {"field": "abstract", "label": "摘要"},
                ],
                "groupBy": "priority",
            },
        ],
    }
    (vault_dir / "知识库.base").write_text(
        json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
