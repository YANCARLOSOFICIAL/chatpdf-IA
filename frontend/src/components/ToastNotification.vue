<template>
  <transition name="toast">
    <div v-if="show" :class="['toast-notification', `toast-${type}`]">
      <span class="toast-icon">{{ icon }}</span>
      <span class="toast-message">{{ message }}</span>
    </div>
  </transition>
</template>

<script>
export default {
  name: 'ToastNotification',
  props: {
    message: {
      type: String,
      required: true
    },
    type: {
      type: String,
      default: 'success',
      validator: (value) => ['success', 'error', 'info', 'warning'].includes(value)
    },
    show: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    icon() {
      const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
      };
      return icons[this.type];
    }
  }
};
</script>

<style scoped>
.toast-notification {
  position: fixed;
  top: 2rem;
  right: 2rem;
  padding: 1rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  max-width: 400px;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  animation: slideIn 0.3s ease-out;
}

.toast-icon {
  font-size: 1.5rem;
}

.toast-message {
  flex: 1;
}

.toast-success {
  background: #4caf50;
  color: #fff;
}

.toast-error {
  background: #f44336;
  color: #fff;
}

.toast-info {
  background: #2196f3;
  color: #fff;
}

.toast-warning {
  background: #ff9800;
  color: #fff;
}

.toast-enter-active, .toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>
