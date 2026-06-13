"""
错题Pro - 本地认证模块
Phase 1-3 CLI阶段使用pbkdf2密码哈希。
Phase 4+ 服务端阶段替换为JWT。
"""

import hashlib
import os
import json

PROFILE_PATH = None  # 由 main.py 设置


def _hash_password(password: str) -> str:
    """pbkdf2_sha256 哈希"""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    """验证密码"""
    salt_hex, dk_hex = stored_hash.split(":")
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(dk_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)
    return actual == expected


def create_account(name: str, password: str, profile_data: dict) -> dict:
    """
    创建账号：写入 profile.json
    返回完整的 profile
    """
    profile_data["student_name"] = name
    profile_data["password_hash"] = _hash_password(password)

    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)
    return profile_data


def login(password: str) -> bool:
    """登录验证"""
    if not os.path.exists(PROFILE_PATH):
        return False
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = json.load(f)
    stored = profile.get("password_hash", "")
    if not stored:
        return False
    return _verify_password(password, stored)


def change_password(old_password: str, new_password: str) -> bool:
    """修改密码"""
    if not login(old_password):
        return False
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = json.load(f)
    profile["password_hash"] = _hash_password(new_password)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return True


def load_profile() -> dict | None:
    """读取当前用户配置"""
    if not os.path.exists(PROFILE_PATH):
        return None
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_profile(profile: dict) -> None:
    """保存用户配置"""
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def has_account() -> bool:
    """是否已有账号"""
    return os.path.exists(PROFILE_PATH)
