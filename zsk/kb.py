#!/usr/bin/env python3
"""
知识库 CLI 工具。
用法: python kb.py <command> [options]

命令:
  list       列出所有知识点
  search     全文搜索
  show       查看详情
  stats      统计信息
  add        手动添加知识点
  edit       编辑知识点
  delete     删除知识点
  import     从 MD 研报导入
  export     导出 HTML 可视化
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path
from kb_core import KnowledgeBase, KnowledgeNode
from kb_ontology import ONTOLOGY, PRIORITY_LEVELS, PREDEFINED_TAGS
from kb_agent import detect_agents, install_skills, uninstall_skills, get_primary_agent, get_build_command, get_install_message

# 项目根目录 — 始终是 kb.py 所在目录，无论从何处调用
PROJECT_DIR = Path(__file__).resolve().parent


def cmd_list(kb: KnowledgeBase, args):
    nodes = kb.list_all()
    if args.category:
        nodes = [n for n in nodes if n.category == args.category]
    if args.tag:
        nodes = [n for n in nodes if args.tag in n.tags]
    if args.priority:
        nodes = [n for n in nodes if n.priority == args.priority]
    if args.limit:
        nodes = nodes[:args.limit]

    if not nodes:
        print("（无知识点）")
        return

    for n in nodes:
        stars = "⭐" * n.priority
        cat = f"[{ONTOLOGY.get(n.category, {}).get('label', n.category)}]" if n.category else ""
        tags = ", ".join(n.tags[:3]) if n.tags else ""
        print(f"  {stars} {n.id:14s} {cat:8s} {n.title}")
        if args.verbose:
            print(f"       {n.abstract[:100]}")
            if tags:
                print(f"       🏷 {tags}")
            print()


def cmd_search(kb: KnowledgeBase, args):
    results = kb.search(args.keyword)
    if not results:
        print(f"未找到匹配 '{args.keyword}' 的知识点")
        return
    print(f"找到 {len(results)} 个结果：\n")
    for n in results:
        stars = "⭐" * n.priority
        cat = f"[{ONTOLOGY.get(n.category, {}).get('label', n.category)}]" if n.category else ""
        print(f"  {stars} {n.id:14s} {cat:8s} {n.title}")
        if n.abstract:
            print(f"       {n.abstract[:120]}")
        print()


def cmd_show(kb: KnowledgeBase, args):
    node = kb.get(args.id)
    if not node:
        print(f"未找到节点: {args.id}")
        return

    pri = PRIORITY_LEVELS.get(node.priority, PRIORITY_LEVELS[5])
    cat = ONTOLOGY.get(node.category, {}).get("label", node.category) if node.category else "-"

    print(f"{'=' * 60}")
    print(f"📌 {node.title}")
    print(f"{'=' * 60}")
    print(f"ID:       {node.id}")
    print(f"优先级:   {pri['label']} (P{node.priority})")
    print(f"分类:     {cat}  /  {node.l2_category or '-'}")
    print(f"来源:     {node.source_file}  § {node.source_section}")
    print(f"标签:     {', '.join(node.tags) if node.tags else '-'}")
    print(f"父节点:   {node.parent_id or '(根节点)'}")
    children = kb.get_children(node.id)
    print(f"子节点:   {', '.join(c.title for c in children) if children else '(无)'}")
    print(f"创建:     {node.created_at}")
    print(f"更新:     {node.updated_at}")
    if node.abstract:
        print(f"\n📝 摘要:")
        print(f"   {node.abstract}")
    if node.references:
        print(f"\n📚 参考文献:")
        for r in node.references:
            print(f"   {r}")
    print(f"\n{'─' * 60}")
    print(f"📄 正文 (Markdown):")
    print(f"{'─' * 60}")
    print(node.content if node.content else "（无内容）")
    print(f"{'─' * 60}")


def cmd_stats(kb: KnowledgeBase, args):
    s = kb.stats()
    print(f"{'=' * 40}")
    print(f"📊 知识库统计")
    print(f"{'=' * 40}")
    print(f"节点总数:   {s['node_count']}")
    print(f"最大深度:   {s['max_depth']}")
    print(f"\n按分类:")
    for cat, count in s["by_category"].items():
        label = ONTOLOGY.get(cat, {}).get("label", cat)
        bar = "█" * min(count, 40)
        print(f"  {label:12s} {count:3d}  {bar}")
    print(f"\n按优先级:")
    for level, count in s["by_priority"].items():
        label = PRIORITY_LEVELS.get(level, {}).get("label", f"P{level}")
        print(f"  P{level} {label:8s} {count:3d}")
    print(f"\n热门标签:")
    for tag, count in list(s["top_tags"].items())[:10]:
        print(f"  {tag:20s} {count:3d}")


def cmd_add(kb: KnowledgeBase, args):
    node = KnowledgeNode(
        id=args.id or "",
        title=args.title,
        abstract=args.abstract or "",
        content=args.content or "",
        priority=args.priority or 3,
        tags=args.tags.split(",") if args.tags else [],
        category=args.category or "",
        l2_category=args.l2 or "",
        parent_id=args.parent or None,
        source_file=args.source or "",
        source_section=args.section or "",
    )
    nid = kb.add(node)
    print(f"✅ 已添加: {node.title}  (id={nid})")


def cmd_edit(kb: KnowledgeBase, args):
    updates = {}
    if args.title is not None:
        updates["title"] = args.title
    if args.abstract is not None:
        updates["abstract"] = args.abstract
    if args.content is not None:
        updates["content"] = args.content
    if args.priority is not None:
        updates["priority"] = args.priority
    if args.tags is not None:
        updates["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.category is not None:
        updates["category"] = args.category
    if args.l2 is not None:
        updates["l2_category"] = args.l2
    if args.parent is not None:
        updates["parent_id"] = args.parent if args.parent != "none" else None
    if args.source is not None:
        updates["source_file"] = args.source
    if args.section is not None:
        updates["source_section"] = args.section

    if not updates:
        print("未提供任何更新字段")
        return

    ok = kb.update(args.id, **updates)
    if ok:
        print(f"✅ 已更新: {args.id}")
        cmd_show(kb, args)
    else:
        print(f"❌ 未找到节点: {args.id}")


def cmd_delete(kb: KnowledgeBase, args):
    node = kb.get(args.id)
    if not node:
        print(f"❌ 未找到节点: {args.id}")
        return
    ok = kb.delete(args.id, cascade=args.cascade)
    if ok:
        mode = "（级联删除子节点）" if args.cascade else "（子节点已提升为根节点）"
        print(f"🗑 已删除: {node.title} {mode}")
    else:
        print(f"❌ 删除失败: {args.id}")


def cmd_import(kb: KnowledgeBase, args):
    from kb_import import import_and_merge, import_directory_merge

    filepath = Path(args.path)

    print("=" * 60)
    print("⚠  import 是规则匹配模式，准确度有限")
    print("=" * 60)
    print()
    print("   💡 建议改用智能构建模式以获得更准确的知识树：")
    print(f"      python3 {PROJECT_DIR}/kb.py build")
    print()
    print("   build 模式会输出完整分析报告，由 Agent 语义理解每个概念后再精准构建。")
    print("   import 模式仅作快速初导，可能漏合概念或分类错误。")
    print()
    print("   继续使用 import？(规则模式)[y/N] ", end="", flush=True)

    if not sys.stdin.isatty():
        # 非交互模式（agent 调用）→ 自动跳过，改用 build
        print("(非交互终端，自动跳过 import，请使用 build 命令)")
        print("=" * 60)
        return

    resp = input().strip().lower()
    if resp not in ("y", "yes"):
        print("已取消。请使用: python3 kb.py build")
        return

    print()

    if args.no_merge:
        # 旧模式：每份报告独立成树
        from kb_import import import_md, import_directory
        if filepath.is_dir():
            results = import_directory(filepath, default_category=args.category or "")
            total = 0
            for fname, nodes in results.items():
                if not args.dry_run:
                    for n in nodes:
                        kb.add(n)
                print(f"  📄 {fname}: {len(nodes)} 个知识点")
                total += len(nodes)
            if not args.dry_run:
                kb.ensure_category_tree()
                kb.fill_empty_abstracts()
                kb.dedup_pass()
            action = "将导入" if args.dry_run else "已导入"
            print(f"\n📦 {action} {len(results)} 个文件，共 {total} 个知识点（独立模式）")
        else:
            nodes = import_md(filepath, default_category=args.category or "")
            if not args.dry_run:
                for n in nodes:
                    kb.add(n)
                kb.ensure_category_tree()
                kb.fill_empty_abstracts()
                kb.dedup_pass()
            action = "将导入" if args.dry_run else "已导入"
            print(f"📄 {filepath.name}: {action} {len(nodes)} 个知识点（独立模式）\n")
            for n in nodes:
                cat = ONTOLOGY.get(n.category, {}).get("label", n.category) if n.category else "-"
                print(f"  {'⭐' * n.priority} [{cat}] {n.title}")
                print()
    else:
        # 默认：合并模式
        if args.dry_run:
            from kb_import import import_md
            if filepath.is_dir():
                for md_file in sorted(filepath.glob("*.md")):
                    nodes = import_md(md_file, default_category=args.category or "")
                    print(f"  📄 {md_file.name}: 预览 {len(nodes)} 个节点（将合并入已有知识树）")
            else:
                nodes = import_md(filepath, default_category=args.category or "")
                print(f"📄 {filepath.name}: 预览 {len(nodes)} 个节点（将合并入已有知识树）\n")
                # 获取章节层级以识别 H1
                from kb_import import _parse_headings
                sections, _ = _parse_headings(Path(filepath).read_text(encoding="utf-8"))
                title_to_level = {s["title"]: s["level"] for s in sections}
                for n in nodes:
                    cat = ONTOLOGY.get(n.category, {}).get("label", n.category) if n.category else "-"
                    sec_level = title_to_level.get(n.source_section, 0)
                    if sec_level == 1 and not n.category and n.children:
                        action = "跳过"
                    elif not n.category and not n.children:
                        action = "跳过"
                    elif n.category and kb.find_by_title_category(n.title, n.category):
                        action = "合并"
                    else:
                        action = "新增"
                    print(f"  {action:4s} {'⭐' * n.priority} [{cat:6s}] {n.title}")
                print()
            print("⚠ 试运行模式。去掉 --dry-run 确认导入。")
        else:
            if filepath.is_dir():
                stats = import_directory_merge(kb, filepath, default_category=args.category or "")
            else:
                stats = import_and_merge(kb, filepath, default_category=args.category or "")
                print(f"📄 {filepath.name}: 合并 {stats['merged']}, 新增 {stats['new']}, 跳过 {stats['skipped']}")
                print()

    if args.dry_run and not args.no_merge:
        print("⚠ 试运行模式，未实际写入。去掉 --dry-run 确认导入。")

    if not filepath.exists():
        print(f"❌ 路径不存在: {args.path}")


def cmd_export(kb: KnowledgeBase, args):
    from kb_export import export_html

    output = Path(args.output) if args.output else (PROJECT_DIR / "output" / "knowledge_base.html")
    out_path = export_html(kb, output)
    print(f"✅ HTML 已导出: {out_path.resolve()}")
    print(f"   可在浏览器中打开查看")


def cmd_reorganize(kb: KnowledgeBase, args):
    """重建分类树层级：主根 → 8 个分类 → 概念节点。"""
    root_id = kb.ensure_category_tree()
    root = kb.get(root_id)
    print(f"✅ 分类树已重建")
    print(f"   主根: {root.title if root else '?'}")
    cats = kb.get_children(root_id)
    print(f"   分类: {len(cats)} 个")
    for c in cats:
        sub = kb.get_children(c.id)
        print(f"     [{c.title}] → {len(sub)} 个概念节点")
    print()
    print(f"   💡 建议运行 python3 kb.py export 更新可视化")


def cmd_dedup(kb: KnowledgeBase, args):
    """合并归一化标题相同的重复节点。"""
    n = kb.fill_empty_abstracts()
    if n:
        print(f"📝 填充了 {n} 个空摘要")
    result = kb.dedup_pass()
    if result["merged"]:
        print(f"🔗 合并了 {result['merged']} 对重复节点，移除 {result['removed']} 个")
    else:
        print("✅ 未发现重复节点")
    kb.ensure_category_tree()
    print(f"   💡 建议运行 python3 kb.py export 更新可视化")


def cmd_build(kb: KnowledgeBase, args):
    """
    读取 reports/ 下所有研报，输出结构化分析供 Agent 智能构建知识库。
    Agent 阅读此输出后，使用 kb.py add/edit 命令精确操作。
    """
    reports_dir = PROJECT_DIR / "reports"

    # 收集所有支持的文档格式
    from kb_doc_reader import list_supported_formats
    supported = list_supported_formats()
    patterns = ["*.md", "*.markdown"]
    if supported.get("pdf"):
        patterns.append("*.pdf")
    if supported.get("docx"):
        patterns.append("*.docx")
    patterns.extend(["*.html", "*.htm", "*.txt"])

    doc_files = []
    for pattern in patterns:
        doc_files.extend(reports_dir.glob(pattern))
    doc_files = sorted(set(doc_files), key=lambda f: f.name)

    if not doc_files:
        print("❌ reports/ 目录下没有文档。请先放入文档文件。")
        print(f"   支持的格式: {', '.join(f for f, ok in supported.items() if ok)}")
        if not supported.get("pdf"):
            print("   ⚠️ PDF 支持未启用。运行: pip install PyPDF2")
        if not supported.get("docx"):
            print("   ⚠️ DOCX 支持未启用。运行: pip install python-docx")
        return

    # ── 1. 当前 KB 状态 ──
    print("=" * 65)
    print("📊 当前知识库状态")
    print("=" * 65)
    s = kb.stats()
    print(f"节点: {s['node_count']}    最大深度: {s['max_depth']}")
    print()

    root = kb.get("kb-root")
    if root:
        for cid in root.children:
            cat = kb.get(cid)
            if not cat:
                continue
            concepts = kb.get_children(cid)
            names = [c.title for c in concepts]
            print(f"  [{cat.title}] {len(concepts)} 个概念: {', '.join(names) if names else '(空)'}")
    print()

    # ── 2. 本体论 ──
    print("=" * 65)
    print("📂 本体分类体系（8 个一级分类）")
    print("=" * 65)
    for cat_id, cat_info in ONTOLOGY.items():
        l2_list = cat_info.get("l2", [])
        print(f"  {cat_id:20s} {cat_info['label']}")
        print(f"  {'':20s} {cat_info['description']}")
        if l2_list:
            print(f"  {'':20s} 二级: {', '.join(l2_list)}")
        print()
    print()

    # ── 3. 研报分析 ──
    from kb_import import _parse_headings
    from kb_doc_reader import read_document, UnsupportedFormatError
    print("=" * 65)
    print(f"📄 研报分析（{len(doc_files)} 份）")
    print("=" * 65)

    for doc_file in doc_files:
        print(f"\n{'─' * 55}")
        print(f"📄 {doc_file.name}")
        print(f"{'─' * 55}")

        # 通过 kb_doc_reader 读取文档
        try:
            md_text = read_document(doc_file)
        except UnsupportedFormatError as e:
            print(f"  ⚠️ {e}")
            continue
        except FileNotFoundError as e:
            print(f"  ⚠️ {e}")
            continue

        suffix = doc_file.suffix.lower()
        is_md = suffix in (".md", ".markdown")

        # ── 非 MD 格式：智能分块分析 ──
        if not is_md:
            from kb_doc_reader import chunk_document, detect_structure
            struct = detect_structure(md_text)
            chunks = chunk_document(md_text, max_chars=4000, source_filename=doc_file.name)

            print(f"  📋 格式: {suffix}  |  结构: {struct.get('type', 'unknown')}  |  "
                  f"{len(md_text)} 字符  |  {len(chunks)} 个分块")
            print(f"  💡 无 Markdown 标题，已自动分块。Agent 需逐块阅读做语义提取。")
            print()

            for i, chunk in enumerate(chunks[:6]):
                preview = chunk["content"][:120].replace("\n", " ") + ("…" if len(chunk["content"]) > 120 else "")
                print(f"  📦 {chunk['label']} ({chunk['char_count']} 字符)")
                print(f"     {preview}")
            if len(chunks) > 6:
                print(f"  ... 还有 {len(chunks) - 6} 个分块")
            continue

        # ── MD 格式：标题层级分析 ──
        sections, refs = _parse_headings(md_text)

        # MD 但无标题结构：回退到分块分析
        if not sections:
            from kb_doc_reader import chunk_document, detect_structure
            struct = detect_structure(md_text)
            chunks = chunk_document(md_text, max_chars=4000, source_filename=doc_file.name)

            print(f"  📋 MD(无标题)  |  结构: {struct.get('type', 'unknown')}  |  "
                  f"{len(md_text)} 字符  |  {len(chunks)} 个分块")
            print(f"  💡 此 MD 文件无标题层级，已自动分块。Agent 需逐块阅读做语义提取。")
            print()

            for i, chunk in enumerate(chunks[:6]):
                preview = chunk["content"][:120].replace("\n", " ") + ("…" if len(chunk["content"]) > 120 else "")
                print(f"  📦 {chunk['label']} ({chunk['char_count']} 字符)")
                print(f"     {preview}")
            if len(chunks) > 6:
                print(f"  ... 还有 {len(chunks) - 6} 个分块")
            continue

        # MD 有标题结构：正常章节分析
        for sec in sections:
            indent = "  " * (sec["level"] - 1)
            prefix = "#" * sec["level"]
            title = sec["title"]

            # 自动分类建议
            from kb_ontology import map_section_to_category
            auto_cat = map_section_to_category(title)
            cat_hint = f"  ← 建议分类: {ONTOLOGY[auto_cat]['label']}" if auto_cat and auto_cat in ONTOLOGY else ""

            # 检查是否已存在
            exists = kb.find_by_title_category(title, auto_cat or "") if auto_cat else None
            exist_hint = " ⚠ 已存在(将合并)" if exists else ""

            # 内容预览
            content = sec["content"].strip()
            preview = content[:100].replace("\n", " ") + ("…" if len(content) > 100 else "")

            print(f"{indent}{prefix} {title}{cat_hint}{exist_hint}")
            if preview:
                print(f"{indent}   📝 {preview}")

            # 手动标注
            ann = sec.get("annotations", {})
            if ann:
                print(f"{indent}   🏷 标注: {ann}")

        if refs:
            print(f"\n  📚 参考文献 ({len(refs)} 条)")

    # ── 4. Agent 操作指引 ──
    print(f"\n{'=' * 65}")
    print("🤖 Agent 操作步骤")
    print(f"{'=' * 65}")
    print(f"""
