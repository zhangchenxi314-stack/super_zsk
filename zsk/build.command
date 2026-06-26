#!/bin/bash
# ============================================================
# zsk 知识库一键构建脚本 (macOS 双击)
# ============================================================
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "============================================"
echo "  🚀 zsk 知识库 — 一键构建"
echo "============================================"
echo ""

# 检测文档
HAS_DOCS=$(find reports/ -maxdepth 1 -type f \( -name "*.md" -o -name "*.pdf" -o -name "*.docx" -o -name "*.html" -o -name "*.txt" \) 2>/dev/null | head -1)
if [ -z "$HAS_DOCS" ]; then
    echo "❌ reports/ 文件夹下没有文档"
    echo "   支持的格式: .md / .pdf / .docx / .html / .txt"
    exit 1
fi
echo "✅ 检测到文档"

# 检测 Agent（优先 Open Code）
if command -v opencode &>/dev/null; then
    echo "🧠 使用 Open Code 进行语义构建..."
    echo ""
    exec opencode -z "加载 zsk skill，构建知识库。" --skills zsk
elif command -v hermes &>/dev/null; then
    echo "🧠 使用 Hermes 进行语义构建..."
    echo ""
    exec hermes -z "加载 zsk skill，构建知识库。" --skills zsk
else
    echo ""
    echo "⚠️ 未检测到 Open Code 或 Hermes"
    echo ""
    echo "请复制以下命令到你的 Agent 对话框："
    echo "============================================"
    echo "  加载 zsk skill，构建知识库。"
    echo "============================================"
    exit 0
fi
