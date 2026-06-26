@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   📦 zsk 知识库 — 一键安装
echo ============================================
echo.

:: ── 1. 检查 Python ──
echo [1/3] 检查 Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   ❌ 未找到 Python，请先安装 Python 3.9+
    echo   下载地址: https://www.python.org/downloads/
    echo   安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
python --version
echo   ✅ Python 就绪
echo.

:: ── 2. 安装依赖 ──
echo [2/3] 安装依赖...
pip install markdown -q
if %errorlevel% neq 0 (
    echo   ⚠️ markdown 安装失败，请手动执行: pip install markdown
) else (
    echo   ✅ markdown 就绪
)
echo.
echo   📋 可选依赖（按需安装）：
echo      PDF 文档  → pip install PyPDF2
echo      DOCX 文档 → pip install python-docx
echo.

:: ── 3. 注册 skill ──
echo [3/3] 注册 skills...
python "%~dp0kb.py" setup
echo.

echo ============================================
echo   ✅ 安装完成！
echo.
echo   下一步：
echo   1. 把文档放入 reports\ 文件夹
echo   2. 双击 build.bat
echo.
echo   或者对 Agent 说：
echo     加载 zsk skill，构建知识库。
echo ============================================
echo.
pause
