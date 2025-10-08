# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify
from services.graph_repo import get_items, get_detail, build_graph_for_domain, list_domains
from services.search_service import search_items
from services.detail_repo import get_detail_by_node_id, load_all_details  # 新增导入
from services.portrait_repo import load_graph_for_domain, load_node_detail

base_bp = Blueprint("base", __name__)

def _render(tpl, active=None, **ctx):
    return render_template(tpl, active=active, **ctx)

# ---------------- 页面 ----------------
@base_bp.route("/")
def index():
    # 提供给 index.html 的热词；前端样式/脚本不变
    hot_tags = [
        "光遗传学调控", "Tensor Cores", "ChatGPT",
        "模型压缩（Pruning）", "类人表情生成", "双向神经接口", "Sora"
    ]
    return _render("index.html", active="home", hot_tags=hot_tags)

@base_bp.route("/results")
def results_page():
    q = request.args.get("q", "") or ""
    type_ = (request.args.get("type", "tech") or "tech").strip().lower()
    if type_ not in ("tech", "product"):
        type_ = "tech"

    # ✅ 这里只在路由里调用搜索；不要在模块顶部调用！
    found = search_items(get_items(), q, type_)

    # 仅传模板需要的字段
    view_items = [
        {
            "id": it["id"],
            "name": it["name"],
            "kind": it["kind"],
            "org": it["org"],
            "date": it["date"],
            "abstract": it["abstract"],
        }
        for it in found
    ]
    return _render("results.html", active="results", items=view_items, q=q, type_=type_)

@base_bp.route("/detail/<int:item_id>")
def detail_page(item_id):
    """
    服务端渲染详情页（若你的 detail.html 里自己 fetch /api/detail，就不一定用到这些上下文）
    """
    # 1) 先在聚合卡片里把 item 找出来（拿到 _node_id）
    mp = {it["id"]: it for it in get_items()}
    base_item = mp.get(item_id)
    if not base_item:
        # 可渲染一个 404 模板；这里简单返回 detail.html 由前端再调用 /api/detail
        return _render("detail.html", active="results", item_id=item_id)

    node_id = base_item.get("_node_id", "")
    detail = get_detail_by_node_id(node_id) or {}

    # 2) 合并一些你模板可能会用到的字段（保持向后兼容）
    #    detail 文件里已有 name/type/field/abstract/year/source/enterprise/country 等
    ctx = {
        "item_id": item_id,
        "base_item": base_item,   # 卡片基础信息（name/kind等）
        "detail": detail          # 领域详细信息
    }
    return _render("detail.html", active="results", **ctx)




@base_bp.route("/portrait", defaults={"item_id": None})
@base_bp.route("/portrait/<int:item_id>")
def portrait_page(item_id):
    return _render("portrait.html", active="portrait", item_id=item_id)

@base_bp.route("/ranking")
def ranking_page():
    """
    读取 6 个 rank_table_*.json（detail_repo 已经聚合），
    根据 query 参数过滤并按 key_score 排序，把“技术/产品”分别传给模板。
    """
    # 查询参数
    year_q  = request.args.get("year", "").strip()
    field_q = request.args.get("field", "").strip()  # 例如：'脑机接口'、'芯片'、'全部' 等

    # 读取所有详细记录：{detail_id -> dict}
    all_recs_map = load_all_details()
    all_recs = list(all_recs_map.values())

    # 过滤：仅保留有 name / key_score 的条目
    def norm_type(t):
        t = (t or "").strip().lower()
        if t in ("技术", "tech", "technology"): return "tech"
        if t in ("产品", "product"): return "product"
        return ""

    def ok_year(rec):
        if not year_q:
            return True
        try:
            return str(rec.get("year", "")).strip() == str(year_q)
        except Exception:
            return False

    def ok_field(rec):
        if not field_q or field_q == "全部":
            return True
        return (rec.get("field") or "").strip() == field_q

    def score_of(rec):
        # 主用 key_score；没有就用三项均值兜底
        ks = rec.get("key_score")
        if isinstance(ks, (int, float)):
            return float(ks)
        parts = [rec.get("article_score"), rec.get("patent_score"), rec.get("report_score")]
        parts = [float(x) for x in parts if isinstance(x, (int, float))]
        return sum(parts) / len(parts) if parts else 0.0

    # 拆成 技术 / 产品 两组
    tech_rows = []
    prod_rows = []
    for rec in all_recs:
        t = norm_type(rec.get("type"))
        if not t:
            continue
        if not rec.get("name"):
            continue
        if not ok_year(rec) or not ok_field(rec):
            continue
        s = score_of(rec)
        row = {
            "id": rec.get("id"),
            "name": rec.get("name"),
            "field": rec.get("field"),
            "year": rec.get("year"),
            "key_score": s,
        }
        (tech_rows if t == "tech" else prod_rows).append(row)

    # 排序：key_score 降序
    tech_rows.sort(key=lambda r: r["key_score"], reverse=True)
    prod_rows.sort(key=lambda r: r["key_score"], reverse=True)

    # 传入模板
    return _render(
        "ranking.html",
        active="ranking",
        items_tech=tech_rows,   # 取前 100（可自行调整）
        items_prod=prod_rows,
    )

