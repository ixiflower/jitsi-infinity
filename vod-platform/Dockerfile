FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install --omit=dev --no-audit --no-fund 2>&1

COPY .next ./.next
COPY next.config.js package.json ./

VOLUME /data
ENV SQLITE_PATH=/data/vod.db
ENV NODE_ENV=production
ENV PORT=5050

EXPOSE 5050
CMD ["npx", "next", "start", "-p", "5050"]
