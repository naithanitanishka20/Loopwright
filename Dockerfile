# Loopwright as one hosted service: the product site at / and the app at /app/.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv/loopwright

COPY pyproject.toml README.md ./
COPY loopwright ./loopwright
RUN pip install ".[serve,import]"

# ResPlan.zip and split.json into data/, each checked against its pinned SHA-256; the app then keeps only
# the test split and the plans the site opens, a tenth of the memory of all 17,000
COPY scripts/fetch_resplan.py scripts/hosted_plans.py ./scripts/
RUN python scripts/fetch_resplan.py \
 && python scripts/hosted_plans.py data/ResPlan.zip data/hosted.pkl \
 && rm data/ResPlan.zip

COPY site ./site

RUN useradd --create-home --uid 10001 loopwright
USER loopwright

EXPOSE 8000
# Railway sets PORT and RAILWAY_PUBLIC_DOMAIN, and checks health from healthcheck.railway.app
CMD exec loopwright serve --site site --data data/hosted.pkl --host 0.0.0.0 --port "${PORT:-8000}" \
    --allow-host "${RAILWAY_PUBLIC_DOMAIN:-localhost}" --allow-host healthcheck.railway.app
