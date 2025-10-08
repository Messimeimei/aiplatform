# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, glob, unicodedata, re
from typing import Dict, Any, List, Optional, Tuple, Set
from functools import lru_cache
from services.detail_repo import load_all_details  # 复用你已有的索引

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
ENV_GRAPH_FILES = os.getenv("GRAPH_FILES", "").strip()

TECH_TYPES = {"技术", "tech", "Technology"}
PROD_TYPES = {"产品", "product", "Product"}
COMP_TYPES = {"企业", "company", "Company", "enterprise", "Enterprise"}
COUNTRY_TYPES = {"国家", "country", "Country"}

RELATION_GLOB = os.getenv("RELATION_GLOB", os.path.join(DATA_DIR, "relation_*.json"))
RANK_GLOB = os.getenv("RANK_GLOB", os.path.join(DATA_DIR, "rank_table_*.json"))


def _norm(s: str) -> str:
    try:
        return unicodedata.normalize("NFKC", (s or "")).lower().strip()
    except Exception:
        return (s or "").lower().strip()


def _discover_files(glob_pat: str) -> List[str]:
    if ENV_GRAPH_FILES:
        # 兼容旧环境变量：GRAPH_FILES 里也可能混着 rank/relations；都加载
        files = [p.strip() for p in ENV_GRAPH_FILES.split(",") if p.strip()]
        return [p if os.path.isabs(p) else os.path.join(ROOT_DIR, p) for p in files]
    return sorted(glob.glob(glob_pat))


def _safe_load(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"nodes": [], "edges": [], "rows": []}
    if not isinstance(data, dict) and not isinstance(data, list):
        return {"nodes": [], "edges": [], "rows": []}

    # 关系文件
    if isinstance(data, dict) and ("nodes" in data or "edges" in data or "links" in data):
        nodes = data.get("nodes") or data.get("Nodes") or []
        edges = data.get("edges") or data.get("Edges") or data.get("links") or []
        return {"nodes": nodes, "edges": edges, "rows": []}

    # rank 表：可能是 list 或 dict.rows
    if isinstance(data, list):
        return {"nodes": [], "edges": [], "rows": data}
    if isinstance(data, dict):
        rows = data.get("rows") or data.get("data") or []
        return {"nodes": [], "edges": [], "rows": rows}

    return {"nodes": [], "edges": [], "rows": []}


@lru_cache(maxsize=1)
def load_all() -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, Dict[str, Any]]]]:
    rel_files = _discover_files(RELATION_GLOB)
    rank_files = _discover_files(RANK_GLOB)
    relations = [(os.path.basename(fp), _safe_load(fp)) for fp in rel_files]
    ranks = [(os.path.basename(fp), _safe_load(fp)) for fp in rank_files]
    print("[GraphRepo] Relations:", ", ".join([n for n, _ in relations]) or "(none)")
    print("[GraphRepo] Ranks:", ", ".join([n for n, _ in ranks]) or "(none)")
    return relations, ranks


def _node_name(id2node: Dict[str, Dict[str, Any]], node_id: Optional[str]) -> str:
    if not node_id:
        return "-"
    return (id2node.get(node_id, {}) or {}).get("name") or str(node_id)


def _chips_html(label: str, names: List[str]) -> str:
    if not names:
        return ""
    chips = "".join([f'<span class="chip" title="{n}">{n}</span>' for n in names])
    return f'<div class="meta-line"><span class="meta-label">{label}</span>{chips}</div>'


