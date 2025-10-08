# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import re, unicodedata

def norm(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", str(text)).lower().strip()

_TAG_RE = re.compile(r"<[^>]+>")

def _strip_tags(s: str) -> str:
    return _TAG_RE.sub("", s or "")

def _kind_ok(it: Dict, type_: str) -> bool:
    k = it.get("kind")
    if (type_ or "tech") == "product":
        return k == "关键产品"
    return k == "关键技术"

def search_items(items: List[Dict], q: str, type_: str) -> List[Dict]:
    base = [it for it in items if _kind_ok(it, type_)]
    qn = norm(q)
    if not qn:
        return base
    res = []
    for it in base:
        aliases = it.get("_aliases") or []
        hay_parts = [
            it.get("name",""),
            _strip_tags(it.get("org","")),
            it.get("abstract",""),
            " ".join(aliases),
            str(it.get("_node_id") or ""),
            str(it.get("id") or ""),
        ]
        if qn in norm(" ".join(hay_parts)):
            res.append(it)
    return res
