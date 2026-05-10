# syntax=docker/dockerfile:1.7
#
# Production image for the ASICify web app.
#
# Build from the repo root:
#   docker build -t asicify/web .
#
# Run:
#   docker run --rm -p 3000:3000 asicify/web
#
# The image embeds the docs/ directory so /docs/[slug] pages can be rendered
# at request time without the source repo present.

# ============================================================================
# Stage 1: deps
# ----------------------------------------------------------------------------
# Install workspace dependencies. Copy only the manifests so Docker's layer
# cache holds across source changes.
# ============================================================================
FROM node:22-alpine AS deps

RUN apk add --no-cache libc6-compat
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

WORKDIR /repo

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* turbo.json ./
COPY apps/web/package.json        ./apps/web/package.json
COPY packages/shared/package.json ./packages/shared/package.json

RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && \
    pnpm install --frozen-lockfile --filter @asicify/web...

# ============================================================================
# Stage 2: build
# ----------------------------------------------------------------------------
# Compile the Next.js app to its standalone server bundle.
# ============================================================================
FROM node:22-alpine AS builder

RUN apk add --no-cache libc6-compat
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

WORKDIR /repo

COPY --from=deps /repo/node_modules                      ./node_modules
COPY --from=deps /repo/apps/web/node_modules             ./apps/web/node_modules
COPY --from=deps /repo/packages/shared/node_modules      ./packages/shared/node_modules

# Source for the web app and its shared workspace dep.
COPY apps/web        ./apps/web
COPY packages/shared ./packages/shared
# Markdown rendered at runtime by /docs/[...slug].
COPY docs            ./docs
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* turbo.json ./

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

RUN pnpm --filter @asicify/web build

# ============================================================================
# Stage 3: runtime
# ----------------------------------------------------------------------------
# Minimal final image. Just node + the standalone server output + assets.
# ============================================================================
FROM node:22-alpine AS runner

RUN apk add --no-cache tini

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Run as a non-root user.
RUN addgroup -S -g 1001 nodejs && \
    adduser  -S -u 1001 -G nodejs nextjs

# Standalone bundle. With outputFileTracingRoot pointing at the repo root,
# Next emits the bundle at apps/web/.next/standalone/ but its internal layout
# starts from the tracing root (server.js ends up at standalone/apps/web/server.js).
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/apps/web/.next/static ./apps/web/.next/static

# Markdown content sourced by lib/docs.ts (resolves to ../../docs from apps/web).
COPY --from=builder --chown=nextjs:nodejs /repo/docs ./docs

USER nextjs

EXPOSE 3000

# WORKDIR matches what Next standalone expects so process.cwd() lines up
# with the docs path resolver in lib/docs.ts.
WORKDIR /app/apps/web

# tini reaps zombie processes and forwards signals correctly.
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "server.js"]
