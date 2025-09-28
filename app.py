import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, static_folder="static", template_folder="templates")

def _render(tpl, active=None, **ctx):
    return render_template(tpl, active=active, **ctx)

# —— 演示用的“数据库” —— #
DEMO_ITEMS = [
    {"id": 101, "name": "多模态",     "kind": "关键技术", "org": "示例机构A", "date": "2025-08",
     "abstract": "多模态融合感知与表征，包含视觉/文本/语音等模态的联合建模。"},
    {"id": 202, "name": "智能体平台", "kind": "关键产品", "org": "示例企业B", "date": "2025-07",
     "abstract": "可编排 Agent 能力平台，支持多工具协同与自动化执行。"},
    {"id": 303, "name": "知识蒸馏",   "kind": "关键技术", "org": "示例实验室C", "date": "2025-06",
     "abstract": "将大模型知识迁移到小模型，保持精度的同时显著提效降本。"},
]
DEMO_DETAIL = {
    101: {
        "id": 101, "name": "多模态", "kind": "关键技术", "field": "多模态", "country": "CN", "year": 2025,
        "abstract": "多模态（vision+text+audio）融合感知与表征，常见于跨模态检索、VQA 等。",
        "metrics": {"论文数": 128, "引用": 5280, "机构数": 36},
        "images": ["/static/hero-bg.jpg"],
        "relatedTech": ["跨模态对齐", "检索增强", "对比学习"],
        "relatedProduct": ["多模态识别平台", "智能体平台"],
        "sources": [{"name": "示例百科", "url": "https://example.com/wiki"}]
    },
    202: {
        "id": 202, "name": "智能体平台", "kind": "关键产品", "field": "智能体", "country": "CN", "year": 2025,
        "abstract": "可编排的 Agent 平台，支持工具调用、记忆与反思、流程自动化。",
        "metrics": {"企业部署": 42, "平均节省人力(%)": 37},
        "images": [],
        "relatedTech": ["规划-执行-反思", "RAG", "工具调用"],
        "relatedProduct": ["企业知识库", "流程自动化套件"],
        "sources": [{"name": "官网", "url": "https://example.com/agent"}]
    },
    303: {
        "id": 303, "name": "知识蒸馏", "kind": "关键技术", "field": "模型压缩", "country": "US", "year": 2024,
        "abstract": "将大模型的 soft targets 转移给学生模型，常与量化/剪枝结合以部署在边缘端。",
        "metrics": {"论文数": 96, "开源实现": 18},
        "images": [],
        "relatedTech": ["量化", "剪枝", "蒸馏数据合成"],
        "relatedProduct": ["边缘推理引擎"],
        "sources": [{"name": "论文合集", "url": "https://example.com/papers"}]
    }
}

# ── 页面路由 ────────────────────────────────
@app.get("/")
def index():
    return _render("index.html", active="home")

@app.get("/results")
def results_page():
    q = request.args.get("q", "")
    type_ = request.args.get("type", "tech")
    # TODO: 替换 DEMO_ITEMS 为你的检索结果（保证每条有 id）
    return _render("results.html", active="results", items=DEMO_ITEMS, q=q, type_=type_)

# 详情页（模板异步拉 /api/detail/<id>）
@app.get("/detail/<int:item_id>")
def detail_page(item_id):
    return _render("detail.html", active="results", item_id=item_id)

# ✅ 画像页：item_id 可选
@app.get("/portrait", defaults={"item_id": None})
@app.get("/portrait/<int:item_id>")
def portrait_page(item_id):
    # 这里可以根据是否有 item_id 做不同渲染
    return _render("portrait.html", active="portrait", item_id=item_id)

@app.get("/identify")
def identify_page():
    return _render("identify.html", active="discover")

@app.get("/ranking")
def ranking_page():
    return _render("ranking.html", active="ranking")

# ── API：详情（供 detail.html 拉数据） ────────────────────────────────
@app.get("/api/detail/<int:item_id>")
def api_detail(item_id):
    d = DEMO_DETAIL.get(item_id)
    if not d:
        return jsonify({"error": "not_found"}), 404
    return jsonify(d)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
