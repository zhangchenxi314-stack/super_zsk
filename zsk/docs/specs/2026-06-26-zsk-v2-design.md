# zsk v2.0 设计文档

**日期**: 2026-06-26  
**版本**: v2.0  
**基于**: zsk v1.4（Agent 技术知识库）

## 一、项目目标

将 zsk 从一个"JSON 知识库 + HTML 可视化"系统升级为"Obsidian Vault 知识库 + 关系图谱可视化"系统，同时大幅降低用户上手成本。

### 核心需求

| 需求 | 说明 |
|------|------|
| 多格式文档读取 | 支持 MD/PDF/DOCX/HTML/TXT，按需加载解析器 |
| LLM 语义分析 | 保持 Hermes Agent + skill 模式，优先适配 Open Code |
| 关系数据库 | Obsidian Vault（.md + YAML frontmatter + wikilinks），人+AI 可读可编辑 |
| 关系图谱可视化 | 原生 Obsidian 图谱 + JSON Canvas + Bases 数据库视图 |
| 零上手成本 | 双击 install.bat → 双击 build.bat → 完成 |
| 快速卸载 | 双击 uninstall.bat 或 `python kb.py uninstall` |
| Windows 可移植 | 复制项目文件夹即用，路径自感知 |
| 最小依赖 | 核心仅 `markdown`，PDF/DOCX 解析器可选按需安装 |

---

## 二、系统架构

### 数据流

```
任意文档（MD/PDF/DOCX/HTML/TXT）
        │
        ▼
  kb_doc_reader.py        ← NEW: 统一文档读取层
  提取纯文本内容
        │
        ▼
  zsk-build skill + LLM   ← 保持：Agent 语义分析（Open Code / Hermes）
  分类/合并/优先级/标签
        │
        ▼
  kb_obsidian.py          ← NEW: Obsidian Vault 生成器
  生成 .md 笔记 + .canvas + .base
        │
        ▼
  vault/                  ← Obsidian 打开即用
  ├── .obsidian/
  ├── 笔记文件 (.md)
  ├── 知识图谱.canvas
  └── 知识库.base
```

### 模块变更

| 模块 | 类型 | 职责 |
|------|------|------|
| `kb_doc_reader.py` | **新增** | 多格式文档 → 纯文本（MD/PDF/DOCX/HTML/TXT） |
| `kb_agent.py` | **新增** | Agent 平台检测与适配（Open Code > Hermes） |
| `kb_obsidian.py` | **新增** | JSON 知识库 → Obsidian vault（.md/.canvas/.base） |
| `kb_import.py` | 修改 | 接入 kb_doc_reader，支持非 MD 格式 |
| `kb.py` | 修改 | 新增命令（obsidian-export/obsidian-build/uninstall/all），setup 适配多 Agent |
| `kb_core.py` | 保持 | 数据模型与 CRUD 不变 |
| `kb_ontology.py` | 保持 | 8 分类体系不变 |
| `kb_export.py` | 保持 | HTML 导出保留 |
| skills | 更新 | 新增 `zsk` 统一入口 skill；zsk-build / zsk-knowledge-base 增加 Obsidian 步骤 |
| `skills/zsk/SKILL.md` | **新增** | 用户唯一需要知道的 skill，一句话走完全程 |

---

## 三、新增模块详细设计

### 3.1 kb_doc_reader.py — 文档读取层

**职责**: 统一的文档 → 纯文本转换，按格式自动路由，按需加载依赖。

**依赖策略**:

| 格式 | 库 | 状态 |
|------|-----|------|
| .md / .txt | 标准库 | ✅ 内置 |
| .html | 标准库 `html.parser` | ✅ 内置 |
| .pdf | `PyPDF2` | ⚠️ 可选（`pip install PyPDF2`） |
| .docx | `python-docx` | ⚠️ 可选（`pip install python-docx`） |

**核心接口**:

```python
def read_document(filepath: Path) -> str:
    """自动检测格式，返回纯文本。不支持时抛出 UnsupportedFormatError。"""

def list_supported_formats() -> dict:
    """返回 {格式: 是否可用}。"""

def check_dependency(format: str) -> bool:
    """检查特定格式的依赖是否已安装。"""
```

