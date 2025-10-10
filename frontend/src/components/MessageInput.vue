<template>
  <div class="message-input-container">
    <form @submit.prevent="handleSubmit" class="message-form">
      <textarea
        v-model="localMessage"
        @keydown.enter.exact.prevent="handleSubmit"
        placeholder="Escribe tu pregunta aquí... (Enter para enviar)"
        class="message-input"
        :disabled="disabled || isSending"
        rows="1"
        ref="textarea"
      ></textarea>
      <button 
        type="submit" 
        class="send-btn" 
        :disabled="disabled || !localMessage.trim() || isSending"
        :title="buttonTitle"
      >
        <span v-if="!isSending">{{ buttonText }}</span>
        <span v-else class="spinner-small"></span>
      </button>
    </form>
    <div class="input-footer">
      <span class="char-counter" :class="{ 'warning': characterCount > maxChars * 0.9 }">
        {{ characterCount }} / {{ maxChars }}
      </span>
      <span v-if="!pdfUploaded" class="info-text">⚠️ Primero sube un PDF</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MessageInput',
  props: {
    message: {
      type: String,
      default: ''
    },
    disabled: {
      type: Boolean,
      default: false
    },
    isSending: {
      type: Boolean,
      default: false
    },
    pdfUploaded: {
      type: Boolean,
      default: false
    },
    maxChars: {
      type: Number,
      default: 2000
    },
    buttonText: {
      type: String,
      default: 'Enviar'
    }
  },
  emits: ['send', 'update:message'],
  data() {
    return {
      localMessage: this.message
    };
  },
  computed: {
    characterCount() {
      return this.localMessage.length;
    },
    buttonTitle() {
      if (!this.pdfUploaded) return 'Primero sube un PDF';
      if (this.isSending) return 'Enviando...';
      return 'Enviar mensaje (Enter)';
    }
  },
  watch: {
    message(newVal) {
      this.localMessage = newVal;
    },
    localMessage(newVal) {
      this.$emit('update:message', newVal);
      this.autoResize();
    }
  },
  methods: {
    handleSubmit() {
      if (!this.localMessage.trim() || this.disabled || this.isSending || !this.pdfUploaded) return;
      
      if (this.characterCount > this.maxChars) {
        this.$emit('error', `El mensaje es demasiado largo. Máximo ${this.maxChars} caracteres.`);
        return;
      }
      
      this.$emit('send', this.localMessage.trim());
      this.localMessage = '';
      this.resetTextarea();
    },
    autoResize() {
      this.$nextTick(() => {
        const textarea = this.$refs.textarea;
        if (textarea) {
          textarea.style.height = 'auto';
          textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }
      });
    },
    resetTextarea() {
      this.$nextTick(() => {
        const textarea = this.$refs.textarea;
        if (textarea) {
          textarea.style.height = 'auto';
        }
      });
    }
  },
  mounted() {
    this.autoResize();
  }
};
</script>

<style scoped>
.message-input-container {
  margin-top: 1rem;
}

.message-form {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  animation: fadeInUp 0.7s;
}

.message-input {
  flex: 1;
  padding: 0.8rem;
  border-radius: 8px;
  border: 2px solid #bdbdbd;
  font-size: 1.05rem;
  background: #fff;
  resize: none;
  min-height: 48px;
  max-height: 120px;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
  line-height: 1.5;
}

.message-input:focus {
  outline: none;
  border-color: #7b1fa2;
  box-shadow: 0 0 0 3px rgba(123, 31, 162, 0.1);
}

.message-input:disabled {
  background: #f5f5f5;
  color: #999;
  cursor: not-allowed;
}

.send-btn {
  background: #7b1fa2;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.9rem 1.7rem;
  font-size: 1.1rem;
  cursor: pointer;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(123, 31, 162, 0.10);
  transition: background 0.2s, transform 0.2s;
  min-width: 100px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:disabled {
  background: #bdbdbd;
  cursor: not-allowed;
  transform: none;
}

.send-btn:hover:not(:disabled) {
  background: #1976d2;
  transform: scale(1.05);
}

.spinner-small {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
  padding: 0 0.5rem;
}

.char-counter {
  font-size: 0.85rem;
  color: #888;
  transition: color 0.2s;
}

.char-counter.warning {
  color: #f44336;
  font-weight: 600;
}

.info-text {
  font-size: 0.85rem;
  color: #ff9800;
  font-weight: 500;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
