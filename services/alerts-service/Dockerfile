FROM python:3.11-slim AS security-updated-base

# Apply Debian's fix for CVE-2026-53615 while the upstream image remains vulnerable.
ARG UTIL_LINUX_VERSION=2.41.5-0+deb13u1
RUN apt-get update \
    && apt-get install --only-upgrade -y --no-install-recommends "util-linux=${UTIL_LINUX_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

FROM security-updated-base AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY libs/platform_common /build/libs/platform_common
COPY services/alerts-service/requirements.txt /build/services/alerts-service/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /build/services/alerts-service/requirements.txt

FROM security-updated-base AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY services/alerts-service/app /app/app
COPY services/alerts-service/alembic.ini /app/alembic.ini
COPY services/alerts-service/alembic /app/alembic
RUN /usr/local/bin/python -m pip uninstall -y pip setuptools wheel || true \
    && /opt/venv/bin/python -m pip uninstall -y pip setuptools wheel || true \
    && rm -rf /usr/local/lib/python3.11/site-packages/pip* \
        /usr/local/lib/python3.11/site-packages/setuptools* \
        /usr/local/lib/python3.11/site-packages/wheel* \
        /opt/venv/lib/python3.11/site-packages/pip* \
        /opt/venv/lib/python3.11/site-packages/setuptools* \
        /opt/venv/lib/python3.11/site-packages/wheel*

USER appuser
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
