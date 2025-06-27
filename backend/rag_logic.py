import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# Получаем ключ API из переменных окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверяем, что ключ API доступен
if not OPENAI_API_KEY:
    raise ValueError("Необходимо установить переменную окружения OPENAI_API_KEY")

# Инициализация моделей и компонентов
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model_name="gpt-3.5-turbo", temperature=0)

# Шаблон промпта
PROMPT_TEMPLATE = """
Ты — полезный ассистент. Твоя задача — отвечать на вопросы пользователя, основываясь на содержании предоставленных ниже документов.
Твой ответ должен быть основан только на фактах из текста. Избегай домыслов.
Если информация для ответа явно отсутствует в контексте, сообщи, что ты не можешь дать ответ на основе имеющихся данных.
Для каждого утверждения в своем ответе ты должен указать источник в формате [Источник: название_файла, страница X].

Контекст:
{context}

---

Вопрос: {question}
Ответ:
"""
prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

def format_docs(docs):
    """Форматирует документы для передачи в промпт."""
    return "\n\n".join(
        f"Источник: {doc.metadata.get('source', 'N/A')}, страница {doc.metadata.get('page', 'N/A')}\nСодержимое: {doc.page_content}"
        for doc in docs
    )

def get_rag_chain(vectorstore):
    """Создает и возвращает RAG-цепочку."""
    retriever = vectorstore.as_retriever()
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

async def process_chat_message(question: str, vectorstore: Chroma):
    """Обрабатывает сообщение чата с использованием RAG."""
    retriever = vectorstore.as_retriever()
    docs = retriever.get_relevant_documents(question)

    # Если релевантные документы не найдены, сразу возвращаем ответ
    if not docs:
        return {
            "answer": "К сожалению, в загруженных документах я не нашел ответа на ваш вопрос.",
            "sources": []
        }

    rag_chain = get_rag_chain(vectorstore)
    answer = await rag_chain.ainvoke(question)
    
    # Источники теперь встроены в ответ, поэтому возвращаем пустой список
    return {"answer": answer, "sources": []}
