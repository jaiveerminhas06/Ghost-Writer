# Stage 1: build the React page into static files.
FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Python server (CPU only), which also serves those files.
FROM python:3.12-slim
# Hugging Face Spaces run the container as user 1000, so the app folder must belong to that user.
RUN useradd -m -u 1000 user
WORKDIR /app
COPY deploy/requirements-space.txt .
RUN pip install --no-cache-dir -r requirements-space.txt
COPY --chown=user api/ api/
COPY --chown=user src/ src/
COPY --chown=user results/09_thresholds.csv results/09_thresholds.csv
COPY --chown=user --from=web /web/dist frontend/dist
RUN mkdir models && chown user models
USER user
# GW_MODEL_REPO (the Hub repo holding models/) is set in the Space's settings, not here.
ENV GW_IG_STEPS=32 HF_HOME=/tmp/hf
EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
