<template>
  <transition name="toast">
    <div v-if="visible" class="toast" :class="type">
      <span class="toast-icon">
        {{ icon }}
      </span>
      <span class="toast-message">{{ message }}</span>
      <button class="toast-close" @click="close">✕</button>
    </div>
  </transition>
</template>

<script>
export default {
  name: 'ToastNotification',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    message: {
      type: String,
      required: true
    },
    type: {
      type: String,
      default: 'info',
      validator: (value) => ['success', 'error', 'info', 'warning'].includes(value)
    },
    duration: {
      type: Number,
      default: 3000
    }
  },
  emits: ['close'],
  computed: {
    icon() {
      const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
      };
      return icons[this.type] || icons.info;
    }
  },
  watch: {
    visible(newVal) {
      if (newVal && this.duration > 0) {
        setTimeout(() => {
          this.close();
        }, this.duration);
      }
    }
  },
  methods: {
    close() {
      this.$emit('close');
    }
  }
};
</script>

<style scoped>
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 9999;
  max-width: 400px;
}

.toast.success {
  border-color: #10b981;
}

.toast.error {
  border-color: #ef4444;
}

.toast.info {
  border-color: #3b82f6;
}

.toast.warning {
  border-color: #f59e0b;
}

.toast-icon {
  font-size: 24px;
  line-height: 1;
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  font-size: 14px;
  color: #e4e6eb;
  font-weight: 500;
}

.toast-close {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #9ca3af;
  font-size: 18px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.toast-close:hover {
  background: #1e2640;
  color: #e4e6eb;
}

/* Animations */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(400px);
  opacity: 0;
}

.toast-leave-to {
  transform: translateY(100px);
  opacity: 0;
}

/* Light mode */
:global(#app.light-mode) .toast {
  background: #ffffff;
  border-color: #e2e8f0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

:global(#app.light-mode) .toast-message {
  color: #1a202c;
}

:global(#app.light-mode) .toast-close {
  color: #4a5568;
}

:global(#app.light-mode) .toast-close:hover {
  background: #f7fafc;
  color: #1a202c;
}

@media (max-width: 768px) {
  .toast {
    bottom: 16px;
    right: 16px;
    left: 16px;
    max-width: none;
  }
}
</style>
