# TL_GS 快速上手

---

## 支持平台

| 平台 | 支持状态 |
|------|----------|
| Windows 10/11 | ✅ 完整支持 |
| macOS | ✅ 完整支持 |
| Linux | ✅ 完整支持 |

---

## 一、安装 Python

**下载地址**：https://www.python.org/downloads/

安装时务必勾选 ✅ **Add Python to PATH**（添加到系统变量）。

验证安装：
```
python --version
```

---

## 二、安装依赖

### Windows（推荐双击运行）

```cmd
setup.bat
```

### macOS / Linux（手动安装）

```bash
pip install -r requirements.txt
```

---

## 三、配置

编辑 `config.yaml`：

```yaml
host: "0.0.0.0"
port: 19889

# 关联的 TL_item_monitor 数据库路径
tl_item_monitor_db: "../TL_item_monitor_BD/data/tl_monitor.db"

# 策略数据文件路径
strategies_file: "data/strategies.json"

# OpenAI API Key（用于截图识别，可不填）
openai_api_key: ""
```

> **注意**：`tl_item_monitor_db` 支持相对路径，相对于 TL_GS 目录。上面配置假设 TL_GS 和 TL_item_monitor_BD 在同一父目录下。

---

## 四、启动

### Windows

双击运行 `start.bat`

### macOS / Linux

```bash
python3 server.py
```

### 启动成功输出

```
TL_GS 启动中... http://0.0.0.0:19889
 * Running on http://127.0.0.1:19889
```

访问地址：**http://localhost:19889**

---

## 五、功能详解

### 5.1 策略列表

页面展示所有玩法，支持：
- 按成本/收益/ROI 排序
- 按地图/难度/标签筛选
- 查看玩法详情和成本明细

### 5.2 截图识别入库

1. 点击 **添加策略** 按钮
2. 上传游戏内玩法详情截图
3. 系统自动 OCR 解析成本物品 + 核心掉落
4. 一键入库

> 截图需包含完整的"玩法详情"弹窗内容。

### 5.3 ROI 推荐

首页自动展示 **Top 3 推荐玩法**，按投资回报率排序。

### 5.4 策略管理

- 修改数量：点击物品数量列，**按 Enter 确认**
- 删除策略：点击 ✕ 按钮
- 查看详情：点击玩法名称

---

## 六、数据库说明

| 文件 | 说明 |
|------|------|
| `data/tl_gs.db` | 策略数据库（SQLite，自动创建） |
| `data/strategies.json` | 策略 JSON 备份（已迁移至 SQLite） |
| `static/uploads/` | 截图上传目录 |

---

## 七、常见问题

| 问题 | 解决办法 |
|------|----------|
| 启动报错 "No module named 'yaml'" | 运行 `setup.bat` 安装依赖 |
| 火价显示 "未连接" | 检查 `tl_item_monitor_db` 路径是否指向 TL_item_monitor_BD 的数据库 |
| 截图识别失败 | 确保截图包含完整玩法详情弹窗 |
| 端口被占用 | 修改 `config.yaml` 中 `port` |

---

## 八、版本说明

- **v1.0** - SQLite 数据库迁移 + 端口改为 19889
- 策略数据从 JSON 迁移至 SQLite
- 日志轮转支持