@lru_cache(maxsize=1)
def build_items_from_graphs() -> List[Dict[str, Any]]:
    relations, ranks = load_all()

    # ------- 预索引 rank：按 id 存，便于合并 -------
    rank_by_id: Dict[str, Dict[str, Any]] = {}
    id_source_map: Dict[str, str] = {}
    for src_name, pkt in ranks:
        for r in pkt.get("rows", []):
            rid = r.get("id") or r.get("ID")
            if not rid:
                continue
            rank_by_id[rid] = r
            id_source_map[rid] = src_name

    items: List[Dict[str, Any]] = []
    auto_inc = 1000

    # ------- 遍历 relation_* 构建基础卡片 -------
    for source_name, g in relations:
        nodes, edges = g["nodes"], g["edges"]
        id2node = {n.get("id"): n for n in nodes if n.get("id")}

        # 关系索引
        product_to_companies: Dict[str, Set[str]] = {}
        company_to_countries: Dict[str, Set[str]] = {}
        product_to_techs: Dict[str, Set[str]] = {}

        for e in edges:
            rel = e.get("relation") or ""
            s, t = e.get("source"), e.get("target")
            if not s or not t:
                continue
            if rel == "产品-归属-企业":
                product_to_companies.setdefault(s, set()).add(t)
            elif rel == "企业-归属-国家":
                company_to_countries.setdefault(s, set()).add(t)
            elif rel == "产品-应用-技术":
                product_to_techs.setdefault(s, set()).add(t)

        # 技术
        for n in nodes:
            t = (n.get("type") or "").strip()
            if t in TECH_TYPES:
                name = n.get("name", "")
                rid = n.get("id")
                row = rank_by_id.get(rid, {})  # ★ 合并 rank
                # 别名（rank 名称不同）
                aliases = []
                rname = row.get("name")
                if rname and rname != name:
                    aliases.append(rname)

                items.append({
                    "id": auto_inc,
                    "name": name,
                    "kind": "关键技术",
                    "org": "-",
                    "date": "—",
                    "abstract": row.get("abstract") or f"技术要点：{name}",
                    "_node_id": rid,
                    "_source": row and id_source_map.get(rid, source_name) or source_name,
                    "_aliases": aliases,
                    "_scores": {
                        "article": row.get("article_score"),
                        "patent": row.get("patent_score"),
                        "report": row.get("report_score"),
                        "key": row.get("key_score"),
                    },
                    "_meta": {
                        "field": row.get("field"),
                        "country": row.get("country"),
                        "enterprise": row.get("enterprise"),
                        "year": row.get("year"),
                        "source": row.get("source"),
                    }
                })
                auto_inc += 1

        # 产品
        for n in nodes:
            t = (n.get("type") or "").strip()
            if t in PROD_TYPES:
                pid = n.get("id")
                name = n.get("name", "")

                comp_ids = sorted(product_to_companies.get(pid, set()))
                comp_names = [_node_name(id2node, cid) for cid in comp_ids]

                country_ids: Set[str] = set()
                for cid in comp_ids:
                    country_ids |= company_to_countries.get(cid, set())
                country_names = [_node_name(id2node, c) for c in sorted(country_ids)]

                tech_ids = sorted(product_to_techs.get(pid, set()))
                tech_names = [_node_name(id2node, tid) for tid in tech_ids]

                lines = []
                if comp_names:
                    lines.append(_chips_html("企业", comp_names))
                if country_names:
                    lines.append(_chips_html("国家", country_names))
                if tech_names:
                    lines.append(_chips_html("技术", tech_names))
                org_html = "".join(lines) if lines else "-"

                row = rank_by_id.get(pid, {})
                aliases = []
                rname = row.get("name")
                if rname and rname != name:
                    aliases.append(rname)

                # rank 里补企业/国家（没有关系也能显示）
                r_comp = row.get("enterprise")
                r_country = row.get("country")
                if r_comp and r_comp not in comp_names:
                    comp_names.append(r_comp)
                    org_html = _chips_html("企业", comp_names) + (
                        _chips_html("国家", country_names) if country_names else "") + (
                                   _chips_html("技术", tech_names) if tech_names else "")
                if r_country and r_country not in country_names:
                    country_names.append(r_country)
                    org_html = _chips_html("企业", comp_names) + _chips_html("国家", country_names) + (
                        _chips_html("技术", tech_names) if tech_names else "")

                items.append({
                    "id": auto_inc,
                    "name": name,
                    "kind": "关键产品",
                    "org": org_html,
                    "date": "—",
                    "abstract": row.get("abstract") or "",
                    "_node_id": pid,
                    "_source": row and id_source_map.get(pid, source_name) or source_name,
                    "_companies": comp_names,
                    "_countries": country_names,
                    "_techs": tech_names,
                    "_aliases": aliases,
                    "_scores": {
                        "article": row.get("article_score"),
                        "patent": row.get("patent_score"),
                        "report": row.get("report_score"),
                        "key": row.get("key_score"),
                    },
                    "_meta": {
                        "field": row.get("field"),
                        "country": r_country or (country_names[0] if country_names else None),
                        "enterprise": r_comp or (comp_names[0] if comp_names else None),
                        "year": row.get("year"),
                        "source": row.get("source"),
                    }
                })
                auto_inc += 1

        # 企业
        for n in nodes:
            t = (n.get("type") or "").strip()
            if t in COMP_TYPES:
                name = n.get("name", "")
                rid = n.get("id")
                cset = company_to_countries.get(rid, set())
                countries = [_node_name(id2node, c) for c in sorted(cset)]
                org_html = _chips_html("国家", countries) if countries else "-"
                row = rank_by_id.get(rid, {})
                items.append({
                    "id": auto_inc,
                    "name": name,
                    "kind": "企业",
                    "org": org_html,
                    "date": "—",
                    "abstract": row.get("abstract") or f"企业：{name}",
                    "_node_id": rid,
                    "_source": row and id_source_map.get(rid, source_name) or source_name,
                    "_aliases": [row.get("name")] if row.get("name") and row.get("name") != name else [],
                })
                auto_inc += 1

        # 国家
        for n in nodes:
            t = (n.get("type") or "").strip()
            if t in COUNTRY_TYPES:
                name = n.get("name", "") or n.get("id") or "国家"
                rid = n.get("id")
                row = rank_by_id.get(rid, {})
                items.append({
                    "id": auto_inc,
                    "name": name,
                    "kind": "国家",
                    "org": "-",
                    "date": "—",
                    "abstract": row.get("abstract") or f"国家：{name}",
                    "_node_id": rid,
                    "_source": row and id_source_map.get(rid, source_name) or source_name,
                    "_aliases": [row.get("name")] if row.get("name") and row.get("name") != name else [],
                })
                auto_inc += 1

    # ------- rank-only：relation 中没有出现过的 id 也要建卡 -------
    existing_ids = {it.get("_node_id") for it in items if it.get("_node_id")}

    def _infer_kind(rk: Dict[str, Any]) -> str:
        t = _norm(rk.get("type") or "")
        if t in TECH_TYPES: return "关键技术"
        if t in PROD_TYPES: return "关键产品"
        return "关键产品" if rk.get("enterprise") else "关键技术"

    for rid, rk in rank_by_id.items():
        if rid in existing_ids:
            # 已在 relation 中建卡：把 rank 名字作为别名追加到对应卡片（确保可检索）
            for it in items:
                if it.get("_node_id") == rid:
                    aliases = it.setdefault("_aliases", [])
                    if rk.get("name") and rk["name"] not in aliases and rk["name"] != it.get("name"):
                        aliases.append(rk["name"])
                    # 也可补全抽象
                    if not it.get("abstract") and rk.get("abstract"):
                        it["abstract"] = rk["abstract"]
                    break
            continue

        kind = _infer_kind(rk)
        name = rk.get("name") or rid
        org_html = "-"
        comp_names, country_names = [], []
        if kind == "关键产品":
            if rk.get("enterprise"): comp_names.append(rk["enterprise"])
            if rk.get("country"):    country_names.append(rk["country"])
            lines = []
            if comp_names:    lines.append(_chips_html("企业", comp_names))
            if country_names: lines.append(_chips_html("国家", country_names))
            org_html = "".join(lines) if lines else "-"

        items.append({
            "id": auto_inc,
            "name": name,
            "kind": kind,
            "org": org_html,
            "date": "—",
            "abstract": rk.get("abstract") or "",
            "_node_id": rid,
            "_source": id_source_map.get(rid, ""),
            "_companies": comp_names,
            "_countries": country_names,
            "_aliases": [],
        })
        auto_inc += 1

    # 稳定排序
    items.sort(key=lambda it: (it["kind"], _norm(it["name"])))
    return items


