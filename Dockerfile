# Stage 1: install the dependencies into a separate folder, so build tools never reach the final image.
FROM python:3.14-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: the runtime image.
FROM python:3.14-slim AS runner
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --home-dir /app app

COPY --from=builder /install /usr/local
COPY --chown=app:app main.py ./
COPY --chown=app:app src ./src
RUN mkdir -p /app/logs && chown app:app /app/logs

USER app
EXPOSE 5004

# One worker on purpose: the rate-limit counters and Socket.IO connections live in this process's memory.
# --proxy-headers: the app sits behind Caddy, so trust its X-Forwarded-* headers (only reachable inside the Docker network).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5004", "--proxy-headers", "--forwarded-allow-ips", "*"]
