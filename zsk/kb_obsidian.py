"""
Obsidian Vault 生成器。
从 JSON 知识库生成完整 Obsidian vault：
  - 按分类文件夹组织 .md 笔记（YAML frontmatter + wikilinks）
  - JSON Canvas 图谱文件 (.canvas)
  - Obsidian Bases 数据库视图 (.base)
  - .obsidian/ 配置目录
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from kb_ontology import ONTOLOGY, PRIORITY_LEVELS


def generate_vault(kb, vault_dir: str | Path, incremental: bool = False) -> dict:
    """
    从 KnowledgeBase 生成完整 Obsidian vault。
    返回 {"created": N, "updated": N, "skipped": N}。
    """
    vault_dir = Path(vault_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)
    stats = {"created": 0, "updated": 0, "skipped": 0}

    # 1. 创建 .obsidian 配置
    _ensure_obsidian_config(vault_dir)

    # 2. 为每个知识节点生成 .md 笔记（跳过系统节点）
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

    # 3. 生成分类索引页
    for cat_id in ONTOLOGY:
        _write_category_index(kb, cat_id, vault_dir)

    # 4. 生成 MOC 总索引
    _write_moc(kb, vault_dir)

    # 5. 生成 .canvas 文件
    _write_canvas(kb, vault_dir)

    # 6. 生成 .base 文件
    _write_base(kb, vault_dir)

    return stats


# ── .obsidian 配置 ─────────────────────────────────────

def _ensure_obsidian_config(vault_dir: Path):
    """确保 .obsidian/ 目录和基础配置存在。"""
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    app_config = obsidian_dir / "app.json"
    if not app_config.exists():
        config = {
            "showLineNumber": False,
            "defaultViewMode": "preview",
            "livePreview": True,
        }
        app_config.write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    graph_config = obsidian_dir / "graph.json"
    if not graph_config.exists():
        category_colors = {
            "architecture": "#d32f2f",
            "planning": "#f57c00",
            "tool-calling": "#1976d2",
            "memory": "#388e3c",
            "multi-agent": "#7b1fa2",
            "rag": "#0097a7",
            "evaluation": "#fbc02d",
            "safety": "#757575",
        }
        groups = [
            {
                "query": f"path:{idx:02d}-",
                "color": color,
                "label": ONTOLOGY[cat]["label"],
            }
            for idx, (cat, color) in enumerate(
                sorted(category_colors.items(), key=lambda x: list(ONTOLOGY.keys()).index(x[0])),
                start=1,
            )
        ]
        graph = {
            "collapse-filter": False,
            "search": "",
            "showTags": True,
            "showAttachments": False,
            "hideUnresolved": False,
            "colorGroups": groups,
            "lineSizeMultiplier": 1.5,
        }
        graph_config.write_text(
            json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
        )


# ── 文件辅助 ───────────────────────────────────────────

def _safe_filename(title: str) -> str:
    """将标题转为安全的文件名（保留中文，移除非法字符）。"""
    safe = re.sub(r'[<>:"/\\|?*]', "-", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    if len(safe) > 80:
        safe = safe[:80]
    return safe


def _category_order(cat_id: str) -> int:
    """返回分类的排序序号（与 ONTOLOGY 顺序一致）。"""
    keys = list(ONTOLOGY.keys())
    return keys.index(cat_id) + 1 if cat_id in keys else 9


def _note_path(node, vault_dir: Path) -> Path:
    """返回笔记的文件路径：vault/XX-分类名/笔记名.md。"""
    if node.category and node.category in ONTOLOGY:
        idx = _category_order(node.category)
        cat_label = ONTOLOGY[node.category]["label"]
        folder = f"{idx:02d}-{cat_label}"
    else:
        folder = "09-未分类"
    filename = _safe_filename(node.title) + ".md"
    return vault_dir / folder / filename


# ── 笔记生成 ───────────────────────────────────────────

def _write_note(node, kb, note_path: Path, vault_dir: Path):
    """写入单个知识节点的 .md 笔记。"""
    pri_info = PRIORITY_LEVELS.get(node.priority, PRIORITY_LEVELS[5])
    cat_label = (
        ONTOLOGY.get(node.category, {}).get("label", "") if node.category else ""
    )

    # YAML frontmatter
    tags_lines = "\n  - ".join(node.tags) if node.tags else ""
    fm_parts = [
        "---",
        f"id: {node.id}",
        f"title: {node.title}",
        f"category: {node.category}",
        f"category_label: {cat_label}",
        f"priority: {node.priority}",
    ]
    if tags_lines:
        fm_parts.append("tags:\n  - " + tags_lines)
    else:
        fm_parts.append("tags: []")
    fm_parts.extend([
        f"source_file: {node.source_file}",
        f"source_section: {node.source_section}",
        f"created: {node.created_at[:10] if node.created_at else ''}",
        f"updated: {node.updated_at[:10] if node.updated_at else ''}",
        "---",
    ])

    # 正文头部
    stars = "⭐" * node.priority
    meta_parts = [
        f"> **优先级**: {stars} P{node.priority} {pri_info['label']}",
    ]
    if cat_label:
        meta_parts[0] += f"  |  **分类**: {cat_label}"
    if node.source_file:
        meta_parts[0] += f"  |  **来源**: {node.source_file}"

    body_parts = []
    body_parts.extend(fm_parts)
    body_parts.append("")
    body_parts.append(f"# {node.title}")
    body_parts.append("")
    body_parts.extend(meta_parts)
    body_parts.append("")
    if node.abstract:
        body_parts.append(f"> {node.abstract}")
        body_parts.append("")
    if node.content:
        body_parts.append(node.content)
        body_parts.append("")

    # 子概念
    children = kb.get_children(node.id)
    if children:
        body_parts.append("## 📂 子概念")
        for child in children:
            body_parts.append(f"- [[{child.title}]]")
        body_parts.append("")

    # 相关概念（同级兄弟节点）
    siblings = kb.get_siblings(node.id)
    if siblings:
        body_parts.append("## 🔗 相关概念")
        for sib in siblings:
            body_parts.append(f"- [[{sib.title}]]")
        body_parts.append("")

    # 参考文献
    if node.references:
        body_parts.append("## 📚 参考文献")
        for ref in node.references:
            body_parts.append(f"- {ref}")
        body_parts.append("")

    note_path.write_text("\n".join(body_parts), encoding="utf-8")


# ── 索引页 ────────────────────────────────────────────

def _write_category_index(kb, cat_id: str, vault_dir: Path):
    """生成分类索引页（_分类名.md）。"""
    if cat_id not in ONTOLOGY:
        return

    cat_info = ONTOLOGY[cat_id]
    idx = _category_order(cat_id)
    folder = vault_dir / f"{idx:02d}-{cat_info['label']}"
    folder.mkdir(parents=True, exist_ok=True)

    # 收集该分类下的概念
    cat_node = kb.get(f"cat-{cat_id}")
    concepts: list = []
    if cat_node:
        concepts = [kb.get(cid) for cid in cat_node.children if kb.get(cid)]

    lines = [
        "---",
        f"category: {cat_id}",
        f"category_label: {cat_info['label']}",
        "type: index",
        "---",
        "",
        f"# {cat_info['label']}",
        "",
        cat_info["description"],
        "",
        f"## 概念列表（{len(concepts)} 个）",
        "",
    ]

    for node in concepts:
        if node:
            stars = "⭐" * node.priority
            abstract_preview = (node.abstract[:80] + "…") if node.abstract and len(node.abstract) > 80 else (node.abstract or "")
            lines.append(
                f"- {stars} [[{node.title}]] — {abstract_preview}"
            )

    if cat_info.get("l2"):
        lines.append("")
        lines.append("## 二级分类")
        for l2 in cat_info["l2"]:
            lines.append(f"- `{l2}`")

    index_path = folder / f"_{cat_info['label']}.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")


def _write_moc(kb, vault_dir: Path):
    """生成 Map of Content 总索引页。"""
    index_dir = vault_dir / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    s = kb.stats()
    lines = [
        "---",
        "type: moc",
        "---",
        "",
        "# 🧠 Agent 开发技术知识库",
        "",
        f"> 节点总数: **{s['node_count']}**  |  最大深度: **{s['max_depth']}** 层",
        "",
        "## 📂 分类导航",
        "",
    ]

    for cat_id, cat_info in ONTOLOGY.items():
        cat_node = kb.get(f"cat-{cat_id}")
        count = len(cat_node.children) if cat_node else 0
        lines.append(
            f"- **[[{cat_info['label']}|{cat_info['label']}]]** ({count} 个概念)"
        )
        lines.append(f"  {cat_info['description']}")
        lines.append("")

    # 优先级分布
    if s.get("by_priority"):
        lines.append("## 📊 优先级分布")
        lines.append("")
        for level, count in s["by_priority"].items():
            pri_info = PRIORITY_LEVELS.get(level, {})
            label = pri_info.get("label", f"P{level}")
            lines.append(f"- P{level} {label}: **{count}** 个节点")
        lines.append("")

    # 标签云
    if s.get("top_tags"):
        top = list(s["top_tags"].items())[:15]
        lines.append("## 🏷 热门标签")
        lines.append("")
        tags_str = "  ".join([f"`{tag}`({count})" for tag, count in top])
        lines.append(tags_str)
        lines.append("")

    moc_path = index_dir / "知识库总览.md"
    moc_path.write_text("\n".join(lines), encoding="utf-8")


# ── Canvas 生成 ─────────────────────────────────────────

def _write_canvas(kb, vault_dir: Path):
    """生成 JSON Canvas 图谱文件。"""
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

    # 主根节点
    canvas["nodes"].append({
        "id": "kb-root",
        "type": "text",
        "x": root_x,
        "y": -120,
        "width": node_width,
        "height": node_height,
        "color": "1",
    })

    for col, cat_id in enumerate(cat_ids):
        cat_node = kb.get(f"cat-{cat_id}")
        if not cat_node:
            continue

        cat_info = ONTOLOGY[cat_id]
        x = col * col_width
        y = 0

        cat_file = f"{_category_order(cat_id):02d}-{cat_info['label']}/_{cat_info['label']}.md"
        canvas["nodes"].append({
            "id": cat_node.id,
            "type": "text",
            "x": x,
            "y": y,
            "width": node_width,
            "height": node_height,
            "file": cat_file,
            "color": "2",
        })
        canvas["edges"].append({
            "id": f"edge-root-{cat_id}",
            "fromNode": "kb-root",
            "toNode": cat_node.id,
        })

        # 该分类下的概念节点
        concepts = kb.get_children(cat_node.id)
        for row, concept in enumerate(concepts):
            cy = y + (row + 1) * row_height
            note_path = _note_path(concept, vault_dir)
            rel_path = str(note_path.relative_to(vault_dir))
            canvas["nodes"].append({
                "id": concept.id,
                "type": "text",
                "x": x,
                "y": cy,
                "width": node_width,
                "height": node_height,
                "file": rel_path,
                "color": "3",
            })
            canvas["edges"].append({
                "id": f"edge-{cat_id}-{concept.id}",
                "fromNode": cat_node.id,
                "toNode": concept.id,
            })

    canvas_path = vault_dir / "知识图谱.canvas"
    canvas_path.write_text(
        json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Base 生成 ───────────────────────────────────────────

def _write_base(kb, vault_dir: Path):
    """生成 Obsidian Bases 数据库视图。"""
    base = {
        "name": "知识库",
        "views": [
            {
                "type": "table",
                "name": "全部节点",
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
                "type": "card",
                "name": "按分类",
                "columns": [
                    {"field": "title", "label": "标题"},
                    {"field": "priority", "label": "优先级"},
                ],
                "groupBy": "category_label",
            },
            {
                "type": "table",
                "name": "按优先级",
                "columns": [
                    {"field": "title", "label": "标题"},
                    {"field": "category_label", "label": "分类"},
                    {"field": "abstract", "label": "摘要"},
                ],
                "filters": [],
                "groupBy": "priority",
            },
        ],
    }

    base_path = vault_dir / "知识库.base"
    base_path.write_text(
        json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8"
    )
