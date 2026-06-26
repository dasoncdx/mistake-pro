#!/usr/bin/env python3
"""
错题Pro - 题库爬虫 Agent
独立脚本，不嵌入 Web 服务。用 cron 每日运行，积累教材配套题库。
Usage: python crawler.py [--subject math] [--grade grade_4]
"""

import os
import json
import time
import hashlib
import argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.join(ROOT, "question_bank")

GRADE_MAP = {
    "grade_1": "小一", "grade_2": "小二", "grade_3": "小三",
    "grade_4": "小四", "grade_5": "小五", "grade_6": "小六",
}

SUBJECT_MAP = {"math": "数学", "english": "英语", "chinese": "语文"}


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def question_id(question: str, answer: str, knowledge_point: str) -> str:
    """生成题目唯一 ID，用于去重"""
    raw = f"{knowledge_point}|{question}|{answer}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def load_existing(subject: str, grade: str) -> set[str]:
    """加载已有题目 ID 集合，避免重复抓取"""
    ids = set()
    d = os.path.join(BANK_DIR, subject, grade)
    if not os.path.isdir(d):
        return ids
    for fname in os.listdir(d):
        if fname.endswith(".jsonl"):
            with open(os.path.join(d, fname), errors="ignore") as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        ids.add(item.get("id", ""))
                    except json.JSONDecodeError:
                        continue
    return ids


def save_questions(subject: str, grade: str, questions: list[dict], source: str):
    """追加题目到 question_bank/{subject}/{grade}/{date}_{source}.jsonl"""
    d = os.path.join(BANK_DIR, subject, grade)
    ensure_dir(d)
    today = datetime.now().strftime("%Y%m%d")
    fname = f"{today}_{source}.jsonl"
    existing_ids = load_existing(subject, grade)
    new_count = 0
    with open(os.path.join(d, fname), "a") as f:
        for q in questions:
            qid = q.get("id") or question_id(q["question"], q["answer"], q["knowledge_point"])
            if qid in existing_ids:
                continue
            q["id"] = qid
            q["crawled_at"] = datetime.now().isoformat()
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
            existing_ids.add(qid)
            new_count += 1
    return new_count


# ─── Source Plugins ────────────────────────────────────────────

def crawl_open_textbook(subject: str, grade: str) -> list[dict]:
    """
    示例爬虫：从公开教材资源网抓取题目。
    实际部署时替换为真实数据源。
    目前返回空列表占位 — 后续接入真实爬取逻辑。
    """
    return []


def crawl_manual_bank(subject: str, grade: str) -> list[dict]:
    """
    加载手动准备的题目（存放在 question_bank/manual/ 下）。
    格式：{"knowledge_point":"三角形_三角形的内角和","question":"...","answer":"...","source":"manual"}
    """
    manual_dir = os.path.join(BANK_DIR, "manual", subject, grade)
    if not os.path.isdir(manual_dir):
        return []
    questions = []
    for fname in sorted(os.listdir(manual_dir)):
        if fname.endswith(".json") or fname.endswith(".jsonl"):
            path = os.path.join(manual_dir, fname)
            with open(path, errors="ignore") as f:
                if fname.endswith(".jsonl"):
                    for line in f:
                        try:
                            questions.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
                else:
                    data = json.load(f)
                    if isinstance(data, list):
                        questions.extend(data)
                    elif isinstance(data, dict):
                        questions.append(data)
    return questions


# ─── Main ──────────────────────────────────────────────────────

def crawl(subject: str = "math", grade: str = "grade_4"):
    print(f"[crawler] 开始爬取: {GRADE_MAP.get(grade, grade)} {SUBJECT_MAP.get(subject, subject)}")

    sources = [
        ("open_textbook", crawl_open_textbook),
        ("manual", crawl_manual_bank),
    ]

    total = 0
    for source_name, source_fn in sources:
        try:
            questions = source_fn(subject, grade)
            if questions:
                n = save_questions(subject, grade, questions, source_name)
                print(f"[crawler] {source_name}: 新增 {n} 道题")
                total += n
        except Exception as e:
            print(f"[crawler] {source_name} 失败: {e}")

    print(f"[crawler] 完成，共新增 {total} 道题")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="错题Pro题库爬虫")
    parser.add_argument("--subject", default="math", choices=["math", "english", "chinese"])
    parser.add_argument("--grade", default="grade_4", choices=list(GRADE_MAP.keys()))
    args = parser.parse_args()
    crawl(args.subject, args.grade)
