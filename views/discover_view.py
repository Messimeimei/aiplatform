# views/discover_view.py
import os
from flask import Blueprint, render_template, request, jsonify
from services.intelligent_discovery import intelligent_discovery

discover_bp = Blueprint("discover", __name__)

# ---------- 页面路由 ----------
@discover_bp.get("/identify")
def identify_page():
    return render_template("identify.html", active="discover")


# ---------- API：智发现 ----------
@discover_bp.post("/api/identify")
def api_identify():
    """
    智发现接口：支持文本和文件两种模式
    mode='text' 传 JSON {mode:'text', text:'...'}
    mode='file' 上传 FormData {mode:'file', file:...}
    """
    try:
        mode = None
        if request.is_json:
            mode = request.json.get("mode")
        elif "mode" in request.form:
            mode = request.form.get("mode")

        if mode == "text":
            text = request.json.get("text", "").strip()
            if not text:
                return jsonify({"error": "empty_text"}), 400
            result = intelligent_discovery(text, "/app/data")

        elif mode == "file":
            if "file" not in request.files:
                return jsonify({"error": "missing_file"}), 400
            file = request.files["file"]
            save_path = os.path.join("static", "uploads", file.filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            result = intelligent_discovery(save_path, "/app/data")

        else:
            return jsonify({"error": "invalid_mode"}), 400

        return jsonify({
            "tech": result.get("key_tech_found", []),
            "product": result.get("key_products_found", []),
            "raw_tech": result.get("all_tech_words", []),
            "raw_product": result.get("all_product_words", []),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
