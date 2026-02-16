# Build stage
FROM node:24-alpine AS builder

WORKDIR /app/frontend

COPY package.json yarn.lock ./
RUN npm install yarn && yarn

COPY tsconfig*.json vite.config.ts eslint.config.js index.html ./
COPY src src

# Enable Vite plugin to allow handling environment variables via nginx at runtime
# See vite.config.ts
ENV REPLACE_ENV_FORMAT_ENVSUBST=true
ENV NODE_ENV=production
RUN yarn build

FROM nginx:1.29-alpine AS production

COPY --from=builder /app/frontend/dist /usr/share/nginx/html
COPY --from=builder /app/frontend/dist/index.html /usr/share/nginx/templates/index.html.template
#COPY public /usr/share/nginx/html/public

ENV NGINX_ENVSUBST_TEMPLATE_DIR=/usr/share/nginx/templates
ENV NGINX_ENVSUBST_OUTPUT_DIR=/usr/share/nginx/html

COPY <<EOF /etc/nginx/conf.d/default.conf
server {
  listen 80;
  server_name localhost;

  location / {
    root /usr/share/nginx/html;
    try_files \$uri /index.html;
  }
}
EOF

EXPOSE 80
