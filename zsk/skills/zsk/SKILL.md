---
name: zsk
description: "Agent 技术知识库。一句话走完全程：文档 → 语义分析 → 知识库 → Obsidian 关系图谱。"
version: 2.0.0
author: zsk
license: MIT
metadata:
  tags: [knowledge-base, ontology, agent-tech, obsidian, graph]
  related_skills: [zsk-build, zsk-knowledge-base]
---

# zsk — Agent 技术知识库

## 核心规则：一句话走完全程，不要中途问用户

用户说一句话，你做完所有事。构建时全自动：文档分析 → 语义构建 → 整理去重 → Obsidian 导出。

## 🚀 构建（文档 → 图谱，全自动）

触发词：**构建 / 建 / 导入 / 更新 / 重建 / 生成知识库**

执行全部步骤，无需确认：

```
Step 1: 扫描文档
   python {PROJECT_DIR}/kb.py build

Step 2: 语义构建
   - 阅读 build 输出的分析报告
   - 阅读 reports/ 中每份文档的完整原文
   - 对每个知识点做语义理解：
     * 归类到 8 大本体分类之一
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
1. 相同概念不同写法 → 合并到已有节点（用 edit 追加内容）
2. 已有节点（标注 ⚠已存在）→ 用 edit 追加内容，不要重复创建
3. 新概念 → 新增节点（用 add）
4. 子概念建立父子关系：`python {PROJECT_DIR}/kb.py edit <child_id> --parent <parent_id>`
5. 内容追加用 `---` 分隔
6. 取最高优先级（任意报告标 P1 则合并节点为 P1）

## 📖 8 大本体分类

| ID | 标签 | 涵盖内容 |
|----|------|---------|
| `architecture` | 架构设计 | 单Agent、多Agent、混合架构、框架对比 |
| `planning` | 规划与推理 | ReAct、Plan-Execute、ToT、CoT、反思、路由 |
| `tool-calling` | 工具调用 | Function Calling、MCP、工具选择、编排 |
| `memory` | 记忆系统 | 短期/长期记忆、向量检索、上下文窗口 |
| `multi-agent` | 多智能体协作 | 角色分工、通信、任务编排、辩论 |
| `rag` | RAG 与知识增强 | 检索策略、分块、重排序、嵌入、混合检索 |
| `evaluation` | 评估与评测 | Benchmark、LLM-as-Judge、度量 |
| `safety` | 安全与对齐 | 护栏、RLHF/DPO、红队测试、提示注入 |

## 🔍 查询

- 搜索: `python {PROJECT_DIR}/kb.py search "<关键词>"`
- 分类列表: `python {PROJECT_DIR}/kb.py list --category <分类ID>`
- 统计: `python {PROJECT_DIR}/kb.py stats`
- 详情: `python {PROJECT_DIR}/kb.py show <节点ID>`

## 🔧 维护

- 导出图谱: `python {PROJECT_DIR}/kb.py obsidian-export --force`
- 增量更新: `python {PROJECT_DIR}/kb.py obsidian-export --incremental`
- 修复整理: `python {PROJECT_DIR}/kb.py reorganize && python {PROJECT_DIR}/kb.py dedup && python {PROJECT_DIR}/kb.py obsidian-export --force`
- 打开图谱: 提示用户用 Obsidian 打开 `{PROJECT_DIR}/vault/`

## ⚠️ 处理非 MD 格式文档（PDF/DOCX/HTML/TXT）

这些文档没有 Markdown 标题结构。直接阅读全文内容，做语义理解和概念提取。将提取的概念按 8 个本体分类归类，相同的概念合并。不需要依赖标题层级。

## Windows 用户

- 安装: 双击 `install.bat`
- 构建: 双击 `build.bat`
- 卸载: 双击 `uninstall.bat`

如果双击脚本无效，手动执行：
```
pip install markdown
python kb.py setup
```
然后对 Agent 说：**加载 zsk skill，构建知识库。**
