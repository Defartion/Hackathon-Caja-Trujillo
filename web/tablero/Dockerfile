# Compila la app con Vite y la sirve como sitio estático con nginx.
# Construir desde la raíz del repo:  docker build -f web/tablero/Dockerfile --build-arg VITE_API_URL=https://api... .
FROM node:20-alpine AS build
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
WORKDIR /app
COPY web/tablero/package.json web/tablero/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/tablero/ ./
RUN npm run build

FROM nginx:1.27-alpine
ENV PORT=80
COPY web/_docker/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
