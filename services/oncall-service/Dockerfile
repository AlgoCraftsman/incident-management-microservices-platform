FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY libs/platform_common /build/libs/platform_common
COPY services/oncall-service/requirements.txt /build/services/oncall-service/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /build/services/oncall-service/requirements.txt

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY services/oncall-service/app /app/app
COPY services/oncall-service/alembic.ini /app/alembic.ini
COPY services/oncall-service/alembic /app/alembic
RUN /usr/local/bin/python -m pip uninstall -y pip setuptools wheel || true \
    && /opt/venv/bin/python -m pip uninstall -y pip setuptools wheel || true \
    && rm -rf /usr/local/lib/python3.11/site-packages/pip* \
        /usr/local/lib/python3.11/site-packages/setuptools* \
        /usr/local/lib/python3.11/site-packages/wheel* \
        /opt/venv/lib/python3.11/site-packages/pip* \
        /opt/venv/lib/python3.11/site-packages/setuptools* \
        /opt/venv/lib/python3.11/site-packages/wheel*

USER appuser
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