def get_items() -> List[Dict[str, Any]]:
    return build_items_from_graphs()


def get_detail(item_id: int) -> Optional[Dict[str, Any]]:
    mp = {it["id"]: it for it in get_items()}
    it = mp.get(item_id)
    if not it:
        return None
    # 从 _meta/_scores 提取可用信息
    meta = it.get("_meta") or {}
    srcs = it.get("_meta", {}).get("source") or []
    if isinstance(srcs, str): srcs = [srcs]
    return {
        "id": it["id"],
        "name": it["name"],
        "type": it.get("kind"),
        "kind": it.get("kind"),
        "field": meta.get("field") or "—",
        "country": meta.get("country") or "—",
        "enterprise": meta.get("enterprise"),
        "year": meta.get("year") or "—",
        "abstract": it.get("abstract") or "",
        "relatedTech": it.get("_techs", []),
        "relatedProduct": [],
        "images": [],
        "metrics": {
            "论文得分": (it.get("_scores") or {}).get("article"),
            "专利得分": (it.get("_scores") or {}).get("patent"),
            "报告得分": (it.get("_scores") or {}).get("report"),
            "关键度": (it.get("_scores") or {}).get("key"),
        },
        "sources": [{"name": "来源文件", "url": it.get("_source", "")}] + \
                   ([{"name": "rank 来源", "url": u} for u in srcs if u] if srcs else [])
    }


