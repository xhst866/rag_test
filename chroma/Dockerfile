# Используем базовый образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt ./

# Устанавливаем зависимости, включая фиксированную версию numpy
RUN pip install --no-cache-dir -r requirements.txt

# Команда для запуска ChromaDB (стандартная для этого образа)
CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8000"]
