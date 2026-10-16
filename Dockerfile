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

# ResPlan.zip and split.json into data/, each checked against its pinned SHA-256, then every plan into one
# store the server reads a plan at a time from, the split inside it. The downloads are written readable by
# root only, so the store is opened up for the server's own user and the downloads go.
COPY scripts/fetch_resplan.py scripts/plan_store.py ./scripts/
RUN python scripts/fetch_resplan.py \
 && python scripts/plan_store.py data/ResPlan.zip data/plans.sqlite \
 && rm data/ResPlan.zip data/split.json \
 && chmod a+r data/plans.sqlite

COPY site ./site

RUN useradd --create-home --uid 10001 loopwright
USER loopwright

EXPOSE 8000
# Railway sets PORT. A public service answers to any host name, so a domain added later works at once;
# the host check is for the app on a machine of its own, where it guards against DNS rebinding.
CMD exec loopwright serve --site site --data data/plans.sqlite --host 0.0.0.0 --port "${PORT:-8000}" --allow-host "*"
