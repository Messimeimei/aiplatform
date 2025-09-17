import os
from flask import Flask, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

def _render(tpl, active=None, **ctx):
    return render_template(tpl, active=active, **ctx)

# ── 页面路由 ────────────────────────────────
@app.get("/")
def index():
    return _render("index.html", active="home")

@app.get("/results")
def results_page():
    return _render("results.html", active="results")

@app.get("/identify")
def identify_page():
    return _render("identify.html", active="discover")

@app.get("/portrait")
def portrait_page():
    return render_template("portrait.html", active="portrait")


@app.get("/ranking")
def ranking_page():
    return _render("ranking.html", active="ranking")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)
