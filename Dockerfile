FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

RUN apt-get update && apt-get -y install --no-install-recommends dumb-init && rm -rf /var/lib/apt/lists/*

# Install production requirements
ADD ./requirements.txt requirements.txt
RUN uv pip install --no-cache-dir -r ./requirements.txt --system

ENTRYPOINT ["dumb-init", "--", "./uvicorn.sh"]