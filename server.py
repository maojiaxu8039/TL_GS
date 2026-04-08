"""
TL_GS - 火炬之光无限 玩法策略推荐
Flask 服务器，基于 TL_item_monitor 数据库查询物品价格
"""
import json
import re
import sqlite3
import os
import base64
import uuid
import yaml
import time
import threading
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory
import gs_db

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yaml"

# 价格自动刷新（每小时一次）
_last_price_refresh = 0
_PRICE_REFRESH_INTERVAL = 3600  # 秒

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

cfg = load_config()
TL_DB_PATH = BASE_DIR / cfg["tl_item_monitor_db"]
STRATEGIES_FILE = BASE_DIR / cfg["strategies_file"]
PORT = cfg.get("port", 19878)
HOST = cfg.get("host", "127.0.0.1")
UPLOAD_DIR = BASE_DIR / "static" / "uploads"

app = Flask(__name__, template_folder="templates")

def reload_config():
    global TL_DB_PATH, STRATEGIES_FILE, PORT, HOST
    cfg = load_config()
    TL_DB_PATH = BASE_DIR / cfg["tl_item_monitor_db"]
    STRATEGIES_FILE = BASE_DIR / cfg["strategies_file"]
    PORT = cfg.get("port", 19878)
    HOST = cfg.get("host", "127.0.0.1")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ========== 数据库查询 ==========

