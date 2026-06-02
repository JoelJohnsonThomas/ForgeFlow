# Multi-stage build: node compiles the SPA, nginx serves it + proxies /api → api:8000

# ---- Stage 1: build ----
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts index.html ./
COPY src ./src
COPY public ./public

RUN npm run build

# ---- Stage 2: serve ----
FROM nginx:1.27-alpine
# Drop the template into nginx's auto-envsubst directory — the official image's
# entrypoint expands ${VAR} references against the container env at startup.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
# Use 127.0.0.1, not localhost: BusyBox wget resolves localhost to IPv6 ::1,
# but nginx listens on IPv4 only, so the probe got "connection refused".
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1
