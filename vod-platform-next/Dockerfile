FROM node:22-slim
WORKDIR /app

COPY .next/standalone/ ./
COPY .next/static .next/static

ENV NODE_ENV=production
ENV PORT=5050
EXPOSE 5050
CMD ["node", "server.js"]
