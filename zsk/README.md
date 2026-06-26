# zsk — Agent 技术知识库

将任意格式文档（MD/PDF/DOCX/HTML/TXT）自动转化为 Obsidian 知识图谱——一句话走完全程。

## 快速开始

```
Windows 三步上手:
  1. 双击 install.bat        ← 自动搞定一切
  2. 把文档扔进 reports\      ← 任意格式 .md .pdf .docx .html .txt
  3. 双击 build.bat          ← 自动构建 + 导出图谱

对 Agent 说:
  加载 zsk skill，构建知识库。

查看结果:
  Obsidian → 打开 vault\ 文件夹 → 关系图谱自动呈现
```

## 核心功能

- **多格式文档** — 支持 MD/PDF/DOCX/HTML/TXT，无标题的纯文本也能自动分块
- **LLM 语义构建** — Agent 理解文档内容，精准分类合并，超越规则匹配
- **Obsidian 关系图谱** — 导出为 Obsidian vault，wikilink 自动渲染关系网络
- **人+AI 可读可编辑** — 每个知识点一个 .md 文件，YAML frontmatter 结构化字段
- **一句话走完全程** — `zsk` skill：文档 → 语义分析 → 知识库 → 图谱，全自动
- **跨平台可移植** — 复制文件夹即用，双击脚本一键完成
- **最小依赖** — 核心仅 `markdown` 一个库，PDF/DOCX 解析器按需安装

## 8 大本体分类

| 分类 ID | 标签 | 涵盖内容 |
|---------|------|---------|
| `architecture` | 架构设计 | 单Agent、多Agent、混合架构、框架对比 |
| `planning` | 规划与推理 | ReAct、Plan-Execute、ToT、CoT、反思、路由 |
| `tool-calling` | 工具调用 | Function Calling、MCP、工具选择、编排 |
| `memory` | 记忆系统 | 短期/长期记忆、向量检索、上下文窗口 |
| `multi-agent` | 多智能体协作 | 角色分工、通信、任务编排、辩论 |
| `rag` | RAG 与知识增强 | 检索策略、分块、重排序、嵌入、混合检索 |
| `evaluation` | 评估与评测 | Benchmark、LLM-as-Judge、度量 |
| `safety` | 安全与对齐 | 护栏、RLHF/DPO、红队测试、提示注入 |

## 三种使用方式

### 方式一：双击脚本（零门槛）

| 操作 | 文件 |
|------|------|
| 首次安装 | `install.bat` |
| 构建知识库 | `build.bat` |
| 卸载 | `uninstall.bat` |

### 方式二：对 Agent 说话

> 加载 zsk skill，构建知识库。
> 加载 zsk skill，搜索 MCP 相关内容。
> 加载 zsk skill，看看知识库统计。

### 方式三：命令行

```bash
python kb.py build              # 分析文档
python kb.py search "MCP"       # 搜索
python kb.py stats              # 统计
python kb.py obsidian-export    # 导出 Obsidian vault
python kb.py all                # 一键流程
```

## 文档格式支持

| 格式 | 依赖 | 说明 |
|------|------|------|
| .md / .txt | 无需安装 | 标准库直接读取 |
| .html | 无需安装 | 自动去标签提取正文 |
| .pdf | `pip install PyPDF2` | PDF 文本提取 |
| .docx | `pip install python-docx` | Word 文本提取 |

非标准格式（无标题层级）会自动检测结构、智能分块，然后交给 Agent 逐块语义分析。

## CLI 命令参考

| 命令 | 用途 |
|------|------|
| `build` | 分析 reports/ 文档，输出结构化报告 |
| `search <kw>` | 全文搜索 |
| `list` | 列出知识点（--category / --tag / --priority） |
| `show <id>` | 查看节点详情 |
| `stats` | 统计信息 |
| `add` | 手动添加知识点 |
| `edit <id>` | 编辑已有节点 |
| `delete <id>` | 删除节点 |
| `export` | 导出 HTML 可视化 |
| `obsidian-export` | 导出 Obsidian vault（.md/.canvas/.base） |
| `reorganize` | 重建分类树 |
| `dedup` | 去重合并 |
| `setup` | 注册 skills 到 Agent |
| `uninstall` | 卸载 skills |
| `all` | 一键完整流程 |

## 项目结构

```
zsk/
├── kb.py                    # CLI 入口（17 命令）
├── kb_core.py               # 数据模型 + CRUD + 合并 + 分类树
├── kb_ontology.py           # 8 分类定义 + 优先级 + 标签
├── kb_import.py             # 文档解析 + 合并导入
├── kb_export.py             # HTML 可视化
├── kb_doc_reader.py         # 多格式文档读取 + 智能分块
├── kb_agent.py              # Agent 平台适配（Open Code / Hermes）
├── kb_obsidian.py           # Obsidian vault 生成器
├── skills/
│   ├── zsk/SKILL.md         # 统一入口（用户只需知道这个）
│   ├── zsk-build/SKILL.md   # 构建子流程
│   └── zsk-knowledge-base/SKILL.md  # 查询子流程
├── reports/                 # 文档输入目录
│   └── EXAMPLE.md           # 研报格式模板
├── data/
│   └── knowledge_base.json  # JSON 知识库
├── vault/                   # Obsidian vault 输出
├── output/                  # HTML 输出
├── build.bat / build.sh     # 一键构建脚本
├── install.bat              # 一键安装
├── uninstall.bat            # 一键卸载
└── README.md
```

## 依赖

**运行环境：** Python 3.9+

**核心依赖：** `pip install markdown`（install.bat 自动安装）

**可选依赖：**
- PDF 支持：`pip install PyPDF2`
- DOCX 支持：`pip install python-docx`

其余全部使用 Python 标准库。

**外部系统：** Open Code（优先）或 Hermes Agent（兼容）

## 故障排查

| 现象 | 解决 |
|------|------|
| Agent 找不到 kb.py | `python kb.py setup` 重新注册 |
| 缺少 markdown | `pip install markdown` |
| PDF 无法读取 | `pip install PyPDF2` |
| DOCX 无法读取 | `pip install python-docx` |
| 中文乱码（Windows） | `chcp 65001` |
| 知识树杂乱 | `python kb.py reorganize` |
