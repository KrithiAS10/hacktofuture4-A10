FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
ARG BACKEND_BASE_URL=http://lerna-backend:8000
ENV BACKEND_BASE_URL=$BACKEND_BASE_URL
# Optional IANA zone baked into client bundle (e.g. Asia/Kolkata). Omit for browser-local time.
ARG NEXT_PUBLIC_DISPLAY_TIMEZONE=
ENV NEXT_PUBLIC_DISPLAY_TIMEZONE=$NEXT_PUBLIC_DISPLAY_TIMEZONE
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV BACKEND_BASE_URL=http://lerna-backend:8000

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
