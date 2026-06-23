"""
错题Pro - 数据库层
SQLite schema + 全部CRUD操作
"""

import sqlite3
import os
from datetime import datetime, timedelta


DB_DIR = "user_data"

# ─── Schema DDL ─────────────────────────────────────────────

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS mistakes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject         TEXT NOT NULL DEFAULT 'math',
    original_problem TEXT NOT NULL,
    wrong_answer    TEXT NOT NULL,
    correct_answer  TEXT,
    knowledge_point TEXT NOT NULL,
    error_type      TEXT NOT NULL CHECK(error_type IN ('knowledge_gap','thinking_error','careless')),
    error_analysis  TEXT NOT NULL,
    pool_status     TEXT NOT NULL DEFAULT 'active' CHECK(pool_status IN ('active','observing','dormant')),
    grade_level     TEXT NOT NULL,
    curriculum_ver  TEXT NOT NULL DEFAULT '人教版',
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    last_reviewed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_mistakes_pool ON mistakes(pool_status);
CREATE INDEX IF NOT EXISTS idx_mistakes_kp ON mistakes(knowledge_point);
CREATE INDEX IF NOT EXISTS idx_mistakes_subject ON mistakes(subject);

CREATE TABLE IF NOT EXISTS variants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mistake_id      INTEGER NOT NULL REFERENCES mistakes(id),
    problem_text    TEXT NOT NULL,
    correct_answer  TEXT NOT NULL,
    difficulty      TEXT NOT NULL DEFAULT 'same' CHECK(difficulty IN ('easy','same','slightly_harder')),
    session_id      TEXT,
    is_original     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_variants_mistake ON variants(mistake_id);

CREATE TABLE IF NOT EXISTS attempts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id      INTEGER NOT NULL REFERENCES variants(id),
    student_answer  TEXT NOT NULL,
    is_correct      INTEGER NOT NULL,
    same_error      INTEGER,
    feedback        TEXT NOT NULL,
    hint            TEXT,
    action_type     TEXT NOT NULL DEFAULT 'correct',
    attempted_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_attempts_variant ON attempts(variant_id);

CREATE TABLE IF NOT EXISTS knowledge_mastery (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_point  TEXT NOT NULL,
    subject          TEXT NOT NULL DEFAULT 'math',
    total_attempts   INTEGER NOT NULL DEFAULT 0,
    correct_attempts INTEGER NOT NULL DEFAULT 0,
    mastery_score    REAL NOT NULL DEFAULT 0.0,
    streak           INTEGER NOT NULL DEFAULT 0,
    pool_status      TEXT NOT NULL DEFAULT 'active' CHECK(pool_status IN ('active','observing','dormant')),
    last_practiced_at TEXT,
    next_review_at   TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(knowledge_point, subject)
);

CREATE INDEX IF NOT EXISTS idx_mastery_review ON knowledge_mastery(next_review_at);
CREATE INDEX IF NOT EXISTS idx_mastery_pool ON knowledge_mastery(pool_status);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject         TEXT NOT NULL DEFAULT 'math',
    grade_level     TEXT NOT NULL,
    curriculum_ver  TEXT NOT NULL DEFAULT '人教版',
    unit_name       TEXT NOT NULL,
    knowledge_point TEXT NOT NULL,
    description     TEXT,
    difficulty_level TEXT DEFAULT 'intermediate',
    example_questions TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(grade_level, subject, knowledge_point, curriculum_ver)
);

