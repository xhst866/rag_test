<template>
  <div class="chat-view">

    <div class="messages-container" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" :class="['message-wrapper', message.role]">
        <div class="message-bubble">
          <div class="message-content" v-html="formatMessage(message.content)"></div>
          <div v-if="message.sources && message.sources.length" class="sources-list">
            <strong>Источники:</strong>
            <ul>
              <li v-for="(source, i) in message.sources" :key="i">
                <a :href="`http://localhost:8000/static/uploads/${source.source}#page=${source.page + 1}`" target="_blank" rel="noopener noreferrer">
                  {{ source.source }}, стр. {{ source.page + 1 }}
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <div class="input-panel">
      <div v-if="selectedFile" class="file-preview">
        <span>{{ selectedFile.name }}</span>
        <button @click="uploadFile" :disabled="isUploading" class="upload-confirm-btn">{{ isUploading ? '...' : '▲' }}</button>
        <button @click="clearSelectedFile" class="upload-cancel-btn">×</button>
      </div>
      <div class="input-area">
        <input type="file" @change="handleFileChange" ref="fileInput" style="display: none" accept=".pdf,.txt">
        <button class="icon-btn attach-btn" @click="triggerFileInput">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
        </button>
        <textarea
          v-model="userInput"
          @keyup.enter.exact.prevent="sendMessage"
          placeholder="Задайте вопрос..."
          rows="1"
          ref="textarea"
        ></textarea>
        <button class="icon-btn send-btn" @click="sendMessage" :disabled="!userInput.trim() && !isUploading">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { marked } from 'marked';

const messages = ref([]);
const userInput = ref('');
const selectedFile = ref(null);
const isUploading = ref(false);
const fileInput = ref(null);
const textarea = ref(null);
const messagesContainer = ref(null);

// Auto-scroll logic
watch(messages, async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}, { deep: true });


const triggerFileInput = () => {
  fileInput.value.click();
};

const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
  }
};

const clearSelectedFile = () => {
  selectedFile.value = null;
  fileInput.value.value = ''; // Reset file input
};

const uploadFile = async () => {
  if (!selectedFile.value) return;
  isUploading.value = true;
  
  const formData = new FormData();
  formData.append('file', selectedFile.value);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || 'Ошибка при загрузке файла.');
    }

    messages.value.push({ role: 'assistant', content: `Файл *${result.filename}* успешно загружен.` });
    clearSelectedFile();
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `Ошибка: ${error.message}` });
  } finally {
    isUploading.value = false;
  }
};

const sendMessage = async () => {
  const messageContent = userInput.value.trim();
  if (!messageContent) return;

  messages.value.push({ role: 'user', content: messageContent });
  userInput.value = '';
  autoResizeTextarea();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: messages.value,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Ошибка сети');
    }

    const data = await response.json();
    messages.value.push({ role: 'assistant', content: data.answer, sources: data.sources });

  } catch (error) {
    messages.value.push({ role: 'assistant', content: `Ошибка: ${error.message}` });
  }
};

