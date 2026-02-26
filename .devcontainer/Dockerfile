FROM mcr.microsoft.com/devcontainers/javascript-node:22

WORKDIR /workspaces/visit3

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mkdir -p /home/node/.cache/uv \
    && chown -R node:node /home/node/.cache

RUN npm config set fund false \
    && npm config set audit false