def invalidate_cache():
    load_all.cache_clear()
    build_items_from_graphs.cache_clear()


def _norm_type_portrait(t: str) -> str:
    t = (t or "").strip()
    if t in TECH_TYPES:    return "tech"
    if t in PROD_TYPES:    return "product"
    if t in COMP_TYPES:    return "company"
    if t in COUNTRY_TYPES: return "country"
    return "node"


def _domain_of(filename: str) -> str:
    base = os.path.splitext(filename)[0]
    return base.replace("relation_", "").replace("rank_table_", "")


@lru_cache(maxsize=1)
def _load_all_relations() -> List[Tuple[str, Dict[str, Any]]]:
    files = sorted(glob.glob(RELATION_GLOB))
    out: List[Tuple[str, Dict[str, Any]]] = []
    for fp in files:
        out.append((os.path.basename(fp), _safe_load_relation(fp)))
    # 可选：启动时打印一下
    print("[GraphRepo] Relations:", ", ".join([n for n, _ in out]))
    return out


def build_graph_for_portrait() -> Dict[str, Any]:
    """
    画像页图谱：
    - 合并所有 relation_*.json 的 nodes/edges（按 id 去重）
    - 节点结构：{id,name,type(tech/product/company/country),aliases[],abstract,domain,score}
    - 若 rank 索引里有相同 id，则把 rank.name 进 aliases，abstract/score 补充进去
    """
    rels = _load_all_relations()
    rank_idx = load_all_details()  # {id -> 详情}

    id2node: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    for fname, pkt in rels:
        domain = _domain_of(fname)
        for n in pkt["nodes"]:
            nid = n.get("id")
            if not nid:
                continue
            if nid not in id2node:
                id2node[nid] = {
                    "id": nid,
                    "name": n.get("name") or nid,
                    "type": _norm_type_portrait(n.get("type")),
                    "aliases": [],
                    "abstract": "",
                    "domain": domain,
                    "score": None,
                }
            else:
                # 同一 id 在多个文件有不同的 name -> 收到 aliases
                nm = n.get("name")
                if nm and nm != id2node[nid]["name"] and nm not in id2node[nid]["aliases"]:
                    id2node[nid]["aliases"].append(nm)

        for e in pkt["edges"]:
            s, t = e.get("source"), e.get("target")
            if not s or not t:
                continue
            edges.append({
                "source": s,
                "target": t,
                "relation": e.get("relation") or e.get("label") or "",
                "domain": domain,
            })

    # 融合 rank 详情
    for nid, node in id2node.items():
        det = rank_idx.get(nid)
        if not det:
            continue
        rname = det.get("name")
        if rname and rname != node["name"] and rname not in node["aliases"]:
            node["aliases"].append(rname)
        node["abstract"] = det.get("abstract") or node["abstract"]
        node["score"] = det.get("key_score") or det.get("article_score")

    return {"nodes": list(id2node.values()), "edges": edges}