请依次完成：

1. 阅读上方研报章节列表，为每个章节确定分类和优先级。
   - 分类来自 8 个本体类: {', '.join(ONTOLOGY.keys())}
   - 优先级: 1=核心基础 2=重要常用 3=一般了解 4=进阶深入 5=扩展选读

2. 对每个需要导入的概念，用以下命令操作：

   新增:  python3 {PROJECT_DIR}/kb.py add \\
           --title "<概念名>" --category <分类ID> --priority <1-5> \\
           --abstract "<一句话摘要>" --content "<正文>" --tags "tag1,tag2"

   更新:  python3 {PROJECT_DIR}/kb.py edit <已有节点ID> \\
           --priority <值> --content "<追加内容>"

3. 概念合并规则：
   - 已有节点（标注 ⚠已存在）→ 用 edit 追加内容，不要重复创建
   - 无标注的 → 新增节点
   - 不同报告中描述同一概念的 → 合并到一个节点下

4. 全部操作完成后，执行收尾：
   python3 {PROJECT_DIR}/kb.py reorganize
   python3 {PROJECT_DIR}/kb.py dedup
   python3 {PROJECT_DIR}/kb.py export
""")


def cmd_setup(kb: KnowledgeBase, args):
    """在新机器上注册 skills 到可用的 Agent（优先 Open Code）。"""
    agents = detect_agents()

    if not agents:
        print("⚠️ 未检测到 Open Code 或 Hermes Agent。")
        print("   skills/ 目录下的 skill 模板已就绪，可手动配置。")
        print(f"   Open Code skills 目录: ~/.open-code/skills/note-taking/")
        print(f"   Hermes skills 目录:  ~/.hermes/skills/note-taking/")
        return

    # 确定目标平台
    target = getattr(args, "platform", None)
    if target and target != "all":
        if target not in agents:
            print(f"⚠️ 未检测到 {target}，可用平台: {', '.join(agents)}")
            return
        platforms = [target]
    else:
        platforms = agents  # 安装到所有可用平台

    for platform in platforms:
        count = install_skills(platform, PROJECT_DIR)
        name = {"opencode": "Open Code", "hermes": "Hermes"}.get(platform, platform)
        print(f"   ✅ {name}: 已安装 {count} 个 skill")

    print()
    primary = agents[0]
    primary_name = {"opencode": "Open Code", "hermes": "Hermes"}.get(primary, primary)
    print(f"📦 Skills 已注册到 {primary_name}。")
    print(f"   对 Agent 说：加载 zsk skill，构建知识库。")


def cmd_obsidian_export(kb: KnowledgeBase, args):
    """导出 Obsidian vault（.md/.canvas/.base）。"""
    from kb_obsidian import generate_vault

    vault_dir = Path(args.output) if args.output else (PROJECT_DIR / "vault")

    if vault_dir.exists() and any(vault_dir.iterdir()) and not args.force and not args.incremental:
        print(f"⚠️ {vault_dir} 已有内容。使用 --force 覆盖，或 --incremental 增量更新。")
        return

    stats = generate_vault(kb, vault_dir, incremental=args.incremental)
    print(f"✅ Obsidian vault 已导出: {vault_dir.resolve()}")
    print(f"   新增: {stats['created']}  更新: {stats['updated']}  跳过: {stats['skipped']}")
    print(f"   用 Obsidian 打开 vault/ 文件夹即可查看关系图谱。")


def cmd_uninstall(kb: KnowledgeBase, args):
    """卸载 skills + 可选移除 pip 依赖。"""
    import subprocess

    platforms = ["opencode", "hermes"]
    total = 0
    for platform in platforms:
        count = uninstall_skills(platform)
        name = {"opencode": "Open Code", "hermes": "Hermes"}.get(platform, platform)
        if count:
            print(f"   ✅ {name}: 已移除 {count} 个 skill")
        total += count

    if total == 0:
        print("   未找到已安装的 skills")

    if args.all:
        print()
        print("📦 卸载 pip 依赖...")
        for pkg in ["markdown", "PyPDF2", "python-docx"]:
            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", pkg, "-y", "-q"],
                capture_output=True,
            )
        print("   ✅ pip 依赖已移除")

    print(f"\n✅ 卸载完成，共移除 {total} 个 skill")


def cmd_all(kb: KnowledgeBase, args):
    """一键完整流程：build → 提示后续步骤。"""
    print("=" * 60)
    print("🚀 zsk 一键构建")
    print("=" * 60)
    print()

    # Step 1: build
    print("📊 分析文档...\n")
    cmd_build(kb, args)
    print()

    # 指引后续步骤
    print("=" * 60)
    print("✅ 分析报告如上。")
    print()
    print("   后续步骤（由 Agent 自动完成，或手动执行）：")
    print(f"   1. 语义分析每个概念 → kb.py add / kb.py edit")
    print(f"   2. {sys.executable} {PROJECT_DIR}/kb.py reorganize")
    print(f"   3. {sys.executable} {PROJECT_DIR}/kb.py dedup")
    print(f"   4. {sys.executable} {PROJECT_DIR}/kb.py obsidian-export")
    print()
    print("   💡 或直接对 Agent 说：加载 zsk skill，构建知识库。")
    print("=" * 60)


def _interactive_import(kb: KnowledgeBase, args):
    """交互式导入：先预览，逐条确认（默认合并模式）。"""
    from kb_import import import_md, import_and_merge

    filepath = Path(args.path)
    if not filepath.is_file():
        print(f"❌ 文件不存在: {args.path}")
        return

    nodes = import_md(filepath, default_category=args.category or "")
    if not nodes:
        print("未提取到知识点。")
        return

    print(f"\n📄 {filepath.name} → 提取到 {len(nodes)} 个节点（将合并入已有知识树）:\n")
    for i, n in enumerate(nodes, 1):
        cat = ONTOLOGY.get(n.category, {}).get("label", n.category) if n.category else "-"
        existing = kb.find_by_title_category(n.title, n.category) if n.category else None
        action = "合并" if existing else "新增"
        print(f"  [{i}] {action:4s} {'⭐' * n.priority} [{cat}] {n.title}")
        if n.abstract:
            print(f"      {n.abstract[:100]}")
        print()

    while True:
        resp = input("导入全部（合并模式）？[Y]es / [n]o 逐条选择 / [q]uit: ").strip().lower()
        if resp in ("", "y", "yes"):
            stats = import_and_merge(kb, filepath, default_category=args.category or "")
            print(f"✅ 合并 {stats['merged']}, 新增 {stats['new']}, 跳过 {stats['skipped']}")
            return
        elif resp in ("n", "no"):
            selected_ids = []
            for i, n in enumerate(nodes, 1):
                ans = input(f"  导入 [{i}] {n.title}? [y/N]: ").strip().lower()
                if ans in ("y", "yes"):
                    selected_ids.append(n.id)
            # 只合并选中的节点
            for n in nodes:
                if n.id not in selected_ids:
                    continue
                existing = kb.find_by_title_category(n.title, n.category) if n.category else None
                if existing:
                    kb.merge_node(n)
                    print(f"  已合并: {n.title}")
                else:
                    kb.nodes[n.id] = n
                    if n.parent_id and n.parent_id in kb.nodes:
                        if n.id not in kb.nodes[n.parent_id].children:
                            kb.nodes[n.parent_id].children.append(n.id)
                    print(f"  已新增: {n.title}")
            kb._save()
            print(f"✅ 完成")
            return
        elif resp in ("q", "quit"):
            print("已取消")
            return
        else:
            print("请输入 y / n / q")


def main():
    parser = argparse.ArgumentParser(
        description="Agent 开发技术知识库 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python kb.py list                              # 列出所有知识点
  python kb.py list --category architecture      # 按分类筛选
  python kb.py search "ReAct"                    # 搜索
  python kb.py show abc123                       # 查看详情
  python kb.py stats                             # 统计
  python kb.py import reports/agent-技术研报.md   # 导入研报
  python kb.py import reports/agent-技术研报.md --interactive  # 交互式导入
  python kb.py import reports/ --dry-run         # 试运行文件夹导入
  python kb.py export                            # 导出 HTML
  python kb.py add --title "新知识点" --category architecture --priority 2
  python kb.py edit abc123 --priority 1
  python kb.py delete abc123
        """,
    )
    sub = parser.add_subparsers(dest="command")

    # list
    p = sub.add_parser("list", help="列出知识点")
    p.add_argument("--category", "-c")
    p.add_argument("--tag", "-t")
    p.add_argument("--priority", "-p", type=int, choices=[1, 2, 3, 4, 5])
    p.add_argument("--limit", "-n", type=int)
    p.add_argument("--verbose", "-v", action="store_true")

    # search
    p = sub.add_parser("search", help="全文搜索")
    p.add_argument("keyword")

    # show
    p = sub.add_parser("show", help="查看详情")
    p.add_argument("id")

    # stats
    sub.add_parser("stats", help="统计信息")

    # add
    p = sub.add_parser("add", help="手动添加知识点")
    p.add_argument("--id")
    p.add_argument("--title", required=True)
    p.add_argument("--abstract")
    p.add_argument("--content")
    p.add_argument("--priority", type=int, choices=[1, 2, 3, 4, 5])
    p.add_argument("--tags")
    p.add_argument("--category")
    p.add_argument("--l2")
    p.add_argument("--parent")
    p.add_argument("--source")
    p.add_argument("--section")

    # edit
    p = sub.add_parser("edit", help="编辑知识点")
    p.add_argument("id")
    p.add_argument("--title")
    p.add_argument("--abstract")
    p.add_argument("--content")
    p.add_argument("--priority", type=int, choices=[1, 2, 3, 4, 5])
    p.add_argument("--tags")
    p.add_argument("--category")
    p.add_argument("--l2")
    p.add_argument("--parent")
    p.add_argument("--source")
    p.add_argument("--section")

    # delete
    p = sub.add_parser("delete", help="删除知识点")
    p.add_argument("id")
    p.add_argument("--cascade", action="store_true", help="级联删除子节点")

    # import
    p = sub.add_parser("import", help="从 MD 研报导入（默认合并模式）")
    p.add_argument("path", help="MD 文件或目录")
    p.add_argument("--category", "-c", help="默认分类")
    p.add_argument("--dry-run", action="store_true", help="试运行（不写入）")
    p.add_argument("--interactive", "-i", action="store_true", help="交互式逐条确认")
    p.add_argument("--no-merge", action="store_true", help="禁用合并：每份报告独立成树")

    # export
    p = sub.add_parser("export", help="导出 HTML")
    p.add_argument("--output", "-o", help="输出路径，默认 output/knowledge_base.html")

    # setup
    p = sub.add_parser("setup", help="在新机器上注册 skills")
    p.add_argument("--platform", "-p", choices=["opencode", "hermes", "all"],
                   help="指定目标平台（默认自动检测所有可用平台）")

    # reorganize
    sub.add_parser("reorganize", help="重建分类树层级：主根 → 分类 → 概念")

    # dedup
    sub.add_parser("dedup", help="合并归一化标题相同的重复节点")

    # build
    sub.add_parser("build", help="读取研报并输出结构化分析，供 Agent 智能构建知识库")

    # obsidian-export
    p = sub.add_parser("obsidian-export", help="导出 Obsidian vault（.md/.canvas/.base）")
    p.add_argument("--output", "-o", help="输出路径，默认 vault/")
    p.add_argument("--force", "-f", action="store_true", help="覆盖已有 vault")
    p.add_argument("--incremental", "-i", action="store_true", help="增量更新（跳过已有笔记）")

    # uninstall
    p = sub.add_parser("uninstall", help="卸载 skills")
    p.add_argument("--all", action="store_true", help="同时卸载 pip 依赖")

    # all
    sub.add_parser("all", help="一键分析文档并输出指引")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    kb = KnowledgeBase(PROJECT_DIR / "data" / "knowledge_base.json")

    commands = {
        "list": cmd_list,
        "search": cmd_search,
        "show": cmd_show,
        "stats": cmd_stats,
        "add": cmd_add,
        "edit": cmd_edit,
        "delete": cmd_delete,
        "import": cmd_import,
        "export": cmd_export,
        "setup": cmd_setup,
        "reorganize": cmd_reorganize,
        "dedup": cmd_dedup,
        "build": cmd_build,
        "obsidian-export": cmd_obsidian_export,
        "uninstall": cmd_uninstall,
        "all": cmd_all,
    }

    if args.command in commands:
        if args.command == "import" and getattr(args, "interactive", False):
            _interactive_import(kb, args)
        else:
            commands[args.command](kb, args)


if __name__ == "__main__":
    main()
