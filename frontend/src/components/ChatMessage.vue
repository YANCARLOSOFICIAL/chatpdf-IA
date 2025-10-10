<template>
  <div class="chat-message" :class="[messageClass]">
    <div class="msg-content">
      <div class="msg-header">
        <div class="msg-role" :class="roleClass">
          <span class="msg-icon">{{ roleIcon }}</span>
          <span>{{ roleLabel }}</span>
        </div>
        <span class="msg-time">{{ formattedTime }}</span>
      </div>
      <div class="msg-text">{{ content }}</div>
    </div>
    <button 
      v-if="role === 'assistant'" 
      @click="$emit('copy', content)" 
      class="copy-btn"
      title="Copiar respuesta"
    >
      📋
    </button>
  </div>
</template>

<script>
export default {
  name: 'ChatMessage',
  props: {
    role: {
      type: String,
      required: true,
      validator: (value) => ['user', 'assistant'].includes(value)
    },
    content: {
      type: String,
      required: true
    },
    timestamp: {
      type: Date,
      default: () => new Date()
    }
  },
  emits: ['copy'],
  computed: {
    messageClass() {
      return this.role === 'user' ? 'user-msg' : 'ai-msg';
    },
    roleClass() {
      return this.role === 'user' ? 'user-label' : 'ai-label';
    },
    roleIcon() {
      return this.role === 'user' ? '👤' : '🤖';
    },
    roleLabel() {
      return this.role === 'user' ? 'Tú' : 'IA';
    },
    formattedTime() {
      const hours = this.timestamp.getHours().toString().padStart(2, '0');
      const minutes = this.timestamp.getMinutes().toString().padStart(2, '0');
      return `${hours}:${minutes}`;
    }
  }
};
</script>

<style scoped>
.chat-message {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.8rem;
  padding: 0.7rem 1rem;
  border-radius: 8px;
  font-size: 1rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  animation: fadeIn 0.4s;
  position: relative;
}

.msg-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.msg-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.msg-time {
  font-size: 0.75rem;
  color: #999;
  font-weight: 400;
}

.msg-text {
  word-break: break-word;
  color: #212121;
  line-height: 1.5;
}

.user-msg {
  background: #e3f2fd;
  border-left: 4px solid #1976d2;
  color: #0d47a1;
}

.ai-msg {
  background: #f1f8e9;
  border-left: 4px solid #43a047;
  color: #1b5e20;
}

.user-label {
  color: #0d47a1;
  font-weight: 700;
}

.ai-label {
  color: #1b5e20;
  font-weight: 700;
}

.copy-btn {
  background: transparent;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s, transform 0.2s;
  padding: 0.3rem;
  margin-left: 0.5rem;
}

.chat-message:hover .copy-btn {
  opacity: 0.6;
}

.copy-btn:hover {
  opacity: 1 !important;
  transform: scale(1.2);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
