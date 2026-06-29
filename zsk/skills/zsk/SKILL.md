---
name: zsk
description: "知识库构建工具。自适应文档领域：先分析文档内容，发现本体分类，再构建知识库并导出 Obsidian 关系图谱。"
version: 3.0.0
author: zsk
license: MIT
metadata:
  tags: [knowledge-base, ontology, obsidian, graph, adaptive]
  related_skills: [zsk-build, zsk-knowledge-base]
---

# zsk — 自适应知识库

## 核心规则

用户说一句话，你做完所有事。**关键：不要假设文档领域。先理解文档内容，再做分类。**

## 🔍 发现本体（新知识领域，首次必做）

触发词：**发现 / 本体 / 领域 / 分类 / 分析领域 / discover**

当用户首次使用、文档换领域、或分类不对时，先执行此流程：

```
Step 1: 扫描文档
   python {PROJECT_DIR}/kb.py discover

Step 2: LLM 阅读并提议分类
   - 阅读 reports/ 中每份文档的完整原文
   - 理解这些文档属于什么领域（医学？金融？法律？技术？）
   - 根据文档内容，提出 5-10 个一级分类
   - 每个分类需要：
     * id: 英文短标识（如 "cardiology"）
     * label: 中文标签（如 "心脏病学"）
     * description: 一句话描述
     * l2: 2-5 个二级分类标识（可选）

Step 3: 写入分类配置
   python {PROJECT_DIR}/kb.py ontology-set '{{"domain":"...","domain_label":"...","categories":{{...}}}}'

Step 4: 告诉用户
   "本体分类已设置。现在可以构建知识库了。"
```

**分类设计原则：**
- 从文档内容归纳，不要套用任何预设模板
- 5-10 个一级分类，覆盖文档涉及的主要主题
- 每个分类的 label 用中文，id 用英文小写+连字符
- 如果文档跨领域，分类可以涵盖多个子领域

## 🚀 构建知识库

触发词：**构建 / 建 / 导入 / 更新 / 重建 / 生成知识库**

```
Step 0: 检查本体
   - 运行 python {PROJECT_DIR}/kb.py ontology-show
   - 如果分类体系与文档领域不匹配 → 自动切换到「发现本体」流程
   - 如果仍为默认 Agent 分类且文档不是 Agent 领域 → 自动切换到「发现本体」流程

Step 1: 扫描文档
   python {PROJECT_DIR}/kb.py build

Step 2: 语义构建
   - 阅读 build 输出的分析报告
   - 阅读 reports/ 中每份文档的完整原文
   - 对每个知识点做语义理解：
     * 归类到当前本体分类之一（参考 ontology-show 的输出，不要用旧的 Agent 8 分类）
     * 判断与已有概念是否重复 → 合并或新建
     * 确定优先级 P1-P5 和标签
     * 生成摘要
   - 用 kb.py add 新建概念
   - 用 kb.py edit 合并到已有概念

Step 3: 整理与去重
   python {PROJECT_DIR}/kb.py reorganize
   python {PROJECT_DIR}/kb.py dedup

Step 4: 导出 Obsidian vault
   python {PROJECT_DIR}/kb.py obsidian-export --force

Step 5: 告诉用户结果
   报告：节点总数、各分类分布、vault 路径
   "用 Obsidian 打开 vault\ 文件夹即可查看关系图谱"
```

**语义合并规则：**
1. 相同概念不同写法 → 合并到已有节点（edit 追加内容）
2. 已有节点（标注 ⚠已存在）→ edit 追加，不重复创建
3. 新概念 → add 新建
4. 子概念建立父子关系：`python {PROJECT_DIR}/kb.py edit <child_id> --parent <parent_id>`
5. 内容追加用 `---` 分隔
6. 取最高优先级（任意来源标 P1 则合并节点为 P1）

**⚠️ 关于分类：**
- 用 `python {PROJECT_DIR}/kb.py ontology-show` 查看当前分类
- 不要假设是 Agent 8 分类。每个知识库有自己的分类体系
- 如果一个知识点找不到合适的分类，考虑是否需要提议扩展分类

## 🔍 查询

- 搜索: `python {PROJECT_DIR}/kb.py search "<关键词>"`
- 分类列表: `python {PROJECT_DIR}/kb.py list --category <分类ID>`
- 统计: `python {PROJECT_DIR}/kb.py stats`
- 详情: `python {PROJECT_DIR}/kb.py show <节点ID>`
- 查看分类: `python {PROJECT_DIR}/kb.py ontology-show`

## 🔧 维护

- 导出图谱: `python {PROJECT_DIR}/kb.py obsidian-export --force`
- 增量更新: `python {PROJECT_DIR}/kb.py obsidian-export --incremental`
- 修复整理: `python {PROJECT_DIR}/kb.py reorganize && python {PROJECT_DIR}/kb.py dedup && python {PROJECT_DIR}/kb.py obsidian-export --force`
- 重置分类: `python {PROJECT_DIR}/kb.py ontology-reset`
- 打开图谱: 提示用户用 Obsidian 打开 `{PROJECT_DIR}/vault/`

## ⚠️ 处理非标准文档

非 MD 格式或没有标题层级的文档，系统已自动分块。
直接逐块阅读，做语义理解和概念提取。按当前本体分类归类。

## Windows 用户

- 安装: 双击 `install.bat`
- 构建: 双击 `build.bat`
- 卸载: 双击 `uninstall.bat`