**UnsupportedFormatError**: 自定义异常，携带安装提示（如 `pip install PyPDF2`）。

### 3.2 kb_agent.py — Agent 平台适配器

**职责**: 检测可用 Agent 平台，为不同平台生成对应 skill 文件。

**支持的平台**:

| 优先级 | 平台 | 技能目录 | CLI |
|--------|------|---------|-----|
| P1 | Open Code | `~/.open-code/skills/` | `opencode` |
| P2 | Hermes | `~/.hermes/skills/` | `hermes` |
| P3 | 通用 | 项目内 `skills/` | 手动复制 |

**核心接口**:

```python
def detect_agents() -> list[str]:
    """返回可用的 Agent 列表，如 ['opencode', 'hermes']。"""

def install_skills(platform: str, project_dir: Path) -> bool:
    """将 skills/ 目录下的 skill 安装到目标平台。"""

def get_build_command(platform: str) -> str:
    """返回对应平台的构建命令。"""
```

### 3.3 kb_obsidian.py — Obsidian Vault 生成器

**职责**: 从 JSON 知识库生成完整 Obsidian vault。

**Vault 目录结构**:

```
vault/
├── .obsidian/
│   └── app.json              ← 基础配置（图谱颜色、分组）
├── _index/
│   └── 知识库总览.md           ← MOC 总索引
├── 01-架构设计/
│   ├── _架构设计.md            ← 分类索引页
│   ├── AI Agent 核心能力要素.md
│   └── ...
├── 02-规划与推理/ ...
├── ...（8 个分类各一个文件夹）
├── 知识图谱.canvas
└── 知识库.base
```

**每条 .md 笔记结构**:

```markdown
---
id: architecture-xxx
title: 标题
category: architecture
category_label: 架构设计
priority: 2
tags:
  - agent
  - core
source_file: agent-tech-2024.md
created: 2026-06-17
updated: 2026-06-17
---

# 标题

> **优先级**: ⭐ P2 重要常用 | **分类**: 架构设计 | **来源**: agent-tech-2024.md

正文内容...

## 📂 子概念
- [[子笔记A]]
- [[子笔记B]]

## 🔗 相关概念
- [[同类笔记]]
```

**核心接口**:

```python
def generate_vault(kb: KnowledgeBase, vault_dir: Path, incremental: bool = False) -> dict:
    """生成完整 vault。返回 {created, updated, skipped} 统计。"""

def _generate_note(node: KnowledgeNode, vault_dir: Path) -> Path:
    """生成单个 .md 笔记文件。"""

def _generate_moc(kb: KnowledgeBase, vault_dir: Path) -> Path:
    """生成总索引页（MOC）。"""

def _generate_category_index(kb: KnowledgeBase, category_id: str, vault_dir: Path) -> Path:
    """生成分类索引页。"""

def _generate_canvas(kb: KnowledgeBase, vault_dir: Path) -> Path:
    """生成 JSON Canvas 图谱文件。"""

def _generate_base(kb: KnowledgeBase, vault_dir: Path) -> Path:
    """生成 Obsidian Bases 数据库视图。"""
```

**关系 → wikilink 映射**:

| JSON 关系 | Obsidian 表达 |
|-----------|--------------|
| `parent_id` / `children` | 笔记中 `## 📂 子概念` + `[[child]]` |
| 同一 category | 同一文件夹 + 分类索引页 wikilinks |
| 相同 tags | YAML frontmatter `tags:` 字段 |
| source_file 追溯 | 笔记正文顶部来源标注 |

---

## 四、CLI 命令变更

### 新增命令

| 命令 | 说明 |
|------|------|
| `obsidian-export` | 一键导出 Obsidian vault（.md/.canvas/.base） |
| `obsidian-build` | build → obsidian-export 合并（Agent 构建 + 导出一步到位） |
| `all` | 完整流程快捷命令 |
| `uninstall` | 卸载 skills + 可选移除 pip 依赖 |

### 修改命令

