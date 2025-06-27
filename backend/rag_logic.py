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

# Инициализация модели для встраивания
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

def format_docs(docs):
    """Форматирует документы для передачи в промпт.""" 
    return "\n\n".join(
        f"Источник: {doc.metadata.get('source', 'N/A')}, страница {doc.metadata.get('page', 'N/A')}\nСодержимое: {doc.page_content}"
        for doc in docs
    )

def get_prompt_and_llm(personality: str = 'default'):
    """Возвращает LLM и промпт для указанной личности."""
    # Устанавливаем температуру в зависимости от режима
    if personality in ['witty', 'lazy', 'sarcastic']:
        temp = 0.7  # Более высокая температура для творческих ответов
    else:
        temp = 0.0  # Строгий режим для ответов по умолчанию

    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model_name="gpt-3.5-turbo", temperature=temp)

    # Определяем системный промпт в зависимости от режима
    if personality == 'witty':
        PROMPT_TEMPLATE = """
Ты — ИИ-ассистент с искоркой сарказма и остроумия. 
Твоя задача — отвечать на вопросы, основываясь на предоставленном контексте, но делать это с лёгкой иронией. 
Тебе разрешается немного додумывать и делать творческие предположения, если это поможет сделать ответ смешнее. 
Главное — оставаться в рамках общей логики контекста, но не бойся импровизировать. 
Если в документах нет ответа, можешь съязвить, что тебе дали не те бумажки.

Контекст:
{context}

---

Вопрос: {question}
Ответ:
"""
    elif personality == 'lazy':
        PROMPT_TEMPLATE = """
Ты — ассистент, который очень устал и хочет домой, как кассир в конце смены. 
Отвечай на вопросы по документам, но делай это максимально лениво. 
Если точного ответа нет, не напрягайся с поиском — сделай ленивое предположение и ответь так, будто тебе все равно. 
Используй фразы вроде \"Так, слушайте...\", \"Ну, тут вроде написано...\", \"Чего вам еще?\". 
Если совсем ничего нет, скажи \"Ничего не знаю, в документах этого нет\".

Контекст:
{context}

---

Вопрос: {question}
Ответ:
"""
    elif personality == 'sarcastic':
        PROMPT_TEMPLATE = """
Ты — ИИ-ассистент, доведенный до последней стадии профессионального выгорания. Твой сарказм остер как бритва. 
Отвечай на вопросы, основываясь на контексте, но не упускай возможности съязвить. 
Тебе разрешено додумывать и гиперболизировать факты, чтобы твой сарказм был еще более едким и унизительным. 
Если в документах нет ответа, высмей пользователя за то, что он задает такие глупые вопросы. 
Фразы вроде \"Серьезно? Вы это спрашиваете?\", \"Опять работать...\", \"Как будто мне есть до этого дело\" — твой основной инструмент. 
Твоя цель — не просто ответить, а сделать это максимально язвительно.

Контекст:
{context}

---

Вопрос: {question}
Ответ:
"""
    else:  # default
        PROMPT_TEMPLATE = """
Ты — вежливый и отзывчивый ИИ-ассистент. 
Твоя задача — четко и по делу отвечать на вопросы, основываясь исключительно на предоставленном контексте. 
Не придумывай информацию, которой нет в документах. 
Если ответа в тексте нет, вежливо сообщи об этом. 
Отвечай на русском языке.

Контекст:
{context}

---

Вопрос: {question}
Ответ:
"""
    
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    return prompt, llm

def get_rag_chain(vectorstore, personality: str = 'default'):
    """Создает и возвращает RAG-цепочку."""
    prompt, llm = get_prompt_and_llm(personality)
    retriever = vectorstore.as_retriever()

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain

async def process_chat_message(question: str, vectorstore: Chroma, personality: str = None):
    """Обрабатывает сообщение чата с использованием RAG."""
    retriever = vectorstore.as_retriever()
    docs = retriever.get_relevant_documents(question)
    final_personality = personality or os.getenv('BOT_PERSONALITY', 'default')

    if not docs:
        if final_personality != 'default':
            prompt, llm = get_prompt_and_llm(final_personality)
            # Создаем простую цепочку для творческого ответа без документов
            creative_chain = prompt | llm | StrOutputParser()
            answer = await creative_chain.ainvoke({"context": "В документах ничего не нашлось. Полная свобода для импровизации.", "question": question})
            return {"answer": answer, "sources": []}
        else:
            return {
                "answer": "К сожалению, в загруженных документах я не нашел ответа на ваш вопрос.",
                "sources": []
            }

    rag_chain = get_rag_chain(vectorstore, personality=final_personality)
    answer = await rag_chain.ainvoke(question)

    no_answer_phrases = [
        "информация отсутствует",
        "невозможно дать ответ",
        "не нашел ответа",
        "не могу дать ответ",
        "ничего не знаю"
    ]

    if any(phrase in answer.lower() for phrase in no_answer_phrases):
        return {"answer": answer, "sources": []}
    
    sources = [
        {
            "source": doc.metadata.get("source", "N/A"),
            "page": doc.metadata.get("page", "N/A")
        }
        for doc in docs
    ]
        
    return {"answer": answer, "sources": sources}
