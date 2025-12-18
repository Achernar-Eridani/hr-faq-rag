# 1. 使用官方轻量级 Python 镜像
FROM python:3.10-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 设置环境变量：防止生成 pyc 文件，让日志实时打印
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. 安装系统基础依赖 (
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. 先复制 requirements.txt 并安装，利用 Docker 缓存层加速构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 6. 复制项目所有代码到镜像中
COPY . .

# 7. 暴露 8000 端口
EXPOSE 8000

# 8. 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]