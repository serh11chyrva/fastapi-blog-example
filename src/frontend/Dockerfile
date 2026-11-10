FROM node:22-alpine AS dependencies

WORKDIR /app
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM dependencies AS development

COPY src/frontend/index.html src/frontend/vite.config.ts src/frontend/tsconfig*.json ./
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM dependencies AS build

COPY src/frontend/ ./
RUN npm run build

FROM nginx:1.29-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
