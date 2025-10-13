<template>
  <transition name="modal">
    <div v-if="visible" class="shortcuts-modal" @click.self="$emit('close')">
      <div class="modal-content">
        <div class="modal-header">
          <h2>⌨️ Atajos de Teclado</h2>
          <button @click="$emit('close')" class="close-btn">✕</button>
        </div>
        
        <div class="shortcuts-grid">
          <div class="shortcut-category">
            <h3>Chat</h3>
            <div class="shortcut-item">
              <div class="shortcut-desc">Enviar mensaje</div>
              <KeyboardHint shortcut="Ctrl+Enter" size="medium" />
            </div>
            <div class="shortcut-item">
              <div class="shortcut-desc">Nuevo chat</div>
              <KeyboardHint shortcut="Ctrl+N" size="medium" />
            </div>
            <div class="shortcut-item">
              <div class="shortcut-desc">Cerrar documento</div>
              <KeyboardHint shortcut="Esc" size="medium" />
            </div>
          </div>

          <div class="shortcut-category">
            <h3>Navegación</h3>
            <div class="shortcut-item">
              <div class="shortcut-desc">Buscar documentos</div>
              <KeyboardHint shortcut="Ctrl+K" size="medium" />
            </div>
            <div class="shortcut-item">
              <div class="shortcut-desc">Mostrar atajos</div>
              <KeyboardHint shortcut="?" size="medium" />
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <p>Usa estos atajos para una experiencia más rápida</p>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import KeyboardHint from './KeyboardHint.vue';

export default {
  name: 'ShortcutsModal',
  components: {
    KeyboardHint
  },
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close']
};
</script>

<style scoped>
.shortcuts-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.modal-content {
  background: #151934;
  border: 1px solid #2a3152;
  border-radius: 16px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid #2a3152;
}

.modal-header h2 {
  font-size: 20px;
  font-weight: 700;
  color: #e4e6eb;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #9ca3af;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
}

.shortcuts-grid {
  padding: 24px;
  display: grid;
  gap: 24px;
}

.shortcut-category h3 {
  font-size: 13px;
  font-weight: 700;
  color: #6b7280;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  margin: 0 0 16px 0;
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #0a0e27;
  border: 1px solid #1e2640;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s;
}

.shortcut-item:hover {
  background: #1e2640;
  border-color: #2a3152;
  transform: translateX(4px);
}

.shortcut-item:last-child {
  margin-bottom: 0;
}

.shortcut-desc {
  font-size: 14px;
  color: #e4e6eb;
  font-weight: 500;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #2a3152;
  text-align: center;
}

.modal-footer p {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

/* Animación */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-content,
.modal-leave-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.95) translateY(20px);
}

/* Light mode */
:global(#app.light-mode) .modal-content {
  background: #ffffff;
  border-color: #e2e8f0;
}

:global(#app.light-mode) .modal-header {
  border-color: #e2e8f0;
}

:global(#app.light-mode) .modal-header h2 {
  color: #1a202c;
}

:global(#app.light-mode) .close-btn {
  border-color: #e2e8f0;
  color: #718096;
}

:global(#app.light-mode) .close-btn:hover {
  background: #f7fafc;
}

:global(#app.light-mode) .shortcut-category h3 {
  color: #718096;
}

:global(#app.light-mode) .shortcut-item {
  background: #f7fafc;
  border-color: #e2e8f0;
}

:global(#app.light-mode) .shortcut-item:hover {
  background: #edf2f7;
}

:global(#app.light-mode) .shortcut-desc {
  color: #1a202c;
}

:global(#app.light-mode) .modal-footer {
  border-color: #e2e8f0;
}

:global(#app.light-mode) .modal-footer p {
  color: #718096;
}

/* Responsive */
@media (max-width: 640px) {
  .modal-content {
    border-radius: 12px;
  }
  
  .modal-header {
    padding: 20px;
  }
  
  .modal-header h2 {
    font-size: 18px;
  }
  
  .shortcuts-grid {
    padding: 20px;
  }
}
</style>
