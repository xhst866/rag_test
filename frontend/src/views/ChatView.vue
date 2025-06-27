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
                <a :href="`${backendUrl}/static/uploads/${encodeURIComponent(source.source)}#page=${source.page + 1}`" target="_blank" rel="noopener noreferrer">
                  {{ source.source }}, стр. {{ source.page + 1 }}
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <div class="input-panel">
       <div class="settings-bar">
        <div class="personality-selector">
          <label for="personality">Стиль ответов:</label>
          <select v-model="selectedPersonality" id="personality">
            <option value="default">Обычный</option>
            <option value="witty">Остроумный</option>
            <option value="lazy">Ленивый кассир</option>
            <option value="sarcastic">Жесткий сарказм</option>
          </select>
        </div>
      </div>
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
        <button class="icon-btn send-btn" @click="sendMessage" :disabled="!userInput.trim()">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import DOMPurify from 'dompurify';
import { marked } from 'marked';

const messages = ref([]);
const userInput = ref('');
const selectedFile = ref(null);
const isUploading = ref(false);
const fileInput = ref(null);
const messagesContainer = ref(null);
const textarea = ref(null);
const selectedPersonality = ref('default');

const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const formatMessage = (content) => {
  const rawHtml = marked.parse(content || '');
  return DOMPurify.sanitize(rawHtml);
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const adjustTextareaHeight = () => {
  if (textarea.value) {
    textarea.value.style.height = 'auto';
    textarea.value.style.height = `${textarea.value.scrollHeight}px`;
  }
};

onMounted(() => {
  messages.value.push({ role: 'assistant', content: 'Здравствуйте! Загрузите PDF или TXT файл, и я отвечу на ваши вопросы по его содержанию.' });
  adjustTextareaHeight();
});

watch(userInput, adjustTextareaHeight);
watch(messages, () => nextTick(scrollToBottom), { deep: true });

const triggerFileInput = () => {
  fileInput.value.click();
};

const handleFileChange = (event) => {
  const file = event.target.files[0];
  if (file) {
    if (file.size > 5 * 1024 * 1024) {
        alert('Размер файла не должен превышать 5 МБ.');
        return;
    }
    selectedFile.value = file;
  }
};

const clearSelectedFile = () => {
  selectedFile.value = null;
  fileInput.value.value = '';
};

const uploadFile = async () => {
  if (!selectedFile.value) return;
  isUploading.value = true;

  const formData = new FormData();
  formData.append('file', selectedFile.value);

  try {
    const response = await fetch(`${backendUrl}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Ошибка при загрузке файла');
    }

    messages.value.push({ role: 'assistant', content: `Файл \"${selectedFile.value.name}\" успешно загружен. Теперь вы можете задавать по нему вопросы.` });
    clearSelectedFile();
  } catch (error) {
    console.error('Ошибка:', error);
    messages.value.push({ role: 'assistant', content: `Ошибка при загрузке файла: ${error.message}` });
  } finally {
    isUploading.value = false;
  }
};

const sendMessage = async () => {
  const currentInput = userInput.value.trim();
  if (!currentInput) return;

  const currentMessages = [...messages.value, { role: 'user', content: currentInput }];
  messages.value = currentMessages;
  userInput.value = '';
  adjustTextareaHeight();

  try {
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: currentMessages,
        personality: selectedPersonality.value
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Ошибка сети');
    }

    const data = await response.json();
    messages.value = [...currentMessages, { role: 'assistant', content: data.answer, sources: data.sources }];

  } catch (error) {
    console.error('Ошибка при отправке сообщения:', error);
    messages.value = [...currentMessages, { role: 'assistant', content: `Произошла ошибка: ${error.message}` }];
  } finally {
    nextTick(() => {
      scrollToBottom();
    });
  }
};
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  background-color: var(--ink-text-light);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-wrapper {
  display: flex;
  max-width: 85%;
}

.message-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-wrapper.assistant {
  align-self: flex-start;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.6;
}

.message-wrapper.user .message-bubble {
  background-color: var(--ink-primary);
  color: var(--ink-text-light);
  border-top-right-radius: 4px;
}

.message-wrapper.assistant .message-bubble {
  background-color: var(--ink-surface);
  color: var(--ink-text-dark);
  border-top-left-radius: 4px;
}

.message-content :deep(p) {
  margin: 0 0 8px 0;
}
.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.input-panel {
  padding: 16px 24px;
  background-color: var(--ink-text-light);
  border-top: 1px solid var(--ink-border);
}

.settings-bar {
  padding: 0 0 12px 0;
  background-color: var(--ink-text-light);
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.personality-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}

.personality-selector label {
  font-weight: 500;
  font-size: 14px;
  color: var(--ink-text-secondary);
}

.personality-selector select {
  padding: 5px 8px;
  border-radius: 6px;
  border: 1px solid var(--ink-border);
  background-color: #fff;
  font-family: inherit;
  color: var(--ink-text-dark);
  outline: none;
}

.file-preview {
  display: flex;
  align-items: center;
  padding: 8px;
  background-color: var(--ink-surface);
  border-radius: 12px;
  margin-bottom: 12px;
  font-size: 14px;
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
</style>