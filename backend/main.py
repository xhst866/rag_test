import os
import tempfile
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from rag_logic import process_chat_message, embeddings
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings

# Загружаем переменные окружения
load_dotenv()

# Инициализация клиента ChromaDB
# Для версии 0.5.x возвращаемся к использованию Settings
# Временно убираем настройки аутентификации для отладки.
# Цель - заставить сервер запуститься. Мы ожидаем, что получим ошибку 401 позже.
chroma_client = chromadb.HttpClient(host="chroma-db", port=8000)

# Инициализация векторного хранилища Chroma
collection_name = "documents"
vectorstore = Chroma(
    client=chroma_client,
    collection_name=collection_name,
    embedding_function=embeddings,
)

app = FastAPI(title="RAG Demo API")

# Монтируем директорию uploads для раздачи статических файлов
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене замените на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Зависимость для получения векторного хранилища
def get_vectorstore():
    return vectorstore

# Модели запросов/ответов
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    conversation_id: Optional[str] = None
    personality: Optional[str] = None

# Тестовый эндпоинт
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Эндпоинт для загрузки файлов
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), vectorstore: Chroma = Depends(get_vectorstore)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не может быть пустым.")

    tmp_file_path = None  # Инициализируем переменную
    try:
        # Сохраняем загруженный файл во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(await file.read())
            tmp_file_path = tmp_file.name

        # Проверяем размер файла
        file_size = os.path.getsize(tmp_file_path)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Размер файла превышает лимит в 5 МБ. Размер вашего файла: {round(file_size / 1024 / 1024, 2)} МБ."
            )

        docs = []
        # Проверяем тип файла
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension == ".pdf":
            # Используем PyPDFLoader для загрузки PDF
            loader = PyPDFLoader(tmp_file_path)
            pages = loader.load_and_split()
            
            # Добавляем имя файла в метаданные каждой страницы
            for page in pages:
                page.metadata["source"] = file.filename

            # Сохраняем файл локально
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_location = os.path.join(upload_dir, file.filename)

            # Перемещаем временный файл в постоянное хранилище
            import shutil
            shutil.move(tmp_file_path, file_location)
            tmp_file_path = None # Сбрасываем, так как файл перемещен

            # Разделяем документы на части для добавления в базу
            text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            docs = text_splitter.split_documents(pages)

        # Добавляем документы в векторное хранилище порциями (батчами)
        if docs:
            batch_size = 50
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i + batch_size]
                vectorstore.add_documents(documents=batch)
            return {"message": f"Файл '{file.filename}' успешно загружен и обработан.", "filename": file.filename}
        else:
            return {"message": "Не удалось извлечь текст из файла или формат не поддерживается."}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")
    finally:
        # Гарантированно удаляем временный файл, если он еще существует
        if tmp_file_path and os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

# Эндпоинт для чата
@app.post("/api/chat")
async def chat(request: ChatRequest, db: Chroma = Depends(get_vectorstore)):
    user_message = request.messages[-1]
    if not user_message.content:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")

    try:
        response = await process_chat_message(
            question=user_message.content, 
            vectorstore=db,
            personality=request.personality
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке запроса: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
