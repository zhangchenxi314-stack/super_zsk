@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   🗑 zsk 知识库 — 一键卸载
echo ============================================
echo.

set REMOVED=0

:: ── 清理 Open Code skills ──
if exist "%USERPROFILE%\.open-code\skills\note-taking\zsk" (
    rmdir /s /q "%USERPROFILE%\.open-code\skills\note-taking\zsk"
    echo   ✅ Open Code: zsk
    set /a REMOVED+=1
)
if exist "%USERPROFILE%\.open-code\skills\note-taking\zsk-build" (
    rmdir /s /q "%USERPROFILE%\.open-code\skills\note-taking\zsk-build"
    echo   ✅ Open Code: zsk-build
    set /a REMOVED+=1
)
if exist "%USERPROFILE%\.open-code\skills\note-taking\zsk-knowledge-base" (
    rmdir /s /q "%USERPROFILE%\.open-code\skills\note-taking\zsk-knowledge-base"
    echo   ✅ Open Code: zsk-knowledge-base
    set /a REMOVED+=1
)

:: ── 清理 Hermes skills ──
if exist "%USERPROFILE%\.hermes\skills\note-taking\zsk" (
    rmdir /s /q "%USERPROFILE%\.hermes\skills\note-taking\zsk"
    echo   ✅ Hermes: zsk
    set /a REMOVED+=1
)
if exist "%USERPROFILE%\.hermes\skills\note-taking\zsk-build" (
    rmdir /s /q "%USERPROFILE%\.hermes\skills\note-taking\zsk-build"
    echo   ✅ Hermes: zsk-build
    set /a REMOVED+=1
)
if exist "%USERPROFILE%\.hermes\skills\note-taking\zsk-knowledge-base" (
    rmdir /s /q "%USERPROFILE%\.hermes\skills\note-taking\zsk-knowledge-base"
    echo   ✅ Hermes: zsk-knowledge-base
    set /a REMOVED+=1
)

if %REMOVED% EQU 0 (
    echo   未找到已安装的 skills
)

echo.

:: ── 可选：移除 pip 依赖 ──
set /p UNINSTALL_PIP="卸载 Python 依赖？(markdown/PyPDF2/python-docx) [y/N]: "
if /i "%UNINSTALL_PIP%"=="y" (
    pip uninstall markdown PyPDF2 python-docx -y -q 2>nul
    echo   ✅ 已移除 Python 依赖
)

:: ── 可选：删除项目文件夹 ──
echo.
set /p DELETE_PROJ="删除整个 zsk 项目文件夹？[y/N]: "
if /i "%DELETE_PROJ%"=="y" (
    echo   项目目录将在 3 秒后删除...
    set "PROJ_DIR=%~dp0"
    start "" cmd /c "timeout /t 3 >nul && rmdir /s /q \"!PROJ_DIR!\""
    exit
)

echo.
echo ============================================
echo   ✅ 卸载完成
echo ============================================
pause
