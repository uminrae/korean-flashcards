@echo off
chcp 65001 >nul
echo ========================================================
echo   「未来的韩语卡片」- 全自动化打包与安装包制作程序
echo ========================================================
echo.

python -X utf8 build_installer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 构建过程中出现异常，请检查上方日志输出。
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [成功] 安装包制作完成！文件位于 Output/ 目录下。
pause
