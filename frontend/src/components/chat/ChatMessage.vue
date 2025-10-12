<template>
  <div 
    class="message"
    :class="message.role"
  >
    <div class="message-avatar">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="message-bubble">
      <div class="message-text" v-html="formattedContent"></div>
      <div class="message-footer">
        <div class="message-time">{{ formattedTime }}</div>
        <button 
          v-if="message.role === 'assistant'" 
          class="copy-btn"
          @click="$emit('copy', message.content)"
          :class="{ 'copied': isCopied }"
          :title="isCopied ? 'Copiado!' : 'Copiar mensaje'"
        >
          {{ isCopied ? '✓' : '📋' }}
        </button>
        <button 
          v-if="message.role === 'assistant' && showRegenerateBtn" 
          class="regenerate-btn"
          @click="$emit('regenerate')"
          title="Regenerar respuesta"
        >
          🔄
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatMessage',
  props: {
    message: {
      type: Object,
      required: true
    },
    isCopied: {
      type: Boolean,
      default: false
    },
    showRegenerateBtn: {
      type: Boolean,
      default: false
    }
  },
  emits: ['copy', 'regenerate'],
  computed: {
    formattedTime() {
      if (!this.message.timestamp) return '';
      const date = new Date(this.message.timestamp);
      return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    },
    formattedContent() {
      // Aquí podemos agregar markdown rendering más adelante
      return this.escapeHtml(this.message.content)
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
    }
  },
  methods: {
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  }
};
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  animation: messageSlideIn 0.3s ease-out;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e2640;
  border-radius: 50%;
  font-size: 20px;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #4d6cfa;
}

.message-bubble {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 70%;
}

.message-text {
  padding: 12px 16px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  color: #e4e6eb;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
}

.message-text :deep(strong) {
  font-weight: 700;
  color: #fff;
}

.message-text :deep(em) {
  font-style: italic;
}

.message-text :deep(code) {
  background: #0a0e27;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.message.user .message-text {
  background: #4d6cfa;
  border-color: #5a7bff;
  color: white;
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}

.message.user .message-footer {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.message-time {
  font-size: 12px;
  color: #6b7280;
}

.copy-btn,
.regenerate-btn {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  opacity: 0;
}

.message:hover .copy-btn,
.message:hover .regenerate-btn {
  opacity: 1;
}

.copy-btn:hover,
.regenerate-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
  transform: scale(1.05);
}

.copy-btn.copied {
  color: #10b981;
  border-color: #10b981;
  opacity: 1;
}

.regenerate-btn:active {
  animation: spin 0.5s ease-in-out;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Light mode */
:global(#app.light-mode) .message-avatar {
  background: #f7fafc;
}

:global(#app.light-mode) .message-text {
  background: #ffffff;
  border-color: #e2e8f0;
  color: #1a202c;
}

:global(#app.light-mode) .message-text :deep(code) {
  background: #f7fafc;
}

:global(#app.light-mode) .message.user .message-text {
  background: #4d6cfa;
  color: white;
}

:global(#app.light-mode) .message-time {
  color: #718096;
}

:global(#app.light-mode) .copy-btn,
:global(#app.light-mode) .regenerate-btn {
  border-color: #e2e8f0;
  color: #4a5568;
}

:global(#app.light-mode) .copy-btn:hover,
:global(#app.light-mode) .regenerate-btn:hover {
  background: #f7fafc;
}
</style>
