FROM node:22

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

VOLUME /data
ENV SQLITE_PATH=/data/vod.db
ENV PORT=5050

EXPOSE 5050
CMD ["npx", "next", "start", "-p", "5050"]
