FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system learnant && adduser --system --ingroup learnant learnant
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=learnant:learnant . .
RUN mkdir -p /app/staticfiles /app/uploads \
    && chmod 755 /app/docker-entrypoint.sh \
    && chown -R learnant:learnant /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health/', timeout=3)"

CMD ["/app/docker-entrypoint.sh"]
