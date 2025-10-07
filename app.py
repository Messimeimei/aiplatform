import os

from flask import Flask
from views.base_view import base_bp
from views.discover_view import discover_bp

app = Flask(__name__, static_folder="static", template_folder="templates")

# 注册蓝图
app.register_blueprint(base_bp)
app.register_blueprint(discover_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