def get_item_price(item_name: str) -> dict:
    if not TL_DB_PATH.exists():
        return {"name": item_name, "price": None, "price_display": "未连接"}
    conn = sqlite3.connect(str(TL_DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT item_id, name, price FROM items WHERE name = ?", (item_name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"item_id": row[0], "name": row[1], "price": row[2], "price_display": f"{row[2]:.2f}" if row[2] else "--"}
    return {"name": item_name, "price": None, "price_display": "未找到"}


def get_latest_fire_price() -> float:
    if not TL_DB_PATH.exists():
        return 0
    conn = sqlite3.connect(str(TL_DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT ten_k FROM fire_price_record ORDER BY scraped_at DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


# ========== 策略数据（由 gs_db.py 管理）============

def refresh_all_prices_if_needed():
    """检查是否需要刷新价格，是则重新从数据库查询所有物品价格"""
    global _last_price_refresh
    now = time.time()
    if now - _last_price_refresh < _PRICE_REFRESH_INTERVAL:
        return
    _last_price_refresh = now
    try:
        strategies = gs_db.load_strategies()
        fire_price = get_latest_fire_price()
        for s in strategies:
            s["_fire_price"] = fire_price
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 价格缓存已刷新 ({len(strategies)} 条策略)")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 价格刷新失败: {e}")

def enrich_strategy(strategy: dict, fire_price: float) -> dict:
    total_cost = 0
    enriched_cost = []
    for item in strategy.get("cost_items", []):
        info = get_item_price(item["name"])
        fire = info["price"] or 0
        cnt = item["count"]
        cost = fire * cnt
        total_cost += cost
        enriched_cost.append({
            **item,
            "price": info["price"],
            "price_display": info["price_display"],
            "total_cost": round(cost, 4),
            "rmb": round(cost * fire_price / 10000, 2) if fire_price else 0,
        })

    enriched_drops = []
    for item in strategy.get("core_drops", []):
        info = get_item_price(item["name"])
        fire = info["price"] or 0
        enriched_drops.append({
            **item,
            "price": info["price"],
            "price_display": info["price_display"],
            "rmb": round(fire * fire_price / 10000, 2) if fire_price else 0,
        })

    return {
        **strategy,
        "enriched_cost_items": enriched_cost,
        "enriched_core_drops": enriched_drops,
        "total_cost_fire": round(total_cost, 4),
        "total_cost_rmb": round(total_cost * fire_price / 10000, 2) if fire_price else 0,
    }


# ========== 截图解析（cnocr 本地 OCR） ==========

def parse_screenshot_ocr(image_path: str) -> dict:
    """
    使用 cnocr 解析截图，提取策略数据。
    适用于 TL 详情弹窗截图，结构已知：
      - "成本物品" 区域 → 成本物品列表
      - "掉率物品" 或 "核心掉落" 区域 → 掉落物品列表
      - "地图区域" → 地图/玩法名称
      - "平均时长" → 时长
    返回 dict，包含 name/map/cost_items/core_drops 等字段。
    """
    from cnocr import CnOcr

    ocr = CnOcr()
    results = ocr.ocr(image_path)

    # 收集所有识别的文本+位置
    lines = []
    for item in results:
        text = item["text"].strip()
        if text:
            lines.append({
                "text": text,
                "score": item.get("score", 0),
            })

    full_text = "\n".join(item["text"] for item in lines)

    # ---- 提取字段 ----
    parsed = {
        "name": "",
        "map": "",
        "avg_duration": "",
        "difficulty": "",
        "tags": [],
        "cost_items": [],
        "core_drops": [],
        "drop_categories": [],
        "notes": "",
    }

    # 地图区域（从 "地图区域" 关键词后面提取）
    m = re.search(r'地图区域\s*[:：]?\s*([^\n]+)', full_text)
    if m:
        parsed["map"] = m.group(1).strip()
        if not parsed["name"]:
            parsed["name"] = parsed["map"]

    # 平均时长
    m = re.search(r'平均时长\s*[:：]?\s*([^\n]+)', full_text)
    if m:
        parsed["avg_duration"] = m.group(1).strip()

    # 使用次数
    m = re.search(r'使用次数\s*[:：]?\s*(\d+)', full_text)
    parsed["use_count"] = int(m.group(1)) if m else 1

    # 尝试从 "主天赋" 提取玩法名（优先级最高）
    m = re.search(r'主天赋\s*\n?\s*([^\n]+)', full_text)
    if m:
        val = m.group(1).strip()
        if val and val not in ("未知玩法", ""):
            parsed["name"] = val

    # 尝试从 "地图玩法" 提取玩法名（次优先）
    if not parsed["name"]:
        m = re.search(r'地图玩法\s*[:：]?\s*([^\n]+)', full_text)
        if m:
            val = m.group(1).strip()
            if val and val not in ("未知玩法", ""):
                parsed["name"] = val

    # ---- 成本物品解析 ----
    # 成本物品表中每行格式: 物品名 单价 数量 总价
    # 关键词：成本物品 / 物品 / 单价 / 数量 / 总价 表头
    # 找 "成本物品" 区域（掉率物品之前的内容）
    cost_section = ""
    drop_section = ""

    cost_idx = full_text.find("成本物品")
    drop_idx = full_text.find("掉率物品")
    core_drop_idx = full_text.find("核心掉落")

    if cost_idx >= 0 and drop_idx > cost_idx:
        cost_section = full_text[cost_idx:drop_idx]
    elif cost_idx >= 0 and core_drop_idx > cost_idx:
        cost_section = full_text[cost_idx:core_drop_idx]

    if drop_idx >= 0:
        drop_section = full_text[drop_idx:]
    elif core_drop_idx >= 0:
        drop_section = full_text[core_drop_idx:]

    # 解析成本物品：从成本区域提取物品行
    # 规则：连续行包含 "火" 且有数字 → 物品行
    # 物品名通常不以数字开头，包含中文
    cost_item_names = [
        "深空回响", "罪孽之劫掠罗盘", "富饶之劲敌罗盘", "黄金之囚笼星盘",
        "钛金手术刀", "繁荣之深空探针", "深空信标", "初火源质",
        "神圣化石", "悬赏之通缉罗盘", "警戒之通缉罗盘", "典藏之玩偶星盘",
        "纯银手术刀", "黄金之纯真星盘", "富饶之灵瓶",
    ]
    known_items = set(cost_item_names)  # 预置已知成本物品

    # 从成本区域匹配已知物品
    for item_name in cost_item_names:
        if item_name in cost_section:
            # 尝试提取数量：物品名后紧跟的数字
            # e.g. "钛金手术刀  98.7火  42  4145火"
            pattern = re.escape(item_name) + r'\s*[:：]?\s*([\d\.]+)\s*火\s*(\d+)\s*'
            mm = re.search(pattern, cost_section)
            if mm:
                try:
                    price = float(mm.group(1))
                    count = int(mm.group(2))
                    parsed["cost_items"].append({"name": item_name, "count": count})
                except ValueError:
                    parsed["cost_items"].append({"name": item_name, "count": 1})
            else:
                # 只找到物品名，没有价格数量 → 记为 count=1（用户手动补充）
                if not any(item["name"] == item_name for item in parsed["cost_items"]):
                    parsed["cost_items"].append({"name": item_name, "count": 1})

    # ---- 核心掉落解析 ----
    # 从掉落区域提取（价格在 1火~200火 左右，有数量）
    drop_pattern = re.findall(
        r'([^\s\d][^\n]{1,20}?)\s+([\d\.]+)\s*火\s+(\d+)\s',
        drop_section,
    )
    rarity_keywords = ["传说", "传奇", "史诗", "精良", "普通", "遗珍"]
    drop_items_seen = set()

    # 先扫描整个掉落区域，建立「稀有词 → 附近物品」映射
    # 策略：稀有词出现在某行时，向前/后找最近的物品名
    rarity_map = {}
    for kw in rarity_keywords:
        idx = 0
        while True:
            pos = drop_section.find(kw, idx)
            if pos == -1:
                break
            # 找这段范围内的物品行（包含 "火" 和数字）
            snippet = drop_section[max(0, pos-50):pos+30]
            item_match = re.search(r'([\u4e00-\u9fff][^\n]{0,20}?)\s+[\d\.]+\s*火', snippet)
            if item_match:
                item_name = item_match.group(1).strip()
                rarity_map[item_name] = kw
            idx = pos + 1

    for match in drop_pattern:
        name = match[0].strip()
        # 过滤表头、无效行
        if any(kw in name for kw in ["物品", "单价", "数量", "总价", "合计", "展开", "总计"]):
            continue
        if name in drop_items_seen:
            continue
        try:
            price = float(match[1])
            count = int(match[2])
        except ValueError:
            continue
        # 稀有度：优先用「附近稀有词」映射，再检查物品名本身
        rarity = rarity_map.get(name, "普通")
        if rarity == "普通":
            for kw in rarity_keywords:
                if kw in name:
                    rarity = kw
                    break
        drop_items_seen.add(name)
        parsed["core_drops"].append({"name": name, "rarity": rarity, "count": count, "price_fire": price})

    # 如果没找到，尝试模糊匹配
    if not parsed["core_drops"]:
        drop_lines = re.findall(r'([^\n]{2,30}?)\s+([\d\.]+)\s*火\s*(\d+)', drop_section)
        for dl in drop_lines:
            name = dl[0].strip()
            if any(kw in name for kw in ["物品", "单价", "数量", "展开", "合计", "总计"]):
                continue
            if name in drop_items_seen:
                continue
            try:
                price = float(dl[1])
                count = int(dl[2])
                rarity = rarity_map.get(name, "普通")
                if rarity == "普通":
                    for kw in rarity_keywords:
                        if kw in name:
                            rarity = kw
                            break
                drop_items_seen.add(name)
                parsed["core_drops"].append({"name": name, "rarity": rarity, "count": count, "price_fire": price})
            except ValueError:
                continue

    # ---- 掉落分类解析（罗盘 42.6%、燃料 26.3% 等） ----
    # 格式：●罗盘 42.6%●燃料26.3%●化石21.5%●通用道具 4.2%●记忆荧光3.0%●灰烬 1.7%●其他0.8%
    for seg in full_text.split('●'):
        seg = seg.strip()
        if not seg:
            continue
        m = re.match(r'([^%\d]+)\s*([\d\.]+%)', seg)
        if m:
            name = m.group(1).strip()
            pct_str = m.group(2).replace('%', '')
            try:
                pct_val = float(pct_str)
                if name:
                    parsed["drop_categories"].append({"name": name, "percent": pct_val})
            except ValueError:
                continue

    # ---- 难度推测（根据平均收益/成本比） ----
    if parsed["cost_items"] and parsed["core_drops"]:
        total_cost_fire = sum(
            item.get("price_fire", 0) * item["count"]
            for item in parsed["cost_items"]
        )
        total_drop_fire = sum(
            item.get("price_fire", 0) * item["count"]
            for item in parsed["core_drops"]
        )
        if total_cost_fire > 0:
            ratio = total_drop_fire / total_cost_fire
            if ratio < 1:
                parsed["difficulty"] = "困难"
            elif ratio < 3:
                parsed["difficulty"] = "中等"
            else:
                parsed["difficulty"] = "简单"

    return parsed


# ========== API 路由 ==========

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/strategies")
def api_strategies():
    refresh_all_prices_if_needed()
    fire_price = get_latest_fire_price()
    strategies = gs_db.load_strategies()
    return jsonify({"fire_price": fire_price, "strategies": [enrich_strategy(s, fire_price) for s in strategies]})

@app.route("/api/strategy/top")
def api_strategy_top():
    """返回 ROI 排名前 N 的策略（默认3个）"""
    refresh_all_prices_if_needed()
    n = request.args.get("n", 3, type=int)
    fire_price = get_latest_fire_price()
    strategies = gs_db.load_strategies()
    enriched = [enrich_strategy(s, fire_price) for s in strategies]
    # 计算 ROI
    def calc_roi(s):
        drop_value = sum((d.get("price") or 0) for d in (s.get("enriched_core_drops") or []))
        cost = s.get("total_cost_fire") or 0
        if cost <= 0:
            return -9999
        return (drop_value / cost - 1) * 100
    # 按 ROI 降序，取前 N
    ranked = sorted(enriched, key=calc_roi, reverse=True)[:n]
    result = []
    for s in ranked:
        drop_value = sum((d.get("price") or 0) for d in (s.get("enriched_core_drops") or []))
        cost = s.get("total_cost_fire") or 0
        roi = calc_roi(s)
        result.append({
            "strategy": s,
            "roi": roi,
            "drop_value": drop_value,
            "cost": cost,
            "profit": drop_value - cost if cost > 0 else 0,
        })
    return jsonify({"fire_price": fire_price, "recommendations": result})

@app.route("/api/item/search")
def api_item_search():
    keyword = request.args.get("q", "")
    if not keyword or len(keyword) < 1:
        return jsonify([])
    if not TL_DB_PATH.exists():
        return jsonify([])
    conn = sqlite3.connect(str(TL_DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT item_id, name, price FROM items WHERE name LIKE ? LIMIT 10", (f"%{keyword}%",))
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"item_id": r[0], "name": r[1], "price": r[2], "price_display": f"{r[2]:.2f}" if r[2] else "--"} for r in rows])

@app.route("/api/fire-price")
def api_fire_price():
    return jsonify({"fire_price": get_latest_fire_price()})

@app.route("/api/refresh-prices")
def api_refresh_prices():
    """手动触发价格刷新"""
    global _last_price_refresh
    _last_price_refresh = 0
    refresh_all_prices_if_needed()
    return jsonify({"success": True})

@app.route("/api/strategy/<int:strategy_id>", methods=["PATCH"])
def api_strategy_patch(strategy_id):
    """更新策略的数量（成本物品/核心掉落）"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "无效 JSON"}), 400
    strategies = gs_db.load_strategies()
    idx = None
    for i, s in enumerate(strategies):
        if s.get("id") == strategy_id:
            idx = i
            break
    if idx is None:
        return jsonify({"success": False, "message": f"未找到 ID={strategy_id} 的策略"}), 404
    # 更新字段
    if "cost_items" in data:
        strategies[idx]["cost_items"] = data["cost_items"]
    if "core_drops" in data:
        strategies[idx]["core_drops"] = data["core_drops"]
    if "dps" in data:
        strategies[idx]["dps"] = data["dps"]
    if "survival" in data:
        strategies[idx]["survival"] = data["survival"]
    gs_db.update_strategy(strategy_id, strategies[idx])
    fire_price = get_latest_fire_price()
    enriched = enrich_strategy(strategies[idx], fire_price)
    return jsonify({"success": True, "strategy": enriched})

@app.route("/api/strategy/<int:strategy_id>", methods=["DELETE"])
def api_strategy_delete(strategy_id):
    gs_db.delete_strategy(strategy_id)
    return jsonify({"success": True, "message": f"已删除 ID={strategy_id}"})

@app.route("/api/strategy/add", methods=["POST"])
def api_strategy_add():
    """
    直接添加策略（不重解析图片）。
    请求体: JSON
      name, map, avg_duration, difficulty, tags,
      cost_items: [{name, count}],
      core_drops: [{name, rarity, count}]
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "无效 JSON"}), 400

    # 掉落物品数量除以使用次数，转换为单次数量
    use_count = data.get("use_count") or 1
    cost_items = data.get("cost_items", [])
    core_drops = []
    for item in data.get("core_drops", []):
        raw = item.get("count", 1)
        core_drops.append({
            "name": item["name"],
            "rarity": item.get("rarity", "普通"),
            "count": round(raw / use_count, 2) if use_count > 1 else raw,
            "price_fire": item.get("price_fire", 0),
        })

    conn_for_id = gs_db.get_conn()
    strategy_id = gs_db.get_next_id(conn_for_id)
    conn_for_id.close()
    new_strategy = {
        "id": strategy_id,
        "name": data.get("name", "") or f"玩法{strategy_id}",
        "map": data.get("map", ""),
        "cost_items": cost_items,
        "core_drops": core_drops,
        "avg_duration": data.get("avg_duration", ""),
        "difficulty": data.get("difficulty", ""),
        "tags": data.get("tags", []),
        "notes": data.get("notes", ""),
        "use_count": use_count,
        "dps": data.get("dps") or 0,
        "survival": data.get("survival") or 0,
    }
    gs_db.add_strategy(new_strategy)

    fire_price = get_latest_fire_price()
    enriched = enrich_strategy(new_strategy, fire_price)

    return jsonify({
        "success": True,
        "message": f"已添加策略: {enriched['name']}",
        "strategy": enriched,
    })

