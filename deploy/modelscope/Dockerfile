# 魔搭创空间（Docker 类型）：平台把 7860 端口作为对外入口。
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

COPY requirements.txt .
RUN pip install --retries 3 -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com -r requirements.txt

COPY . .

# 部署时还原正文树（幂等，只补缺）。线上问答不读它，加这行只为容器里能跑
# tools/build_kb_db.py 与 tools/check_quotes.py；解不出来就让它把构建顶失败，别静默缺文件。
RUN python tools/extract_sources.py

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
