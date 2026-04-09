# TL_GS - 火炬之光无限 · 玩法策略推荐

基于 TL_item_monitor 数据库，实时计算各玩法的成本、收益与 ROI，辅助玩家做出最优刷图决策。

---

## 功能特性

- 📊 **策略列表**：表格展示所有玩法，支持按成本/收益/ROI 排序和筛选
- 🤖 **截图识别**：上传游戏截图，自动 OCR 解析成本物品 + 核心掉落，一键入库
- 🏆 **ROI 推荐**：自动计算各玩法的投资回报率，首页展示 Top 3 推荐
- 💾 **本地存储**：策略数据保存在 SQLite，本地持久化

---

## 环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.9 及以上 |
| 操作系统 | Windows 10+ / macOS / Linux |
| 依赖 | Flask, PyYAML（见 `requirements.txt`）|

> [!TIP]
> 推荐同时安装 [TL_item_monitor](https://github.com/maojiaxu8039/TL_item_monitor)，用于获取实时火价数据。

---

## 快速开始（Windows）

### 第一步：下载项目

点击页面右上角 **Code → Download ZIP**，解压到本地，例如：

```
D:\Projects\TL_GS\
```

### 第二步：安装依赖

**方式 A：双击运行（推荐）**

```
双击 start.bat
```

首次运行会自动安装所需 Python 包。

**方式 B：手动安装**

```cmd
cd D:\Projects\TL_GS
pip install -r requirements.txt
```

### 第三步：配置数据库路径

编辑 `config.yaml`，确认 `tl_item_monitor_db` 指向 TL_item_monitor 的数据库文件（两个项目在同一父目录下使用相对路径即可）：

```yaml
host: "0.0.0.0"
port: 19878

# 关联的 TL_item_monitor 数据库路径
tl_item_monitor_db: "../TL_item_monitor/data/tl_monitor.db"

# 策略数据文件路径
strategies_file: "data/strategies.json"
```

### 第四步：启动

双击 `start.bat`，看到以下输出表示启动成功：

```
TL_GS 启动中... http://0.0.0.0:19878
 * Running on http://127.0.0.1:19878
```

打开浏览器访问 **http://localhost:19878**

---

## 快速开始（macOS / Linux）

```bash
cd TL_GS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

---

## 外网访问

### Windows

1. 确保 `config.yaml` 中 `host: "0.0.0.0"`
2. 双击运行 `start_tunnel.bat`
3. 等待出现 `https://xxxx.trycloudflare.com` 即可在外网访问

> [!NOTE]
> `start_tunnel.bat` 会自动下载 cloudflared，无需手动安装。

### macOS / Linux

```bash
cloudflared tunnel --url http://localhost:19878
```

---

## 项目结构

```
TL_GS/
├── server.py              # Flask 服务器（主程序）
├── config.yaml            # 配置文件
├── requirements.txt       # Python 依赖
├── gs_db.py               # SQLite 数据库模块
├── start.bat              # Windows 一键启动脚本
├── start_tunnel.bat       # Windows 外网隧道脚本
│
├── data/
│   └── tl_gs.db          # 策略数据库（自动创建）
│
├── static/
│   └── uploads/          # 截图上传目录
│
└── templates/
    └── index.html       # 前端页面
```

---

## 配置文件说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `host` | 监听地址，`0.0.0.0` 表示外网可访问 | `127.0.0.1` |
| `port` | 服务端口 | `19878` |
| `tl_item_monitor_db` | TL_item_monitor 数据库路径（绝对或相对路径） | 无 |
| `strategies_file` | 策略 JSON 备份文件路径 | `data/strategies.json` |
| `openai_api_key` | OpenAI API Key（用于截图识别，可不填） | 空 |

---

## 常见问题

### Q: 启动报错 "No module named 'yaml'"
A: 运行 `pip install -r requirements.txt` 安装依赖。

### Q: 火价数据显示 "未连接"
A: 检查 `config.yaml` 中 `tl_item_monitor_db` 路径是否正确指向 TL_item_monitor 的 `tl_monitor.db` 文件。

### Q: 截图识别失败
A: 确保截图包含完整的"玩法详情"弹窗内容，包含物品数量和名称。

### Q: 想修改端口
A: 编辑 `config.yaml` 中的 `port` 字段，重启服务生效。

---

## API 文档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取数据库连接状态 |
| PATCH | `/api/settings` | 更新数据库路径 |
| GET | `/api/strategies` | 获取所有策略（含实时价格计算） |
| GET | `/api/strategy/top?n=3` | ROI Top N 推荐 |
| POST | `/api/strategy/upload` | 上传截图识别入库 |
| PATCH | `/api/strategy/<id>` | 更新策略数量 |
| DELETE | `/api/strategy/<id>` | 删除策略 |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Flask + Python 3 |
| 数据库 | SQLite（策略存储） + TL_item_monitor 数据库（火价数据） |
| 前端 | 原生 HTML/CSS/JS（无框架） |
| OCR | cnocr（本地中文识别，需安装 onnxruntime） |
