# 基础镜像
FROM python:3.10-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libxml2 libxslt1-dev poppler-utils \
  && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# 复制所有代码
COPY . .

# 数据目录 & 持久化挂载点
RUN mkdir -p /data /app/static/uploads
VOLUME ["/data"]

EXPOSE 8000
CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","app:app"]
