# services/detail_repo.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, glob, unicodedata
from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# 可用环境变量覆盖详细文件清单，例如：
# DETAIL_FILES="data/rank_table_video.json,data/rank_table_brain.json"
ENV_DETAIL_FILES = os.getenv("DETAIL_FILES", "").strip()

def _discover_detail_files() -> List[str]:
    if ENV_DETAIL_FILES:
        files = [p.strip() for p in ENV_DETAIL_FILES.split(",") if p.strip()]
        return [p if os.path.isabs(p) else os.path.join(ROOT_DIR, p) for p in files]
    # 默认扫描 6 大领域的 rank_table_*.json
    return sorted(glob.glob(os.path.join(DATA_DIR, "rank_table_*.json")))

def _safe_norm(s: str) -> str:
    try:
        return unicodedata.normalize("NFKC", (s or "")).strip()
    except Exception:
        return (s or "").strip()

@lru_cache(maxsize=1)
def load_all_details() -> Dict[str, Dict[str, Any]]:
    """
    返回 {detail_id -> 详细记录dict}
    例如 detail_id= 'tech_video001' 或 'prod_video001' 等。
    """
    id2detail: Dict[str, Dict[str, Any]] = {}
    files = _discover_detail_files()
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if isinstance(data, list):
            for rec in data:
                did = _safe_norm(rec.get("id"))
                if did:
                    id2detail[did] = rec
    # 可观测一次
    print("[DetailRepo] Loaded detail files:", ", ".join([os.path.basename(p) for p in files]))
    print("[DetailRepo] Total detail records:", len(id2detail))
    return id2detail

def get_detail_by_node_id(node_id: str) -> Optional[Dict[str, Any]]:
    """根据节点/详细记录 id（如 tech_video001）取详细信息。"""
    if not node_id:
        return None
    return load_all_details().get(_safe_norm(node_id))
