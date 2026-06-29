@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "DIR=%~dp0"
cd /d "%DIR%"

echo ============================================
echo   🚀 zsk 知识库 — 一键构建
echo ============================================
echo.

REM 检测文档
set HAS_DOCS=0
for %%x in (md markdown pdf docx html htm txt) do (
    if exist "%DIR%reports\*.%%x" set HAS_DOCS=1
)
if %HAS_DOCS% EQU 0 (
    echo ❌ reports\ 文件夹下没有文档
    echo    支持的格式: .md / .pdf / .docx / .html / .txt
    echo    请先将文档放入 reports\ 文件夹
    pause
    exit /b 1
)
echo ✅ 检测到文档

REM 检测 Agent（优先 Open Code）
set AGENT=
set AGENT_CMD=

where opencode >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set AGENT=Open Code
    set AGENT_CMD=opencode -z "加载 zsk skill，构建知识库。" --skills zsk
    goto :found
)

where hermes >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set AGENT=Hermes
    set AGENT_CMD=hermes -z "加载 zsk skill，构建知识库。" --skills zsk
    goto :found
)

REM 无 Agent
echo.
echo ⚠️ 未检测到 Open Code 或 Hermes
echo.
echo 请复制以下命令到你的 Agent 对话框：
echo ========================================
echo   加载 zsk skill，构建知识库。
echo ========================================
echo.
pause
exit /b 0

:found
echo 🧠 使用 !AGENT! 进行语义构建...
echo.
!AGENT_CMD!

echo.
echo ========================================
echo   ✅ 构建完成！
echo   📂 用 Obsidian 打开 vault\ 文件夹即可查看知识图谱
echo ========================================
pause