def invalidate_portrait_cache():
    _load_all_relations.cache_clear()


from functools import lru_cache
from typing import List, Dict, Any, Tuple
from services.detail_repo import load_all_details  # 直接用你现成的详情索引

_DOMAIN_FILE_MAP_CACHE: Dict[str, str] = {}  # {domain_key: relation_file_abs_path}


def _discover_relation_files() -> List[str]:
    pat = os.path.join(DATA_DIR, "relation_*.json")
    return sorted(glob.glob(pat))


def _domain_key_from_filename(filename: str) -> str:
    base = os.path.splitext(os.path.basename(filename))[0]  # relation_brain
    return base.replace("relation_", "", 1)


def _safe_load_relation(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"nodes": [], "edges": []}
    nodes = data.get("nodes") or data.get("Nodes") or []
    edges = data.get("edges") or data.get("Edges") or data.get("links") or []
    return {"nodes": nodes, "edges": edges}


def list_domains() -> List[Dict[str, str]]:
    """
    返回可用领域列表：[{key:'brain', name:'脑机接口'},{...}]
    name 只是友好名，默认用 key；你也可以按需映射。
    """
    global _DOMAIN_FILE_MAP_CACHE
    _DOMAIN_FILE_MAP_CACHE = {}
    out = []
    for fp in _discover_relation_files():
        key = _domain_key_from_filename(fp)
        _DOMAIN_FILE_MAP_CACHE[key] = fp
        out.append({"key": key, "name": key})  # 需要中文名可以自己映射
    return out


def _norm_portrait_type(t: str) -> str:
    t = (t or "").strip()
    if t in TECH_TYPES:    return "tech"
    if t in PROD_TYPES:    return "product"
    if t in COMP_TYPES:    return "company"
    if t in COUNTRY_TYPES: return "country"
    return "node"


@lru_cache(maxsize=16)
def build_graph_for_domain(domain_key: str) -> Dict[str, Any]:
    """
    只加载一个领域：relation_{domain}.json
    节点合并详情 rank_table_{domain}.json（通过 detail_repo 的总索引自动命中）
    """
    # 找文件
    if not _DOMAIN_FILE_MAP_CACHE:
        list_domains()  # 填充缓存
    fp = _DOMAIN_FILE_MAP_CACHE.get(domain_key)
    if not fp or not os.path.exists(fp):
        # 兜底：空图
        return {"domain": domain_key, "nodes": [], "edges": []}

    # 关系
    rel = _safe_load_relation(fp)
    nodes_raw, edges_raw = rel["nodes"], rel["edges"]

    # 详情索引（全局一次加载，里面自然包含 rank_table_{domain}.json）
    id2detail = load_all_details()

    # 汇总
    id2node: Dict[str, Dict[str, Any]] = {}
    for n in nodes_raw:
        nid = n.get("id")
        if not nid:
            continue
        if nid not in id2node:
            id2node[nid] = {
                "id": nid,
                "name": n.get("name") or nid,
                "type": _norm_portrait_type(n.get("type")),
                "aliases": [],
                "abstract": "",
            }
        else:
            alt = n.get("name")
            if alt and alt != id2node[nid]["name"] and alt not in id2node[nid]["aliases"]:
                id2node[nid]["aliases"].append(alt)

    # 融合 rank 详情（只补已有 relation 节点）
    for nid, node in id2node.items():
        det = id2detail.get(nid)
        if not det:
            continue
        rname = det.get("name")
        if rname and rname != node["name"] and rname not in node["aliases"]:
            node["aliases"].append(rname)
        if det.get("abstract"):
            node["abstract"] = det["abstract"]

    edges = []
    for e in edges_raw:
        s, t = e.get("source"), e.get("target")
        if not s or not t:
            continue
        edges.append({
            "source": s,
            "target": t,
            "relation": e.get("relation") or e.get("label") or ""
        })

    return {
        "domain": domain_key,
        "nodes": list(id2node.values()),
        "edges": edges
    }
