# zsk 使用指南

## 这是什么

zsk 是一个知识库构建工具。你把任意文档扔进去，它自动读、自动理解、自动分类，最后生成一个 Obsidian 关系图谱。整个过程只需要对 Agent 说一句话。

## 三步上手

```
第 1 步：双击 install.bat（仅首次）

第 2 步：把文档扔进 reports/ 文件夹
        支持 .md .pdf .docx .html .txt

第 3 步：双击 build.bat
         或对 Agent 说：加载 zsk skill，构建知识库。
```

完成后用 Obsidian 打开 `vault/` 文件夹，关系图谱自动呈现。

## 什么时候用

| 场景 | 怎么做 |
|------|--------|
| 积累了一批技术文档，想梳理成知识体系 | 文档丢进 reports/ → 双击 build.bat |
| 文档不是 Agent 技术领域，是医学/金融/法律 | 先对 Agent 说「加载 zsk skill，发现本体」，再构建 |
| 知识库已有 100 个节点，今天又来了新文档 | 新文档丢进 reports/ → 双击 build.bat（自动增量合并） |
| 想看某个概念在不在知识库里 | 对 Agent 说「加载 zsk skill，搜索 MCP」 |
| 知识树有点乱，分类不对 | 对 Agent 说「加载 zsk skill，修复知识树」 |
| 想把知识库给别人看 | 把 vault/ 文件夹发给他，他用 Obsidian 打开就行 |
| 想卸载 | 双击 uninstall.bat |
| 不用 Agent，纯命令行 | `python kb.py build` → `python kb.py add ...` |

## 常见场景详解

### 场景 A：首次使用，Agent 技术领域

你的 `reports/` 里有两份 Agent 技术研报，系统自带 Agent 8 分类正好匹配。

```
1. 双击 build.bat
2. Agent 自动：分析文档 → 提取概念 → 归入 8 分类 → 去重 → 导出图谱
3. Obsidian 打开 vault/ → 完成
```

不需要额外操作。默认分类直接可用。

### 场景 B：首次使用，非 Agent 领域

你的 `reports/` 里全是医学文献，默认的「架构设计」「工具调用」这些分类完全对不上。

```
1. 对 Agent 说：加载 zsk skill，发现本体

   Agent 会读完所有医学文献，理解这是「临床医学」领域，
   然后提议分类，比如：
     - cardiology    心脏病学
     - neurology     神经病学
     - pharmacology  药理学
     - pathology     病理学
     ...（5-10 个）

2. Agent 自动写入分类配置

3. 对 Agent 说：构建知识库

   Agent 基于新分类体系重新构建，医学概念归入心脏病学/神经病学等
```

本质区别：系统不再硬编码 Agent 分类，而是先理解你的文档再决定怎么分。

### 场景 C：增量更新

知识库已经建好，你又拿到了三份新文档。

```
1. 新文档丢进 reports/
2. 双击 build.bat

Agent 只处理新文档中的概念：
  - 新概念 → 新建节点
  - 已有概念（如两篇文档都讲了「冠心病」）→ 合并追加，不重复创建
  - 不匹配的概念 → 自动提示是否需要扩展分类
```

不会从头重建，已有知识全部保留。

### 场景 D：文档格式乱七八糟

你的 reports/ 里什么都有：Word 报告、PDF 论文、网页导出的 HTML、纯文本笔记。

```
双击 build.bat 之后，系统自动：

  .docx → python-docx 提取文本
  .pdf  → PyPDF2 提取文本
  .html → 去标签保留正文
  .txt  → 直接读取
  .md   → 正常解析标题层级

  没有标题层级的文档 → 自动智能分块：
    有数字编号（1. 2. 3.）→ 按编号切
    有空行段落 → 按段落组切
    纯长文本 → 按语义边界切

  每块标注来源和位置，交给 Agent 逐块阅读理解
```

你不需要预处理文档，扔进去就行。

### 场景 E：发现分类不准确，想修正

用 Obsidian 浏览图谱时，发现「冠心病」被错误归到了神经病学。

```
方法 1（用 Agent）：
  对 Agent 说：加载 zsk skill，把「冠心病」的分类改成心脏病学
  Agent 执行：python kb.py edit 冠心病id --category cardiology
  → reorganize → obsidian-export

方法 2（手动改文件）：
  打开 vault/02-神经病学/冠心病.md
  修改 frontmatter 中 category: cardiology
  运行 python kb.py obsidian-export --force
```

修改后图谱自动更新。

### 场景 F：纯命令行使用（不用 Agent）

```
# 分析文档
python kb.py build

# 手动逐条添加
python kb.py add --title "冠心病" --category cardiology --priority 1 \
  --abstract "冠状动脉粥样硬化性心脏病" --content "## 病因\n..."

# 建立父子关系
python kb.py edit child_id --parent parent_id

# 整理导出
python kb.py reorganize
python kb.py dedup
python kb.py obsidian-export --force

# 查询
python kb.py search "冠心病"
python kb.py stats
python kb.py list --category cardiology
```

## 输出物说明

构建完成后，`vault/` 目录结构：

```
vault/
├── 01-心脏病学/
│   ├── _心脏病学.md          ← 分类索引
│   ├── 冠心病.md              ← 知识节点（.md 文件 = 人可直接编辑）
│   └── 心律失常.md
├── 02-神经病学/
│   └── ...
├── _index/
│   └── 临床医学总览.md        ← 总索引
├── 知识图谱.canvas            ← Obsidian 画布
├── 知识库.base                ← 数据库视图
└── .obsidian/                 ← 图谱着色配置
```

每个 .md 节点都是标准 Obsidian 笔记，含 YAML 结构化字段和 `[[wikilink]]` 关系链接。

## 卸载

```
双击 uninstall.bat

或命令行：
  python kb.py uninstall          # 仅移除 skills
  python kb.py uninstall --all    # 同时卸载 pip 依赖
```

## 命令速查

| 命令 | 用途 |
|------|------|
| `python kb.py discover` | 扫描文档，让 Agent 发现领域并提议分类 |
| `python kb.py build` | 分析文档，输出报告供 Agent 构建 |
| `python kb.py ontology-set '<json>'` | 设置自定义分类 |
| `python kb.py ontology-show` | 查看当前分类 |
| `python kb.py ontology-reset` | 重置为默认 Agent 分类 |
| `python kb.py add --title ...` | 手动添加知识点 |
| `python kb.py edit <id> ...` | 编辑节点 |
| `python kb.py search <kw>` | 搜索 |
| `python kb.py stats` | 统计 |
| `python kb.py reorganize` | 重建分类树 |
| `python kb.py dedup` | 去重 |
| `python kb.py obsidian-export` | 导出 Obsidian vault |
| `python kb.py export` | 导出 HTML |
| `python kb.py setup` | 注册 skills 到 Agent |
| `python kb.py uninstall` | 卸载 |