# ---------------- API ----------------
@base_bp.route("/api/detail/<int:item_id>")
def api_detail(item_id):
    """
    供前端 JS 使用的详情接口：
    - 优先用 rank_table_*.json 的详细数据
    - 找不到时，回退为卡片基础信息拼一个极简结构
    """
    mp = {it["id"]: it for it in get_items()}
    base_item = mp.get(item_id)
    if not base_item:
        return jsonify({"error": "not_found"}), 404

    node_id = base_item.get("_node_id", "")
    det = get_detail_by_node_id(node_id) or {}

    # 统一返回结构（尽量覆盖 detail 文件里的字段；没有就回退）
    payload = {
        "id": det.get("id") or node_id or item_id,
        "name": det.get("name") or base_item.get("name"),
        "type": det.get("type") or base_item.get("kind"),
        "field": det.get("field") or "—",
        "country": det.get("country") or base_item.get("org") or "—",
        "enterprise": det.get("enterprise") or "—",
        "year": det.get("year") or "—",
        "abstract": det.get("abstract") or base_item.get("abstract") or "",
        "article_score": det.get("article_score"),
        "patent_score": det.get("patent_score"),
        "report_score": det.get("report_score"),
        "key_score": det.get("key_score"),
        "source": det.get("source") or [],

        # 也把卡片端拼过来的汇总行放在 extra 里（模板备用）
        "extra": {
            "kind": base_item.get("kind"),
            "org_summary": base_item.get("org"),
            "source_file": base_item.get("_source")
        }
    }
    return jsonify(payload)

# 1) 领域列表
@base_bp.route("/api/domains", endpoint="domains_list")
def api_domains_list():
    return jsonify(list_domains())

# 2) 按领域返回图谱
@base_bp.route("/api/graph", endpoint="graph_by_domain")
def api_graph_by_domain():
    domain = (request.args.get("domain") or "").strip().lower()
    if not domain:
        domains = list_domains()
        domain = domains[0]["key"] if domains else ""
    return jsonify(build_graph_for_domain(domain))

# 3) 节点详情（按节点ID）
@base_bp.route("/api/node/<path:node_id>", endpoint="node_detail_by_id")
def api_node_detail_by_id(node_id):
    det = get_detail_by_node_id(node_id)
    if det:
        return jsonify(det)
    return jsonify({
        "id": node_id,
        "name": node_id,
        "type": "node",
        "abstract": "",
        "source": []
    })


# —— 新：按领域+节点ID取详情（点击节点时用）——
@base_bp.route("/api/portrait_graph")
def api_portrait_graph():
    domain = (request.args.get("domain","") or "").strip().lower()
    try:
        data = load_graph_for_domain(domain)
    except Exception as e:
        return jsonify({"error":"bad_domain","message":str(e)}), 400
    return jsonify(data)

@base_bp.route("/api/portrait_node_detail")
def api_portrait_node_detail():
    domain  = (request.args.get("domain","") or "").strip().lower()
    node_id = (request.args.get("node_id","") or "").strip()
    if not domain or not node_id:
        return jsonify({"error":"missing_params"}), 400
    det = load_node_detail(domain, node_id)
    if not det:
        return jsonify({"error":"not_found"}), 404
    return jsonify(det)
