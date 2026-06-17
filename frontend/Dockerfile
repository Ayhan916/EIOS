# ── Stage 1: dependency installer ─────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# ── Stage 2: builder ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time variable — the browser calls this URL directly
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Enable Next.js standalone output (minimises image size)
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Stage 3: runtime image ────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

RUN addgroup --gid 1001 eios && \
    adduser --uid 1001 --ingroup eios --disabled-password --no-create-home eios

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

COPY --from=builder --chown=eios:eios /app/.next/standalone ./
COPY --from=builder --chown=eios:eios /app/.next/static ./.next/static
COPY --from=builder --chown=eios:eios /app/public ./public

USER eios

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:3000 || exit 1

CMD ["node", "server.js"]
