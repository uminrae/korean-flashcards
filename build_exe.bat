@echo off
chcp 65001 >nul
echo ========================================================
echo   未来的韩语卡片 - 自动化打包构建程序
echo ========================================================
echo.

python -X utf8 build_exe.py onedir

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 打包过程中出现异常，请检查上方日志输出。
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [成功] 打包完成！构建产物位于 dist/ 目录中。
pause
