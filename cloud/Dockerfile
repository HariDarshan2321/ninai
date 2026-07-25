FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
RUN pip install --no-cache-dir .

RUN groupadd --system --gid 10001 ninai \
    && useradd --system --uid 10001 --gid ninai --home-dir /nonexistent --shell /usr/sbin/nologin ninai
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/ninai-cloud-entrypoint

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=2).read()"]

ENTRYPOINT ["ninai-cloud-entrypoint"]
CMD ["ninai-cloud-mcp"]
