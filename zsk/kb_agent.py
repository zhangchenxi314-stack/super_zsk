"""
Agent 平台适配器。
检测可用 Agent（Open Code > Hermes），管理 skill 安装与卸载。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


# 平台配置：优先级从高到低
PLATFORMS: dict[str, dict] = {
    "opencode": {
        "name": "Open Code",
        "cli": "opencode",
        "skills_dir": "~/.open-code/skills/note-taking",
        "skill_type": "note-taking",
    },
    "hermes": {
        "name": "Hermes",
        "cli": "hermes",
        "skills_dir": "~/.hermes/skills/note-taking",
        "skill_type": "note-taking",
    },
}


def detect_agents() -> list[str]:
    """
    检测当前机器上可用的 Agent 平台。
    返回列表（按优先级排序），如 ['opencode', 'hermes']。
    """
    available: list[str] = []
    for platform_id, cfg in PLATFORMS.items():
        cli = cfg["cli"]
        try:
            # Windows: where, Unix: which
            if Path("/usr/bin/which").exists() or Path("/bin/which").exists():
                result = subprocess.run(
                    ["which", cli], capture_output=True, text=True
                )
            else:
                result = subprocess.run(
                    ["where", cli], capture_output=True, text=True, shell=True
                )
            if result.returncode == 0 and result.stdout.strip():
                available.append(platform_id)
                continue
        except Exception:
            pass

        # 回退：检查 skills 目录是否存在（已安装但 CLI 不在 PATH 中）
        skills_dir = Path(cfg["skills_dir"]).expanduser()
        if skills_dir.exists():
            available.append(platform_id)

    return available


def get_primary_agent() -> str | None:
    """返回优先级最高的可用 Agent，不存在则返回 None。"""
    agents = detect_agents()
    return agents[0] if agents else None


def get_skills_dir(platform: str) -> Path | None:
    """返回指定平台的 skills 安装目录。"""
    cfg = PLATFORMS.get(platform)
    if not cfg:
        return None
    return Path(cfg["skills_dir"]).expanduser()


def get_build_command(platform: str) -> str | None:
    """
    返回对应平台的完整构建命令（命令行调用方式）。
    """
    cfg = PLATFORMS.get(platform)
    if not cfg:
        return None
    cli = cfg["cli"]
    return f'{cli} -z "加载 zsk skill，构建知识库。" --skills zsk'


def get_install_message() -> str:
    """
    返回给用户的 Agent 安装提示。
    根据检测结果，给出具体指引。
    """
    agents = detect_agents()
    if agents:
        parts = [PLATFORMS[a]["name"] for a in agents]
        return f"✅ 检测到: {', '.join(parts)}"

    return (
        "⚠️ 未检测到 Open Code 或 Hermes Agent。\n"
        "   请先安装 Agent 工具：\n"
        "   Open Code: https://opencode.ai\n"
        "   Hermes: 请联系管理员获取安装包\n\n"
        "   安装后重新运行 install.bat"
    )


def install_skills(platform: str, project_dir: Path) -> int:
    """
    将项目 skills/ 目录下的所有 skill 安装到目标平台。
    替换模板中的 {PROJECT_DIR} 占位符。
    返回安装数量。
    """
    skills_src = project_dir / "skills"
    if not skills_src.is_dir():
        return 0

    skills_dir = get_skills_dir(platform)
    if not skills_dir:
        return 0

    installed = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        src_md = skill_dir / "SKILL.md"
        if not src_md.exists():
            continue

        dst_dir = skills_dir / skill_dir.name
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_md = dst_dir / "SKILL.md"

        # 读取模板，替换占位符
        content = src_md.read_text(encoding="utf-8")
        content = content.replace("{PROJECT_DIR}", str(project_dir))
        dst_md.write_text(content, encoding="utf-8")

        installed += 1

    return installed


def uninstall_skills(platform: str) -> int:
    """
    从目标平台移除所有 zsk skill。
    返回移除数量。
    """
    skills_dir = get_skills_dir(platform)
    if not skills_dir or not skills_dir.exists():
        return 0

    removed = 0
    for skill_name in ("zsk", "zsk-build", "zsk-knowledge-base"):
        skill_dir = skills_dir / skill_name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed += 1

    return removed
