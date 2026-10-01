# Build the React app, then serve the static bundle via nginx (proxies /api -> app).
# Node 22: Vite 8 needs Node >= 20.19 or 22.12 (U8 Infra §3.2)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# the lock as committed: no silent upgrade in the image (US-7.5)
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
