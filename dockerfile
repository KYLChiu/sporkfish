# ── Build stage ────────────────────────────────────────────────────────────────
# Uses the same Python version as the dev container (3.11) to avoid surprises.
FROM python:3.11-slim AS builder

# Install only the C-extension build deps needed for packages like numpy/Cython.
# DEBIAN_FRONTEND must come before any apt commands so debconf doesn't block.
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        binutils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a temporary prefix so the final image can
# copy only the wheels (no build tools needed at runtime).
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# Copy installed packages from the builder stage (keeps the runtime image lean).
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Run as a non-root user — reduces blast radius if the container is compromised.
RUN useradd --create-home --shell /bin/bash sporkfish
USER sporkfish
WORKDIR /home/sporkfish/app

# Copy source last so that a code-only change doesn't bust the dependency cache.
COPY --chown=sporkfish:sporkfish . .

CMD ["bash"]
