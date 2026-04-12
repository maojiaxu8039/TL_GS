# TL_GS - 火炬之光无限 · 玩法策略推荐

基于 TL_item_monitor 数据库，实时计算各玩法的成本、收益与 ROI，辅助玩家做出最优刷图决策。

---

## 功能特性

- 📊 **策略列表**：表格展示所有玩法，支持按成本/收益/ROI 排序和筛选
- 🤖 **截图识别**：上传游戏截图，自动 OCR 解析成本物品 + 核心掉落，一键入库
- 🏆 **ROI 推荐**：自动计算各玩法的投资回报率，首页展示 Top 3 推荐
- 💾 **本地存储**：策略数据保存在 SQLite，本地持久化
- 📤 **导出功能**：支持导出策略列表

---

## 环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.9 及以上 |
| 操作系统 | Windows 10+ / macOS / Linux |
| 依赖 | Flask, PyYAML（见 `requirements.txt`）|

---

## 快速开始

### Windows

1. 双击 `setup.bat` 安装依赖
2. 编辑 `config.yaml` 配置数据库路径
3. 双击 `start.bat` 启动

### macOS / Linux

```bash
pip install -r requirements.txt
python3 server.py
```

访问：**http://localhost:19889**

---

## 配置说明

`config.yaml` 完整参数：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `host` | 监听地址，`0.0.0.0` 表示外网可访问 | `127.0.0.1` |
| `port` | 服务端口 | `19889` |
| `tl_item_monitor_db` | TL_item_monitor_BD 数据库路径（绝对或相对路径） | 无 |
| `strategies_file` | 策略 JSON 备份文件路径 | `data/strategies.json` |
| `openai_api_key` | OpenAI API Key（用于截图识别，可不填） | 空 |

---

## 项目结构

```
TL_GS/
├── server.py              # Flask 服务器（主程序）
├── config.yaml            # 配置文件
├── requirements.txt       # Python 依赖
├── gs_db.py               # SQLite 数据库模块
├── start.bat              # Windows 一键启动脚本
├── setup.bat              # Windows 依赖安装脚本
│
├── data/
│   └── tl_gs.db          # 策略数据库（自动创建）
│
├── static/
│   └── uploads/          # 截图上传目录
│
└── templates/
    └── index.html        # 前端页面
```

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

## 常见问题

| 问题 | 解决办法 |
|------|----------|
| 启动报错 "No module named 'yaml'" | 运行 `setup.bat` 安装依赖 |
| 火价显示 "未连接" | 检查 `tl_item_monitor_db` 路径是否正确指向 TL_item_monitor_BD 的数据库 |
| 截图识别失败 | 确保截图包含完整玩法详情弹窗 |
| 端口被占用 | 修改 `config.yaml` 中 `port` |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Flask + Python 3 |
| 数据库 | SQLite（策略存储）+ TL_item_monitor_BD 数据库（火价数据） |
| 前端 | 原生 HTML/CSS/JS（无框架） |
| OCR | cnocr（本地中文识别，需安装 onnxruntime） |
