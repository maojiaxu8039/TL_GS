@echo off
chcp 65001 >nul
echo ========================================
echo  TL_GS 外网访问隧道（Cloudflare）
echo ========================================
echo.
echo [提示] 确保 server.py 已在本机运行（另开一个命令行窗口执行 start.bat）
echo.
echo 按任意键下载 cloudflared 并启动隧道...
pause >nul

:: 下载 cloudflared（Windows x86_64）
set "CF_URL=https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
echo 下载 cloudflared...
curl -L -o cloudflared.exe "%CF_URL%"

if not exist cloudflared.exe (
    echo [错误] 下载失败，请手动下载后放在本目录
    echo 下载地址: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    pause
    exit /b 1
)

echo.
echo 启动隧道...
echo 访问地址会在下方显示（可能需要等待几秒）
echo 按 Ctrl+C 停止隧道
echo.
cloudflared.exe tunnel --url http://localhost:19878

pause