CREATE INDEX IF NOT EXISTS idx_kb_lookup ON knowledge_base(grade_level, subject, knowledge_point);
"""


# ─── Connection ─────────────────────────────────────────────

def get_db_path(student_name: str) -> str:
    """返回某个学生的数据库路径"""
    return os.path.join(DB_DIR, student_name, "mistakes.db")


def get_conn(student_name: str) -> sqlite3.Connection:
    """获取数据库连接并启用外键"""
    db_path = get_db_path(student_name)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(student_name: str) -> None:
    """初始化数据库"""
    conn = get_conn(student_name)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# ─── Mistakes CRUD ──────────────────────────────────────────

def insert_mistake(conn: sqlite3.Connection, **kwargs) -> int:
    """插入错题，返回id"""
    fields = ['subject','original_problem','wrong_answer','correct_answer',
              'knowledge_point','error_type','error_analysis',
              'pool_status','grade_level','curriculum_ver']
    values = {k: kwargs[k] for k in fields if k in kwargs}
    cols = ', '.join(values.keys())
    placeholders = ', '.join('?' for _ in values)
    sql = f"INSERT INTO mistakes ({cols}) VALUES ({placeholders})"
    cur = conn.execute(sql, list(values.values()))
    conn.commit()
    return cur.lastrowid


def get_mistake(conn: sqlite3.Connection, mistake_id: int) -> dict:
    row = conn.execute("SELECT * FROM mistakes WHERE id = ?", (mistake_id,)).fetchone()
    return dict(row) if row else None


def list_mistakes(conn: sqlite3.Connection,
                  subject: str = None,
                  pool_status: str = None,
                  knowledge_point: str = None,
                  limit: int = 50) -> list[dict]:
    sql = "SELECT * FROM mistakes WHERE 1=1"
    params = []
    if subject:
        sql += " AND subject = ?"; params.append(subject)
    if pool_status:
        sql += " AND pool_status = ?"; params.append(pool_status)
    if knowledge_point:
        sql += " AND knowledge_point = ?"; params.append(knowledge_point)
    sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def update_pool_status(conn: sqlite3.Connection, mistake_id: int, status: str) -> None:
    conn.execute("UPDATE mistakes SET pool_status = ?, last_reviewed_at = datetime('now','localtime') WHERE id = ?",
                 (status, mistake_id))
    conn.commit()


# ─── Variants CRUD ──────────────────────────────────────────

def insert_variant(conn: sqlite3.Connection, **kwargs) -> int:
    fields = ['mistake_id','problem_text','correct_answer','difficulty','session_id','is_original']
    values = {k: kwargs[k] for k in fields if k in kwargs}
    cols = ', '.join(values.keys())
    placeholders = ', '.join('?' for _ in values)
    sql = f"INSERT INTO variants ({cols}) VALUES ({placeholders})"
    cur = conn.execute(sql, list(values.values()))
    conn.commit()
    return cur.lastrowid


def get_variants_for_mistake(conn: sqlite3.Connection, mistake_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM variants WHERE mistake_id = ? ORDER BY created_at DESC", (mistake_id,)).fetchall()]


def get_variant(conn: sqlite3.Connection, variant_id: int) -> dict:
    row = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    return dict(row) if row else None


# ─── Attempts CRUD ──────────────────────────────────────────

def insert_attempt(conn: sqlite3.Connection, **kwargs) -> int:
    fields = ['variant_id','student_answer','is_correct','same_error','feedback','hint','action_type']
    values = {k: kwargs[k] for k in fields if k in kwargs}
    cols = ', '.join(values.keys())
    placeholders = ', '.join('?' for _ in values)
    sql = f"INSERT INTO attempts ({cols}) VALUES ({placeholders})"
    cur = conn.execute(sql, list(values.values()))
    conn.commit()
    return cur.lastrowid


def get_attempts_for_variant(conn: sqlite3.Connection, variant_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM attempts WHERE variant_id = ? ORDER BY attempted_at DESC", (variant_id,)).fetchall()]


def get_recent_attempts(conn: sqlite3.Connection, knowledge_point: str, limit: int = 5) -> list[dict]:
    return [dict(r) for r in conn.execute("""
        SELECT a.* FROM attempts a
        JOIN variants v ON a.variant_id = v.id
        JOIN mistakes m ON v.mistake_id = m.id
        WHERE m.knowledge_point = ?
        ORDER BY a.attempted_at DESC LIMIT ?
    """, (knowledge_point, limit)).fetchall()]


# ─── Mastery CRUD ───────────────────────────────────────────

def upsert_mastery(conn: sqlite3.Connection, knowledge_point: str, subject: str,
                   is_correct: bool) -> dict:
    """更新知识点掌握度，返回最新数据"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    existing = conn.execute(
        "SELECT * FROM knowledge_mastery WHERE knowledge_point = ? AND subject = ?",
        (knowledge_point, subject)).fetchone()

    if existing:
        e = dict(existing)
        new_total = e['total_attempts'] + 1
        new_correct = e['correct_attempts'] + (1 if is_correct else 0)
        new_streak = e['streak'] + 1 if is_correct else 0

        # mastery_score: 近期权重0.7，历史权重0.3
        # 简化为：当前正确率 * 0.7 + 历史正确率 * 0.3
        recent_5 = get_recent_attempts(conn, knowledge_point, 5)
        recent_correct = sum(1 for a in recent_5 if a['is_correct'])
        recent_ratio = recent_correct / len(recent_5) if recent_5 else (1 if is_correct else 0)
        historical_ratio = new_correct / new_total if new_total > 0 else 0
        mastery = round(0.7 * recent_ratio + 0.3 * historical_ratio, 2)

        conn.execute("""
            UPDATE knowledge_mastery
            SET total_attempts = ?, correct_attempts = ?, mastery_score = ?,
                streak = ?, last_practiced_at = ?, updated_at = ?
            WHERE id = ?
        """, (new_total, new_correct, mastery, new_streak, now, now, e['id']))
        conn.commit()
    else:
        new_total, new_correct, new_streak = 1, (1 if is_correct else 0), (1 if is_correct else 0)
        mastery = 0.7 if is_correct else 0.0
        conn.execute("""
            INSERT INTO knowledge_mastery
                (knowledge_point, subject, total_attempts, correct_attempts,
                 mastery_score, streak, pool_status, last_practiced_at, next_review_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (knowledge_point, subject, new_total, new_correct, mastery, new_streak, now, now))
        conn.commit()

    return get_mastery(conn, knowledge_point, subject)


def get_mastery(conn: sqlite3.Connection, knowledge_point: str, subject: str = 'math') -> dict:
    row = conn.execute(
        "SELECT * FROM knowledge_mastery WHERE knowledge_point = ? AND subject = ?",
        (knowledge_point, subject)).fetchone()
    return dict(row) if row else None


def get_all_masteries(conn: sqlite3.Connection, subject: str = 'math') -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM knowledge_mastery WHERE subject = ? ORDER BY mastery_score ASC",
        (subject,)).fetchall()]


def get_due_reviews(conn: sqlite3.Connection, subject: str = 'math') -> list[dict]:
    """到期需复习的知识点"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return [dict(r) for r in conn.execute("""
        SELECT * FROM knowledge_mastery
        WHERE subject = ?
          AND pool_status IN ('active','observing')
          AND next_review_at <= ?
        ORDER BY mastery_score ASC
    """, (subject, now)).fetchall()]


def update_mastery_review(conn: sqlite3.Connection, knowledge_point: str, subject: str,
                          next_review_at: str, pool_status: str) -> None:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("""
        UPDATE knowledge_mastery
        SET next_review_at = ?, pool_status = ?, updated_at = ?
        WHERE knowledge_point = ? AND subject = ?
    """, (next_review_at, pool_status, now, knowledge_point, subject))
    conn.commit()

# ─── Knowledge Base CRUD ────────────────────────────────────

def upsert_knowledge_point(conn: sqlite3.Connection, **kwargs) -> int:
    """Insert or update a knowledge point in the knowledge base. Returns id."""
    fields = ['subject','grade_level','curriculum_ver','unit_name',
              'knowledge_point','description','difficulty_level','example_questions']
    values = {k: kwargs[k] for k in fields if k in kwargs}
    # example_questions should be a JSON string
    if 'example_questions' in values and not isinstance(values['example_questions'], str):
        import json
        values['example_questions'] = json.dumps(values['example_questions'], ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM knowledge_base WHERE grade_level=? AND subject=? AND knowledge_point=? AND curriculum_ver=?",
        (values.get('grade_level',''), values.get('subject','math'), values.get('knowledge_point',''), values.get('curriculum_ver','人教版'))
    ).fetchone()
    if existing:
        set_clause = ', '.join(f"{k}=?" for k in values)
        conn.execute(f"UPDATE knowledge_base SET {set_clause} WHERE id=?",
                     list(values.values()) + [existing['id']])
        conn.commit()
        return existing['id']
    else:
        cols = ', '.join(values.keys())
        placeholders = ', '.join('?' for _ in values)
        cur = conn.execute(f"INSERT INTO knowledge_base ({cols}) VALUES ({placeholders})", list(values.values()))
        conn.commit()
        return cur.lastrowid

def search_knowledge_point(conn: sqlite3.Connection, knowledge_point: str,
                           grade_level: str = None, subject: str = 'math') -> dict:
    """Find the closest matching knowledge point. Exact match first, then fuzzy."""
    params = [subject]
    if grade_level:
        row = conn.execute(
            "SELECT * FROM knowledge_base WHERE subject=? AND grade_level=? AND knowledge_point=?",
            (subject, grade_level, knowledge_point)).fetchone()
        if row: return dict(row)
        # Fuzzy: knowledge_point contains the search string
        row = conn.execute(
            "SELECT * FROM knowledge_base WHERE subject=? AND grade_level=? AND knowledge_point LIKE ?",
            (subject, grade_level, f'%{knowledge_point}%')).fetchone()
        if row: return dict(row)
    else:
        row = conn.execute(
            "SELECT * FROM knowledge_base WHERE subject=? AND knowledge_point=?",
            (subject, knowledge_point)).fetchone()
        if row: return dict(row)
        row = conn.execute(
            "SELECT * FROM knowledge_base WHERE subject=? AND knowledge_point LIKE ?",
            (subject, f'%{knowledge_point}%')).fetchone()
        if row: return dict(row)
    return None

def list_knowledge_points(conn: sqlite3.Connection, grade_level: str = None,
                          subject: str = 'math', limit: int = 200) -> list[dict]:
    """List knowledge points, optionally filtered by grade."""
    sql = "SELECT * FROM knowledge_base WHERE subject=?"
    params = [subject]
    if grade_level:
        sql += " AND grade_level=?"
        params.append(grade_level)
    sql += " ORDER BY grade_level, unit_name, knowledge_point LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def get_kb_by_kp(conn: sqlite3.Connection, knowledge_point: str,
                 grade_level: str = None, subject: str = 'math') -> dict:
    """Get knowledge base entry and parse example_questions from JSON."""
    entry = search_knowledge_point(conn, knowledge_point, grade_level, subject)
    if entry and entry.get('example_questions'):
        import json
        try:
            entry['example_questions'] = json.loads(entry['example_questions'])
        except json.JSONDecodeError:
            entry['example_questions'] = []
    return entry
