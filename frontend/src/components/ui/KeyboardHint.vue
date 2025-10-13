<template>
  <div class="keyboard-hint" :class="size">
    <kbd v-for="(key, index) in keys" :key="index" class="key">
      {{ key }}
    </kbd>
  </div>
</template>

<script>
export default {
  name: 'KeyboardHint',
  props: {
    shortcut: {
      type: String,
      required: true
    },
    size: {
      type: String,
      default: 'small', // 'small' | 'medium' | 'large'
      validator: (value) => ['small', 'medium', 'large'].includes(value)
    }
  },
  computed: {
    keys() {
      // Detectar sistema operativo
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      
      // Reemplazar Ctrl/Cmd según el sistema
      let shortcut = this.shortcut;
      if (isMac) {
        shortcut = shortcut.replace(/Ctrl/gi, '⌘');
      }
      
      // Separar por +
      return shortcut.split('+').map(k => k.trim());
    }
  }
};
</script>

<style scoped>
.keyboard-hint {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-bottom-width: 2px;
  border-radius: 4px;
  color: #9ca3af;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  min-width: 20px;
  padding: 4px 6px;
  text-align: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.keyboard-hint.medium .key {
  font-size: 12px;
  min-width: 24px;
  padding: 5px 8px;
  border-radius: 5px;
}

.keyboard-hint.large .key {
  font-size: 14px;
  min-width: 28px;
  padding: 6px 10px;
  border-radius: 6px;
}

/* Light mode */
:global(#app.light-mode) .key {
  background: #f7fafc;
  border-color: #cbd5e0;
  color: #4a5568;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
</style>
