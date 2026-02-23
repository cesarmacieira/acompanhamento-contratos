# ---------- STAGE 1: Builder ----------
FROM registry-cache.jfce.jus.br/docker.io/library/python:3.11-slim AS builder

WORKDIR /app

# Instala dependências básicas de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copia o arquivo de dependências
COPY requirements.txt .

# Cria ambiente virtual isolado e instala libs necessárias
RUN python3.11 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ---------- STAGE 2: Runtime ----------
FROM registry-cache.jfce.jus.br/docker.io/library/python:3.11-slim

# Cria usuário não-root, diretórios e config do Streamlit
RUN useradd -m appuser \
    && mkdir -p /app /home/appuser/.streamlit \
    && printf '[logger]\nlevel = "error"\nmessageFormat = "%%(asctime)s %%(message)s"\n\n[server]\nfileWatcherType = "none"\nrunOnSave = false\n' \
       > /home/appuser/.streamlit/config.toml \
    && chown -R appuser:appuser /app /home/appuser/.streamlit

WORKDIR /app

# Variáveis de ambiente para otimizar execução
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:/opt/venv/bin:$PATH" \
    STREAMLIT_PORT=8080

# Copia o ambiente virtual da imagem builder
COPY --from=builder /opt/venv /opt/venv

# Copia o código do app e demais arquivos
COPY --chown=appuser:appuser ./build/assets/ .

USER appuser

EXPOSE 8080

CMD ["streamlit", "run", "app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.runOnSave=false", \
     "--server.fileWatcherType=none", \
     "--logger.level=error"]