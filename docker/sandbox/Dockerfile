FROM python:3.12-slim-bookworm

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies:
# - git: version control operations
# - nodejs, npm: JavaScript / Node.js execution
# - pandoc: document conversion
# - libreoffice-nogui: headless office document generation / PDF conversion
# - poppler-utils: PDF utilities (pdftotext, pdfinfo)
# - procps, curl, ca-certificates: basic Linux utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    coreutils \
    procps \
    git \
    curl \
    ca-certificates \
    pandoc \
    libreoffice-nogui \
    poppler-utils \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root sandbox user
RUN useradd -m -u 1000 -s /bin/bash sandboxuser

# Create workspace and shared directory, ensuring ownership by sandboxuser
RUN mkdir -p /workspace /shared && \
    chown -R sandboxuser:sandboxuser /workspace /shared

WORKDIR /workspace

# Install document generation & testing libraries
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Switch to non-root execution
USER sandboxuser

# Configure git to safely operate in mounted workspaces
RUN git config --global --add safe.directory '*'

# Default command keeps the container alive for `docker exec`
CMD ["sleep", "infinity"]