| 命令 | 变更 |
|------|------|
| `setup` | 检测 Agent 平台，优先 Open Code；`--platform opencode\|hermes\|all` 参数 |
| `build` | 接入 kb_doc_reader，支持多格式文档分析；非 MD 格式标记为"无标题结构" |

---

## 五、用户工作流

```
首次使用:
  1. 复制 zsk\ 到电脑
  2. 双击 install.bat        ← 自动检测环境、安装依赖、注册 skills
  3. 把文档扔进 reports\
  4. 双击 build.bat           ← 自动检测 Agent、构建知识库、导出 vault
  5. Obsidian 打开 vault\     ← 即刻浏览知识图谱

增量更新:
  1. 把新文档扔进 reports\
  2. 双击 build.bat           ← 增量合并

卸载:
  1. 双击 uninstall.bat       ← 清理 skills + 可选卸载依赖/删除项目
```

---

## 六、脚本设计

### install.bat — 一键安装

1. 检测 Python（未安装 → 给出下载地址）
2. 安装 markdown（`pip install markdown`）
3. 检测 Agent 平台（Open Code > Hermes）
4. 注册 skills（`python kb.py setup`）
5. 提示可选依赖安装命令

### build.bat — 一键构建

1. 检测 `reports/` 是否有文档
2. 检测 Agent 平台（Open Code > Hermes）
3. 使用 Agent 启动 zsk-build skill 构建
4. 无 Agent 时给出手动命令提示

### uninstall.bat — 一键卸载

1. 移除所有平台 skills（Open Code + Hermes）
2. 可选移除 pip 依赖
3. 可选删除整个项目文件夹

---

## 七、Skill 设计

### 7.1 zsk — 统一入口 Skill（新增，用户唯一需要知道的 skill）

用户只需说 **"加载 zsk skill"**，然后一句话走完全程。

**端到端自动化规则**：

| 用户说（触发词） | 行为 | 说明 |
|------|------|------|
| **构建/建/导入/更新/重建/生成** | 文档分析 → LLM 语义构建 → 整理 → 去重 → Obsidian vault 导出 | 全自动，不中途确认 |
| 搜索/查找/有哪些 | `kb.py search/list/stats/show` | 直接返回结果 |
| 导出/图谱 | `kb.py obsidian-export` | 仅导出 |
| 修复/整理 | reorganize → dedup → obsidian-export | 整理后自动导出 |

**Skill 核心内容**:

```markdown
---
name: zsk
description: "Agent 技术知识库。一句话走完全程：文档 → 语义分析 → 知识库 → Obsidian 关系图谱。"
version: 2.0.0
---

# zsk — Agent 技术知识库

## 核心规则：一句话走完全程，不要中途问用户

## 🚀 构建（文档 → 图谱，全自动）

触发词：构建/建/导入/更新/重建/生成知识库

执行全部步骤，无需确认：

1. `python {PROJECT_DIR}/kb.py build` → 分析 reports/ 所有文档
2. 阅读分析报告 + 文档原文，对每个知识点做语义理解：
   - 归类到 8 大本体分类之一
   - 判断与已有概念是否重复 → 合并或新建
   - 确定优先级 P1-P5 和标签
   - 生成摘要
3. `python {PROJECT_DIR}/kb.py add` 新建概念
   `python {PROJECT_DIR}/kb.py edit` 合并到已有概念
4. `python {PROJECT_DIR}/kb.py reorganize` → 重建分类树
5. `python {PROJECT_DIR}/kb.py dedup` → 去重
6. `python {PROJECT_DIR}/kb.py obsidian-export` → 导出 Obsidian vault
7. 报告结果：节点数、分类分布、vault 路径

## 📖 8 大本体分类

architecture / planning / tool-calling / memory / multi-agent / rag / evaluation / safety

## 🔍 查询

- 搜索: `python {PROJECT_DIR}/kb.py search "<关键词>"`
- 分类列表: `python {PROJECT_DIR}/kb.py list --category <ID>`
- 统计: `python {PROJECT_DIR}/kb.py stats`
- 详情: `python {PROJECT_DIR}/kb.py show <节点ID>`

## 🔧 维护

- 导出图谱: `python {PROJECT_DIR}/kb.py obsidian-export`
- 修复整理: reorganize → dedup → obsidian-export
- 打开图谱: 提示用户用 Obsidian 打开 `{PROJECT_DIR}/vault/`
```

