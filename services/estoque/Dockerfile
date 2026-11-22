# syntax=docker/dockerfile:1.7
# Build a partir da RAIZ do repositório:  docker build -f services/estoque/Dockerfile .
ARG PYTHON_IMAGE=python:3.13-slim-bookworm

# ---------- estágio 1: dependências (tem pip/compiladores; não vai para produção) ----------
FROM ${PYTHON_IMAGE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /build
# requirements antes do código: a camada de dependências fica em cache entre commits
COPY services/estoque/requirements.txt ./requirements.txt
COPY libs/veloz_common ./libs/veloz_common
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt ./libs/veloz_common \
 && pip uninstall -y pip

# ---------- estágio 2: runtime enxuto, sem pip/setuptools, usuário não-root ----------
FROM ${PYTHON_IMAGE} AS runtime
ARG APP_VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="loja-veloz-estoque" \
      org.opencontainers.image.description="Serviço de Estoque (catálogo, reserva e baixa)" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    APP_VERSION=${APP_VERSION} \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=20
# usuário dedicado com UID fixo (casa com runAsUser no Kubernetes) e remoção do pip do sistema
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && python -m pip uninstall -y pip
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY services/estoque/app ./app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).status == 200 else 1)"]
# forma exec: o uvicorn é o PID 1 e recebe o SIGTERM diretamente (shutdown gracioso)
CMD ["uvicorn", "app.main:app", "--no-access-log"]
