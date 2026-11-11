# BETFORGE dashboard image (Next.js 15, cyberpunk).
# Builder -> runner (node:20-alpine). At runtime it proxies /api/betforge to the
# FastAPI backend at BETFORGE_API_URL (default http://backend:8000 in compose).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
ARG BETFORGE_API_URL=http://backend:8000
ENV BETFORGE_API_URL=$BETFORGE_API_URL
RUN pnpm build

FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/.next ./.next
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/node_modules ./node_modules
ENV NODE_ENV=production PORT=3000
EXPOSE 3000
CMD ["pnpm", "start"]
