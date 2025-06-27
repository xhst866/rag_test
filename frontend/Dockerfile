# Этап сборки
# Используем slim-образ для лучшей совместимости с нативными модулями
FROM node:18-slim as build-stage

WORKDIR /app

# Копируем package.json и package-lock.json
COPY package*.json ./

# Устанавливаем зависимости
# Очищаем кэш и устанавливаем зависимости
RUN npm cache clean --force && npm install

# Копируем исходный код
COPY . .

# Собираем приложение
RUN npm run build

# Этап продакшн
FROM nginx:stable-alpine as production-stage

# Копируем собранное приложение из этапа сборки
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Копируем конфигурацию nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт 80
EXPOSE 80

# Запускаем nginx
CMD ["nginx", "-g", "daemon off;"]
