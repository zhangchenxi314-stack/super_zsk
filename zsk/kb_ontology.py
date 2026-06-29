"""
知识库本体论定义。
支持动态本体：优先从 ontology_config.json 加载，否则使用默认 Agent 分类。
"""
from __future__ import annotations

import json
from pathlib import Path


# ── 默认本体（Agent 开发领域，作为种子/回退） ───────────

_DEFAULT_ONTOLOGY: dict[str, dict] = {
    "architecture": {
        "label": "架构设计",
        "description": "Agent 系统架构、核心能力要素、框架设计",
        "l2": [
            "single-agent",
            "multi-agent",
            "hybrid",
            "framework-compare",
            "core-capabilities",
            "infrastructure",
        ],
    },
    "planning": {
        "label": "规划与推理",
        "description": "Agent 的任务规划、推理链、决策策略",
        "l2": [
            "react",
            "plan-execute",
            "tree-of-thought",
            "cot",
            "reflection",
            "routing",
        ],
    },
    "tool-calling": {
        "label": "工具调用",
        "description": "Function Calling、MCP、工具选择与编排",
        "l2": [
            "function-calling",
            "mcp",
            "tool-selection",
            "tool-orchestration",
            "api-integration",
        ],
    },
    "memory": {
        "label": "记忆系统",
        "description": "短期/长期记忆、向量检索、上下文管理",
        "l2": [
            "short-term",
            "long-term",
            "vector-retrieval",
            "context-window",
            "memory-consolidation",
        ],
    },
    "multi-agent": {
        "label": "多智能体协作",
        "description": "多 Agent 角色分工、通信、编排",
        "l2": [
            "role-assignment",
            "communication",
            "task-orchestration",
            "debate",
            "swarm",
        ],
    },
    "rag": {
        "label": "RAG 与知识增强",
        "description": "检索增强生成、分块、重排序、索引",
        "l2": [
            "retrieval-strategy",
            "chunking",
            "reranking",
            "embedding",
            "indexing",
            "hybrid-search",
        ],
    },
    "evaluation": {
        "label": "评估与评测",
        "description": "Benchmark、评测方法、质量度量",
        "l2": [
            "benchmark",
            "human-eval",
            "llm-as-judge",
            "metrics",
            "safety-eval",
        ],
    },
    "safety": {
        "label": "安全与对齐",
        "description": "护栏、RLHF/DPO、红队测试",
        "l2": [
            "guardrails",
            "rlhf-dpo",
            "red-teaming",
            "prompt-injection",
            "content-filtering",
        ],
    },
}

# ── 默认标签规范 ──────────────────────────────────────

PREDEFINED_TAGS: list[str] = [
    "llm", "gpt", "claude", "gemini", "llama",
    "langchain", "langgraph", "autogen", "crewai", "semantic-kernel",
    "openai", "anthropic", "google",
    "prompt-engineering", "fine-tuning", "zero-shot", "few-shot",
    "streaming", "async", "state-machine", "dag",
    "beginner", "intermediate", "advanced",
    "tutorial", "paper", "benchmark", "case-study", "overview",
    "trend", "best-practice",
]

# ── 优先级定义（通用，不随领域变化） ──────────────────────

PRIORITY_LEVELS: dict[int, dict[str, str]] = {
    1: {"label": "核心基础", "color": "#d32f2f", "bg": "#ffebee",
        "description": "必须掌握的基础知识"},
    2: {"label": "重要常用", "color": "#f57c00", "bg": "#fff3e0",
        "description": "日常开发常用"},
    3: {"label": "一般了解", "color": "#fbc02d", "bg": "#fffde7",
        "description": "建议了解"},
    4: {"label": "进阶深入", "color": "#1976d2", "bg": "#e3f2fd",
        "description": "深入探索"},
    5: {"label": "扩展选读", "color": "#757575", "bg": "#f5f5f5",
        "description": "按需查阅"},
}

# ── 旧版章节映射（Agent 领域参考，新领域可用 discover 覆盖） ──

SECTION_TO_CATEGORY: dict[str, str | None] = {
    "概述": None,
    "ai agent核心能力要素": "architecture",
    "aiagent核心能力要素": "architecture",
    "agent核心能力要素": "architecture",
    "核心能力要素": "architecture",
    "主流开发框架对比": "architecture",
    "开发框架对比": "architecture",
    "工具调用技术": "tool-calling",
    "工具调用": "tool-calling",
    "rag检索增强生成": "rag",
    "rag": "rag",
    "检索增强生成": "rag",
    "记忆系统": "memory",
    "基础设施演进": "architecture",
    "技术演进趋势总结": "architecture",
    "技术趋势总结": "architecture",
    "参考文献": None,
}


