"""
gs_db.py - TL_GS SQLite 数据库模块
所有策略数据的持久化操作，不含业务逻辑（enrich在server.py）
"""
import sqlite3
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
GS_DB_PATH = BASE_DIR / "data" / "tl_gs.db"
STRATEGIES_JSON_PATH = BASE_DIR / "data" / "strategies.json"


def get_conn():
    conn = sqlite3.connect(str(GS_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    os.makedirs(BASE_DIR / "data", exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY,
        name TEXT,
        map TEXT,
        avg_duration TEXT,
        difficulty TEXT,
        tags TEXT,
        notes TEXT,
        use_count INTEGER DEFAULT 1,
        dps REAL DEFAULT 0,
        survival REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cost_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER,
        name TEXT,
        count REAL,
        FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS core_drops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER,
        name TEXT,
        rarity TEXT DEFAULT '普通',
        count REAL,
        price_fire REAL DEFAULT 0,
        FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
    )
    """)
    # 启用外键（SQLite默认关闭）
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def migrate_from_json():
    """如果JSON文件存在但DB为空，从JSON迁移数据"""
    if not STRATEGIES_JSON_PATH.exists():
        return
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM strategies")
    count = cur.fetchone()[0]
    if count > 0:
        conn.close()
        return  # DB已有数据，不迁移

    print(f"[gs_db] 检测到 strategies.json，开始迁移到 SQLite...")
    with open(STRATEGIES_JSON_PATH, "r", encoding="utf-8") as f:
        strategies = json.load(f)

    for s in strategies:
        _save_strategy_raw(conn, s)

    conn.commit()
    conn.close()
    print(f"[gs_db] 迁移完成，共 {len(strategies)} 条策略")


def _save_strategy_raw(conn, s: dict):
    """在已有连接上保存或更新一条策略（不提交）"""
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    strategy_id = s.get("id")
    cur.execute("SELECT id FROM strategies WHERE id = ?", (strategy_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("""
        UPDATE strategies SET name=?, map=?, avg_duration=?, difficulty=?,
        tags=?, notes=?, use_count=?, dps=?, survival=?
        WHERE id=?
        """, (
            s.get("name", ""),
            s.get("map", ""),
            s.get("avg_duration", ""),
            s.get("difficulty", ""),
            json.dumps(s.get("tags", []), ensure_ascii=False),
            s.get("notes", ""),
            s.get("use_count", 1),
            s.get("dps", 0) or 0,
            s.get("survival", 0) or 0,
            strategy_id,
        ))
    else:
        cur.execute("""
        INSERT INTO strategies (id, name, map, avg_duration, difficulty, tags, notes, use_count, dps, survival)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy_id,
            s.get("name", ""),
            s.get("map", ""),
            s.get("avg_duration", ""),
            s.get("difficulty", ""),
            json.dumps(s.get("tags", []), ensure_ascii=False),
            s.get("notes", ""),
            s.get("use_count", 1),
            s.get("dps", 0) or 0,
            s.get("survival", 0) or 0,
        ))

    # 删除旧的关联数据
    cur.execute("DELETE FROM cost_items WHERE strategy_id = ?", (strategy_id,))
    cur.execute("DELETE FROM core_drops WHERE strategy_id = ?", (strategy_id,))

    # 插入成本物品
    for item in s.get("cost_items", []):
        cur.execute(
            "INSERT INTO cost_items (strategy_id, name, count) VALUES (?, ?, ?)",
            (strategy_id, item.get("name", ""), item.get("count", 1))
        )

    # 插入核心掉落
    for item in s.get("core_drops", []):
        cur.execute(
            "INSERT INTO core_drops (strategy_id, name, rarity, count, price_fire) VALUES (?, ?, ?, ?, ?)",
            (strategy_id, item.get("name", ""), item.get("rarity", "普通"),
             item.get("count", 1), item.get("price_fire", 0))
        )


def get_next_id(conn) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM strategies")
    return cur.fetchone()[0]


def load_strategies() -> list:
    """加载所有策略（含关联数据），返回原始字典列表"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM strategies ORDER BY id")
    rows = cur.fetchall()
    strategies = []
    for row in rows:
        s = dict(row)
        s["tags"] = json.loads(s["tags"]) if s["tags"] else []
        strategy_id = s["id"]

        cur.execute("SELECT name, count FROM cost_items WHERE strategy_id = ?", (strategy_id,))
        s["cost_items"] = [{"name": r["name"], "count": r["count"]} for r in cur.fetchall()]

        cur.execute("SELECT name, rarity, count, price_fire FROM core_drops WHERE strategy_id = ?", (strategy_id,))
        s["core_drops"] = [dict(r) for r in cur.fetchall()]

        strategies.append(s)

    conn.close()
    return strategies


def add_strategy(s: dict) -> dict:
    """新增一条策略，返回（含id）"""
    conn = get_conn()
    _save_strategy_raw(conn, s)
    conn.commit()
    conn.close()
    return s


def update_strategy(strategy_id: int, s: dict) -> dict:
    """更新一条策略"""
    conn = get_conn()
    _save_strategy_raw(conn, s)
    conn.commit()
    conn.close()
    return s


def delete_strategy(strategy_id: int):
    """删除策略及其关联数据"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
    conn.commit()
    conn.close()


# 启动时初始化
init_db()
migrate_from_json()
