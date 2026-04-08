# TL_GS - 火炬之光无限 · 玩法策略推荐

基于 TL_item_monitor 数据库，实时计算各玩法的成本、收益与 ROI，辅助玩家做出最优刷图决策。

## 功能特性

- 📊 **策略列表**：表格展示所有玩法，支持按成本/收益/ROI 排序
- 🤖 **截图识别**：上传游戏截图，自动 OCR 解析成本物品 + 核心掉落，一键入库
- 🏆 **ROI 推荐**：自动计算各玩法的投资回报率，首页展示 Top 3 推荐
- 💾 **本地存储**：策略数据保存在 `data/strategies.json`，无需服务器端数据库

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Flask + Python 3 |
| 数据库 | SQLite（复用 TL_item_monitor 数据库） |
| 前端 | 原生 HTML/CSS/JS，无框架依赖 |
| OCR | cnocr（本地离线中文识别） |

## 目录结构

```
TL_GS/
├── server.py              # Flask 服务器
├── config.yaml            # 配置文件
├── data/
│   └── strategies.json    # 策略数据
├── static/
│   └── uploads/           # 截图上传目录
├── templates/
│   └── index.html        # 前端页面
└── .venv/                 # Python 虚拟环境
```

## 快速开始

### 1. 安装依赖

```bash
cd TL_GS
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux

uv pip install flask pyyaml cnocr cnstd onnxruntime
```

### 2. 配置数据库路径

编辑 `config.yaml`，确保 `tl_item_monitor_db` 指向 TL_item_monitor 的数据库文件：

```yaml
tl_item_monitor_db: "../TL_item_monitor/data/tl_monitor.db"
strategies_file: "data/strategies.json"
port: 19878
host: "127.0.0.1"
```

### 3. 启动

```bash
source .venv/bin/activate
python server.py
```

访问 http://127.0.0.1:19878

## Windows 部署

只需确保两个项目在同一父目录下：

```
D:\Games\
  TL_item_monitor\
    data\tl_monitor.db
  TL_GS\
    config.yaml        → tl_item_monitor_db: "../TL_item_monitor/data/tl_monitor.db"
    server.py
```

数据库路径使用相对路径，移动项目时保持目录结构不变即可。

> ⚠️ Windows 上运行 TL_item_monitor 时，如使用代理/VPN，Playwright 请求可能报 `ERR_PROXY_CONNECTION_FAILED`，需关闭代理或配置 `server.proxy`。

## 截图识别使用说明

1. 点击页面右上角「➕ 添加策略截图」
2. 拖拽或选择游戏内玩法详情弹窗截图
3. 点击「🔍 解析预览」查看识别结果
4. 可编辑玩法名称、地图、平均时长、难度、标签
5. 点击「✅ 直接添加」入库

## 外网访问

默认仅监听 `127.0.0.1`，如需远程访问：

```yaml
# config.yaml
host: "0.0.0.0"
```

## API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取数据库连接状态 |
| PATCH | `/api/settings` | 更新数据库路径 |
| GET | `/api/strategies` | 获取所有策略（含实时价格） |
| GET | `/api/strategy/top?n=3` | ROI Top N 推荐 |
| POST | `/api/strategy/upload` | 上传截图识别入库 |
| PATCH | `/api/strategy/<id>` | 更新策略数量 |
| DELETE | `/api/strategy/<id>` | 删除策略 |