@app.route("/api/strategy/upload", methods=["POST"])
def api_strategy_upload():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "没有上传图片"}), 400
    img = request.files["image"]
    if not img.filename:
        return jsonify({"success": False, "message": "文件名为空"}), 400
    ext = os.path.splitext(img.filename)[1] or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    img.save(str(filepath))

    try:
        parsed = parse_screenshot_ocr(str(filepath))
    except Exception as e:
        return jsonify({"success": False, "message": f"OCR 解析失败: {str(e)}", "image_url": f"/static/uploads/{filename}"}), 500

    # 构建策略对象（成本/掉落数量除以使用次数，转换为单次数量）
    use_count = parsed.get("use_count") or 1
    cost_items = []
    for item in parsed.get("cost_items", []):
        raw = item.get("count", 1)
        cost_items.append({"name": item["name"], "count": raw})
    core_drops = []
    for item in parsed.get("core_drops", []):
        raw = item.get("count", 1)
        core_drops.append({"name": item["name"], "rarity": item.get("rarity", "普通"), "count": round(raw / use_count, 2) if use_count > 1 else raw, "price_fire": item.get("price_fire", 0)})

    conn_for_id = gs_db.get_conn()
    strategy_id = gs_db.get_next_id(conn_for_id)
    conn_for_id.close()
    new_strategy = {
        "id": strategy_id,
        "name": parsed.get("name", "") or f"玩法{strategy_id}",
        "map": parsed.get("map", ""),
        "cost_items": cost_items,
        "core_drops": core_drops,
        "avg_duration": parsed.get("avg_duration", ""),
        "difficulty": parsed.get("difficulty", ""),
        "tags": parsed.get("tags", []),
        "notes": parsed.get("notes", ""),
        "use_count": use_count,
    }

    gs_db.add_strategy(new_strategy)

    fire_price = get_latest_fire_price()
    enriched = enrich_strategy(new_strategy, fire_price)

    return jsonify({
        "success": True,
        "message": f"已添加策略: {enriched['name']}（{len(enriched.get('cost_items', []))} 个成本物品，{len(enriched.get('core_drops', []))} 个掉落物品）",
        "strategy": enriched,
        "raw_parsed": parsed,
        "image_url": f"/static/uploads/{filename}",
    })

