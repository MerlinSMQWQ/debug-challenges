FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 player
WORKDIR /challenge
COPY --chown=player:player . .
USER player
ENTRYPOINT ["python", "shipping.py"]
CMD ["--help"]
