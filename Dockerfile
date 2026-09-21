# KSPR — imagen de análisis aislado con herramientas de ingeniería inversa.
# Uso:
#   docker build -t kspr .
#   docker run --rm -it -v "$PWD:/work" kspr -i
#
# El análisis dinámico sigue deshabilitado por defecto: esta imagen solo
# aporta las herramientas estáticas y el carver.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    KSPR_CONFIG_DIR=/root/.kspr

RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils file yara binwalk foremost upx-ucl p7zip-full strace gdb \
        git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir ".[re]"

ENTRYPOINT ["python", "cli/kspr.py"]
CMD ["--interactive"]
