FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system okoffice && adduser --system --ingroup okoffice okoffice

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY schemas ./schemas
COPY examples ./examples
COPY scripts ./scripts

RUN python -m pip install --upgrade pip && python -m pip install -e .

RUN mkdir -p /workspace /app/.okoffice-out && chown -R okoffice:okoffice /workspace /app

USER okoffice

EXPOSE 7331
VOLUME ["/workspace"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:7331/healthz', timeout=3)); raise SystemExit(0 if data.get('status') == 'ok' else 1)"

ENTRYPOINT ["okoffice"]
CMD ["serve", "--api", "--host", "0.0.0.0", "--port", "7331", "--safe-root", "/workspace"]
