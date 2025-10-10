<template>
  <div class="chat-history-container">
    <div class="section-header">
      <h3 class="section-title">💭 Conversación</h3>
      <div class="header-actions">
        <button v-if="messages.length > 0" @click="$emit('export')" class="action-btn export-btn" title="Exportar chat">
          💾
        </button>
        <button v-if="messages.length > 0" @click="$emit('clear')" class="action-btn clear-btn" title="Limpiar chat">
          🗑️
        </button>
      </div>
    </div>
    
    <div class="chat-history" ref="chatHistory">
      <transition-group name="fade">
        <div v-if="messages.length === 0" key="welcome" class="chat-msg welcome-msg">
          <div class="msg-text">{{ welcomeMessage }}</div>
        </div>
        
        <chat-message
          v-for="(msg, index) in messages"
          :key="index"
          :role="msg.role"
          :content="msg.content"
          :timestamp="msg.timestamp"
          @copy="handleCopy"
        />
        
        <div v-if="isTyping" key="typing" class="chat-msg typing-indicator">
          <div class="msg-role ai-label">
            <span class="msg-icon">🤖</span>
            IA:
          </div>
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script>
import ChatMessage from './ChatMessage.vue';

export default {
  name: 'ChatHistory',
  components: {
    ChatMessage
  },
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    isTyping: {
      type: Boolean,
      default: false
    },
    welcomeMessage: {
      type: String,
      default: '¡Hola! Sube un PDF y pregúntame lo que quieras.'
    }
  },
  emits: ['clear', 'copy', 'export'],
  methods: {
    handleCopy(content) {
      this.$emit('copy', content);
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const chatHistory = this.$refs.chatHistory;
        if (chatHistory) {
          chatHistory.scrollTop = chatHistory.scrollHeight;
        }
      });
    }
  },
  watch: {
    messages: {
      handler() {
        this.scrollToBottom();
      },
      deep: true
    },
    isTyping(newVal) {
      if (newVal) {
        this.scrollToBottom();
      }
    }
  }
};
</script>

<style scoped>
.chat-history-container {
  margin-top: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-title {
  color: #7b1fa2;
  font-size: 1.3rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 1.2rem;
  cursor: pointer;
  transition: transform 0.2s, background 0.2s;
  font-weight: 500;
}

.clear-btn {
  background: #ffebee;
  color: #c62828;
}

.clear-btn:hover {
  background: #f44336;
  color: #fff;
  transform: scale(1.05);
}

.export-btn {
  background: #e8f5e9;
  color: #2e7d32;
}

.export-btn:hover {
  background: #4caf50;
  color: #fff;
  transform: scale(1.05);
}

.chat-history {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 1rem;
  background: #f7f7f7;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(67, 160, 71, 0.06);
  scroll-behavior: smooth;
}

.chat-history::-webkit-scrollbar {
  width: 8px;
}

.chat-history::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.chat-history::-webkit-scrollbar-thumb {
  background: #bdbdbd;
  border-radius: 4px;
}

.chat-history::-webkit-scrollbar-thumb:hover {
  background: #9e9e9e;
}

.chat-msg {
  margin-bottom: 0.8rem;
  padding: 0.7rem 1rem;
  border-radius: 8px;
  font-size: 1rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  animation: fadeIn 0.4s;
}

.welcome-msg {
  background: #fffde7;
  color: #666;
  justify-content: center;
  font-style: italic;
  text-align: center;
}

.msg-text {
  word-break: break-word;
  color: #212121;
  line-height: 1.5;
}

.typing-indicator {
  background: #f1f8e9;
  border-left: 4px solid #43a047;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.msg-role {
  font-weight: bold;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.msg-icon {
  font-size: 1.2rem;
}

.ai-label {
  color: #1b5e20;
  font-weight: 700;
}

.typing-dots {
  display: flex;
  gap: 0.3rem;
  padding: 0.5rem 0;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background: #43a047;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.4s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