@app.route("/api/strategy/parse-only", methods=["POST"])
def api_strategy_parse_only():
    if "image" not in request.files:
        return jsonify({"success": False, "message": "没有上传图片"}), 400
    img = request.files["image"]
    ext = os.path.splitext(img.filename)[1] or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    img.save(str(filepath))

    try:
        parsed = parse_screenshot_ocr(str(filepath))
    except Exception as e:
        return jsonify({"success": False, "message": f"OCR 解析失败: {str(e)}", "image_url": f"/static/uploads/{filename}"}), 500

    return jsonify({"success": True, "parsed": parsed, "image_url": f"/static/uploads/{filename}"})

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/api/settings")
def api_settings_get():
    cfg = load_config()
    db_exists = TL_DB_PATH.exists()
    db_item_count = 0
    db_fire_price = 0
    if db_exists:
        try:
            conn = sqlite3.connect(str(TL_DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM items")
            db_item_count = cur.fetchone()[0]
            cur.execute("SELECT ten_k FROM fire_price_record ORDER BY scraped_at DESC LIMIT 1")
            row = cur.fetchone()
            db_fire_price = row[0] if row else 0
            conn.close()
        except:
            pass
    return jsonify({
        "tl_item_monitor_db": str(cfg.get("tl_item_monitor_db", "")),
        "db_exists": db_exists,
        "db_item_count": db_item_count,
        "db_fire_price": db_fire_price,
    })

@app.route("/api/settings", methods=["PATCH"])
def api_settings_patch():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "无效 JSON"}), 400
    new_path = data.get("tl_item_monitor_db", "")
    if not new_path:
        return jsonify({"success": False, "message": "路径不能为空"}), 400
    abs_path = BASE_DIR / new_path
    if not abs_path.exists():
        return jsonify({"success": False, "message": f"文件不存在: {abs_path}"}), 400
    cfg = load_config()
    cfg["tl_item_monitor_db"] = new_path
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
    reload_config()
    global _last_price_refresh
    _last_price_refresh = 0
    return jsonify({"success": True, "message": "设置已保存"})

if __name__ == "__main__":
    print(f"TL_GS 启动中... http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
