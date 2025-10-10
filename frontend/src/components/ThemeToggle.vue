<template>
  <div class="theme-toggle">
    <button @click="toggleTheme" class="theme-btn" :title="themeTitle">
      <span class="theme-icon">{{ themeIcon }}</span>
    </button>
  </div>
</template>

<script>
export default {
  name: 'ThemeToggle',
  props: {
    isDark: {
      type: Boolean,
      default: false
    }
  },
  emits: ['toggle'],
  computed: {
    themeIcon() {
      return this.isDark ? '☀️' : '🌙';
    },
    themeTitle() {
      return this.isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
    }
  },
  methods: {
    toggleTheme() {
      this.$emit('toggle', !this.isDark);
    }
  }
};
</script>

<style scoped>
.theme-toggle {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 100;
}

.theme-btn {
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid #e0e0e0;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.theme-btn:hover {
  transform: scale(1.1) rotate(20deg);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.theme-icon {
  font-size: 1.5rem;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
