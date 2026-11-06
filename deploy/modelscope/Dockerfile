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

# 部署时还原正文树（幂等，只补缺）。线上问答不读它，还原出来只为容器里能跑
# tools/build_kb_db.py 与 tools/check_quotes.py。
# 不让构建失败：这批正文对运行零收益，为它把站点顶下线不值当。失败时顺手把归档的大小与
# 头 16 字节打进日志——是半截 gzip 还是被换成了 LFS 指针，一眼就能分清。
RUN python tools/extract_sources.py || (echo "!! 警告：正文归档不可用，云端重建检索库前请重传 sources-archive.tar.gz"; ls -l sources-archive.tar.gz; head -c 16 sources-archive.tar.gz | od -An -c)

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