**用户使用示例**:

```
用户：加载 zsk skill，构建知识库。
Agent：
  📊 扫描 reports/ 发现 3 份文档...
  🧠 语义分析中...
  ✅ 新增 5 个概念，合并 3 个
  🔗 去重合并完成
  📂 Obsidian vault 已导出
  ==================================
  知识库构建完成！节点: 32 个  深度: 4 层
  用 Obsidian 打开 vault\ 即可查看关系图谱
```

### 7.2 Skill 体系结构

```
用户 → zsk（统一入口，智能路由）
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
zsk-build  zsk-kb   直接 CLI
（构建）   （查询）   （导出/维护）
```

- **zsk**（新增）: 用户唯一需要知道的 skill 名，自然语言智能路由
- **zsk-build**（保持）: 内部构建子流程，可独立调用
- **zsk-knowledge-base**（保持）: 内部查询子流程，可独立调用

### 7.3 zsk-build skill 变更

新增 Step 6 — Obsidian 导出（与 zsk skill 保持一致）。

---

## 八、错误处理与用户提示

所有错误场景提供中文引导，不输出原始堆栈：

| 场景 | 提示 |
|------|------|
| 无 Python | `❌ 请先安装 Python 3.9+（下载地址: https://www.python.org/downloads/）` |
| reports/ 为空 | `❌ 请将文档放入 reports\ 文件夹` |
| PDF 无依赖 | `⚠️ 运行: pip install PyPDF2` |
| Agent 未找到 | `⚠️ 复制以下命令到 Agent：加载 zsk skill，构建知识库。` |
| vault/ 已存在 | `⚠️ vault\ 已有内容，覆盖？[y/N]` |

---

## 九、项目文件结构（v2.0）

```
zsk/
├── kb.py                    🔧 CLI 入口（16 命令）
├── kb_core.py               ✅ 数据模型 + CRUD
├── kb_ontology.py           ✅ 8 分类本体
├── kb_import.py             🔧 MD 解析 + 多格式接入
├── kb_export.py             ✅ HTML 可视化
├── kb_doc_reader.py         ✨ 多格式文档读取
├── kb_agent.py              ✨ Agent 平台适配
├── kb_obsidian.py           ✨ Obsidian vault 生成器
├── skills/
│   ├── zsk/SKILL.md                  ✨ 统一入口（用户唯一需要知道的）
│   ├── zsk-knowledge-base/SKILL.md   🔧 更新
│   └── zsk-build/SKILL.md           🔧 更新
├── vault/                   ✨ Obsidian vault 输出
├── build.bat                🔧 优先 opencode
├── build.sh                 🔧 优先 opencode
├── install.bat              🔧 增加可选依赖提示
├── uninstall.bat            🔧 多平台卸载
├── reports/                 ✅ 文档输入
├── data/knowledge_base.json ✅ JSON 存储
└── output/knowledge_base.html ✅ HTML 输出
```

---

## 十、依赖清单

| 依赖 | 类型 | 安装 |
|------|------|------|
| `markdown` | 核心 | `pip install markdown`（install.bat 自动） |
| `PyPDF2` | 可选 | `pip install PyPDF2`（按需提示） |
| `python-docx` | 可选 | `pip install python-docx`（按需提示） |
| Python 3.9+ | 运行环境 | 预装 |
| Open Code / Hermes | LLM 分析 | 预装 |

---

## 十一、约束与限制

- 核心依赖仅 `markdown` 一个库（纯 Python，无 C 扩展）
- JSON 知识库和 HTML 导出功能完整保留，无破坏性变更
- 非 MD 格式文档（PDF/DOCX）无标题结构，由 LLM 全文字段语义提取
- 8 分类体系保持硬编码，O7 规划中的可配置化不在本次范围
- 全量 JSON 读写机制不变，性能优化不在本次范围