# ── 动态本体加载 ──────────────────────────────────────

# 模块级缓存的当前本体和元信息
_current_ontology: dict | None = None
_current_domain: str = ""
_current_domain_label: str = ""
_config_path: Path | None = None


def load_ontology(config_path: str | Path | None = None) -> dict:
    """
    加载本体配置。优先级：config_path > 默认路径 > 默认 Agent 本体。

    配置文件格式:
    {
      "domain": "medical",
      "domain_label": "医学知识",
      "categories": {
        "cardiology": {"label": "心脏病学", "description": "...", "l2": [...]},
        ...
      }
    }

    返回 category_id → {label, description, l2} 的字典。
    """
    global _current_ontology, _current_domain, _current_domain_label, _config_path

    if config_path is None:
        # 默认路径：项目 data/ 目录
        import sys
        from pathlib import Path
        # 尝试找到项目根目录
        try:
            from kb_core import KnowledgeBase  # 避免循环导入，仅用于定位
        except Exception:
            pass
        # 简化的路径检测
        project_dir = Path(__file__).resolve().parent
        config_path = project_dir / "data" / "ontology_config.json"

    config_path = Path(config_path)

    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            cats = data.get("categories", {})
            if cats:
                _current_ontology = cats
                _current_domain = data.get("domain", "")
                _current_domain_label = data.get("domain_label", "")
                _config_path = config_path
                return cats
        except (json.JSONDecodeError, KeyError):
            pass

    # 回退到默认
    _current_ontology = dict(_DEFAULT_ONTOLOGY)
    _current_domain = "agent-development"
    _current_domain_label = "Agent 开发技术"
    _config_path = config_path
    return dict(_DEFAULT_ONTOLOGY)


def save_ontology(
    categories: dict,
    domain: str = "",
    domain_label: str = "",
    config_path: str | Path | None = None,
) -> Path:
    """
    保存本体配置到 JSON 文件。
    返回保存的文件路径。
    """
    global _current_ontology, _current_domain, _current_domain_label, _config_path

    if config_path is None:
        if _config_path is not None:
            config_path = _config_path
        else:
            config_path = Path(__file__).resolve().parent / "data" / "ontology_config.json"

    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "domain": domain or _current_domain,
        "domain_label": domain_label or _current_domain_label,
        "categories": categories,
    }
    config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 更新缓存
    _current_ontology = categories
    _current_domain = data["domain"]
    _current_domain_label = data["domain_label"]
    _config_path = config_path

    return config_path


def get_ontology() -> dict:
    """返回当前本体（自动加载）。"""
    global _current_ontology
    if _current_ontology is None:
        return load_ontology()
    return _current_ontology


def get_domain() -> str:
    """返回当前领域 ID。"""
    global _current_domain
    if not _current_domain:
        load_ontology()
    return _current_domain


def get_domain_label() -> str:
    """返回当前领域标签。"""
    global _current_domain_label
    if not _current_domain_label:
        load_ontology()
    return _current_domain_label


def is_custom_ontology() -> bool:
    """是否使用了自定义本体（非默认 Agent 分类）。"""
    return _config_path is not None and _config_path.exists()


def reset_to_default():
    """重置为默认 Agent 本体（删除自定义配置，恢复默认）。"""
    global _current_ontology, _current_domain, _current_domain_label
    _current_ontology = dict(_DEFAULT_ONTOLOGY)
    _current_domain = "agent-development"
    _current_domain_label = "Agent 开发技术"
    # 删除自定义配置文件
    if _config_path is not None and _config_path.exists():
        _config_path.unlink()


# ── 兼容旧代码的模块级别名 ──────────────────────────────

# ONTOLOGY 现在是动态的。为保证旧代码兼容，模块加载时自动初始化。
ONTOLOGY = load_ontology()


def reload_ontology(config_path: str | Path | None = None):
    """强制重新加载本体配置（用于 setup/discover 后刷新）。"""
    global ONTOLOGY
    ONTOLOGY = load_ontology(config_path)


# ── 工具函数 ──────────────────────────────────────────

def get_category(cat_id: str) -> dict | None:
    """根据分类 ID 获取分类信息。"""
    return ONTOLOGY.get(cat_id)


def get_l2_label(cat_id: str, l2_id: str) -> str:
    """获取二级分类的可读标签。"""
    return l2_id.replace("-", " ").title()


def get_priority_info(level: int) -> dict:
    """获取优先级配置。"""
    return PRIORITY_LEVELS.get(level, PRIORITY_LEVELS[5])


def map_section_to_category(section_title: str) -> str | None:
    """
    将研报章节标题映射到本体分类 ID。
    返回 None 表示不自动归类。
    """
    key = section_title.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    return SECTION_TO_CATEGORY.get(key)
