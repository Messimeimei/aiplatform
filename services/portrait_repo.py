# services/portrait_repo.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json
from typing import Dict, Any, List, Tuple, Optional

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# 允许的领域
_DOMAIN_KEYS = {"brain", "chip", "dialogue", "dl", "robot", "video"}

def _p(*parts) -> str:
    return os.path.join(*parts)

def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _files_for(domain: str) -> Tuple[str, str]:
    d = (domain or "").strip().lower()
    if d not in _DOMAIN_KEYS:
        raise ValueError(f"unknown domain: {domain}")
    return _p(DATA_DIR, f"relation_{d}.json"), _p(DATA_DIR, f"rank_table_{d}.json")

def _detail_map(detail_path: str) -> Dict[str, Dict[str, Any]]:
    m: Dict[str, Dict[str, Any]] = {}
    data = _load_json(detail_path) or []
    if isinstance(data, list):
        for rec in data:
            did = str(rec.get("id") or "").strip()
            if did:
                m[did] = rec
    return m

def _kind_from_type(t: str) -> str:
    t = (t or "").strip()
    if t in ("技术", "tech", "Technology"):
        return "tech"
    if t in ("产品", "product", "Product"):
        return "product"
    if t in ("企业", "company", "Company", "enterprise", "Enterprise"):
        return "company"
    if t in ("国家", "country", "Country"):
        return "country"
    return "other"

def _short(s: str, n: int = 140) -> str:
    if not s:
        return ""
    s = str(s).strip()
    return s if len(s) <= n else s[:n].rstrip() + "…"

def load_graph_for_domain(domain: str) -> Dict[str, Any]:
    """
    返回：
    {
      "nodes": [{id,name,kind,desc}],  # desc 来自 rank_table_*.json 的 abstract（截断）
      "edges": [{source,target,label}]
    }
    """
    rel_path, det_path = _files_for(domain)
    rel = _load_json(rel_path) or {}
    nodes = rel.get("nodes") or rel.get("Nodes") or []
    edges = rel.get("edges") or rel.get("Edges") or rel.get("links") or []

    id2detail = _detail_map(det_path)

    out_nodes: List[Dict[str, Any]] = []
    for n in nodes:
        nid   = n.get("id")
        name  = n.get("name") or nid
        kind  = _kind_from_type(n.get("type"))
        det   = id2detail.get(str(nid))
        desc  = _short((det or {}).get("abstract") or n.get("abstract") or "")
        out_nodes.append({
            "id": nid, "name": name, "kind": kind, "desc": desc
        })

    out_edges: List[Dict[str, Any]] = []
    for e in edges:
        out_edges.append({
            "source": e.get("source"),
            "target": e.get("target"),
            "label":  e.get("relation") or e.get("label") or ""
        })

    return {"nodes": out_nodes, "edges": out_edges}

def load_node_detail(domain: str, node_id: str) -> Optional[Dict[str, Any]]:
    """
    合并 relation 节点 + rank_table 详情（以 rank 为主）
    """
    rel_path, det_path = _files_for(domain)
    rel = _load_json(rel_path) or {}
    id2detail = _detail_map(det_path)

    det = id2detail.get(str(node_id))
    if det:
        return det

    # 回退：relation 里的节点
    nodes = rel.get("nodes") or rel.get("Nodes") or []
    for n in nodes:
        if str(n.get("id")) == str(node_id):
            return {
                "id": n.get("id"),
                "name": n.get("name") or n.get("id"),
                "type": n.get("type"),
                "field": n.get("field") or "",
                "country": n.get("country") or "",
                "enterprise": n.get("enterprise") or "",
                "year": n.get("year") or "",
                "abstract": n.get("abstract") or "",
                "source": []
            }
    return None
