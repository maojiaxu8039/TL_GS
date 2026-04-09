@echo off
chcp 65001 >nul
echo ========================================
echo  TL_GS 火炬之光无限 · 玩法策略推荐
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查依赖...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo [安装依赖] 首次运行，安装 Python 包...
    pip install -r requirements.txt
)

:: 检查数据库
echo [2/3] 检查配置...
python -c "import yaml; cfg=yaml.safe_load(open('config.yaml','r',encoding='utf-8')); print('  火价数据库:', cfg.get('tl_item_monitor_db','未配置'))"

:: 启动服务器
echo [3/3] 启动 Flask 服务器...
echo.
echo  访问地址: http://localhost:19878
echo  按 Ctrl+C 停止服务器
echo.
python server.py