const formatMessage = (content) => {
  // Сначала обрабатываем ссылки на источники, превращая их в кликабельные теги <a>
  const processedContent = content.replace(
    /\[Источник: (.*?),(?:\s*страница|\s*стр\.)\s*(\d+)\]/g,
    (match, filename, page) => {
      const url = `http://localhost:8000/static/uploads/${filename.trim()}#page=${page}`;
      // Возвращаем HTML-ссылку. Класс 'source-link' позволит нам стилизовать ее.
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="source-link">${match}</a>`;
    }
  );
  // Затем обрабатываем остальной текст как Markdown
  return marked(processedContent, { breaks: true });
};

const autoResizeTextarea = () => {
  const ta = textarea.value;
  if (ta) {
    ta.style.height = 'auto';
    ta.style.height = `${ta.scrollHeight}px`;
  }
};

onMounted(() => {
  messages.value.push({ role: 'assistant', content: 'Здравствуйте! Загрузите PDF или TXT файл и задайте мне вопрос по его содержимому.' });
  textarea.value.addEventListener('input', autoResizeTextarea);
});

</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap');

:root {
  --ink-bg: #FFFFFF;
  --ink-primary: #6941FF;
  --ink-text-light: #FFFFFF;
  --ink-text-dark: #111111;
  --ink-text-secondary: #6c757d;
  --ink-border: #F0F0F0;
  --ink-surface: #F5F5F7;
}

html, body {
  height: 100%;
  margin: 0;
  font-family: 'Roboto', sans-serif;
  background-color: var(--ink-bg);
  color: var(--ink-text-dark);
}

#app {
  height: 100%;
}

.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 800px;
  margin: 0 auto;
  background-color: var(--ink-bg);
}

.chat-header {
  padding: 24px 32px;
  background-color: var(--ink-bg);
  text-align: left;
}

.logo-img {
  height: 28px;
  vertical-align: middle;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-wrapper {
  display: flex;
  width: 100%;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 16px 22px;
  border-radius: 24px;
  line-height: 1.6;
  word-wrap: break-word;
}

.message-wrapper.user .message-bubble {
  background-color: var(--ink-primary);
  color: var(--ink-text-light);
  border-bottom-right-radius: 8px;
}

.message-wrapper.assistant .message-bubble {
  background-color: var(--ink-surface);
  color: var(--ink-text-dark);
  border-bottom-left-radius: 8px;
}

.input-panel {
  padding: 24px 32px;
  background-color: var(--ink-bg);
  border-top: 1px solid var(--ink-border);
}

.file-preview {
  display: flex;
  align-items: center;
  font-size: 14px;
  margin-bottom: 16px;
  background-color: var(--ink-surface);
  padding: 10px 14px;
  border-radius: 12px;
}

.file-preview span {
  flex-grow: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-right: 10px;
}

.upload-confirm-btn, .upload-cancel-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 20px;
  padding: 0 5px;
}
.upload-confirm-btn { color: var(--ink-primary); }
.upload-cancel-btn { color: #ff4d4d; }

.input-area {
  display: flex;
  align-items: center;
  gap: 16px;
  background-color: var(--ink-surface);
  border-radius: 99px; /* Fully rounded */
  padding: 8px;
}

textarea {
  flex: 1;
  padding: 10px;
  border: none;
  resize: none;
  font-family: inherit;
  font-size: 16px;
  line-height: 1.5;
  max-height: 120px;
  overflow-y: auto;
  background-color: transparent;
  color: var(--ink-text-dark);
}

textarea::placeholder {
  color: #999999;
}

textarea:focus {
  outline: none;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  color: var(--ink-text-secondary);
  transition: color 0.2s;
}

.icon-btn:hover { color: var(--ink-primary); }

.send-btn {
  background-color: var(--ink-primary);
  color: var(--ink-text-light);
  border-radius: 50%;
  width: 48px;
  height: 48px;
  padding: 12px;
  flex-shrink: 0;
}

.send-btn:hover {
  background-color: #5522FF;
  color: var(--ink-text-light);
}

.send-btn:disabled { 
  cursor: not-allowed;
  background-color: #EAEAEA;
  color: #B0B0B0;
}

.sources-list {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.9em;
}

.message-wrapper.assistant .sources-list {
   border-top: 1px solid #E0E0E0;
}

.sources-list strong {
  color: inherit;
}

.sources-list ul {
  list-style-type: none;
  padding-left: 0;
  margin: 8px 0 0 0;
}

.sources-list li {
  margin-bottom: 4px;
}

.sources-list a {
  color: inherit;
  text-decoration: underline;
  opacity: 0.8;
}

.sources-list a:hover {
  opacity: 1;
}

.message-wrapper.user .sources-list a {
  color: var(--ink-text-light);
}

.message-wrapper.assistant .sources-list a {
  color: var(--ink-primary);
}

/* Стили для встроенных ссылок на источники */
.source-link {
  text-decoration: underline;
  opacity: 0.9;
}

.source-link:hover {
  opacity: 1;
}

.message-wrapper.user .source-link {
  color: var(--ink-text-light); /* Белый цвет для сообщений пользователя */
}

.message-wrapper.assistant .source-link {
  color: var(--ink-primary); /* Фиолетовый цвет для сообщений ассистента */
}

</style>