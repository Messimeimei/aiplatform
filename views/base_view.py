# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify
from services.graph_repo import get_items, get_detail
from services.search_service import search_items
from services.detail_repo import get_detail_by_node_id  # 新增导入

base_bp = Blueprint("base", __name__)

def _render(tpl, active=None, **ctx):
    return render_template(tpl, active=active, **ctx)

# ---------------- 页面 ----------------
@base_bp.route("/")
def index():
    # 提供给 index.html 的热词；前端样式/脚本不变
    hot_tags = [
        "脑电图信号处理", "多模态脑信号融合", "低功耗接口芯片",
        "可穿戴EEG", "深度学习神经解码", "双向神经接口", "云端BCI平台"
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
    return _render("ranking.html", active="ranking")

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