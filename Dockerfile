# 运行层
FROM python:3.11-slim

# 基础依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# 工作目录
WORKDIR /app

# 仅复制依赖清单以利用缓存
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目
COPY . /app

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# 启动命令（Flask通常 app:app 为 WSGI 入口）
# 如 app.py 里是 app = Flask(__name__)
CMD ["python", "-c", "import os; print('Tip: use gunicorn in production'); import app; app.app.run(host='0.0.0.0', port=int(os.getenv('PORT',8000)))"]
# 生产建议：改为 gunicorn（更稳）
# CMD ["gunicorn", "-w", "2", "-k", "gthread", "-b", "0.0.0.0:8000", "app:app"]
