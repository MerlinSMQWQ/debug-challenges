FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends lsof procps ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 player

WORKDIR /challenge
COPY --chown=player:player . .
USER player

ENTRYPOINT ["python", "scripts/run_export.py"]
CMD ["--help"]
