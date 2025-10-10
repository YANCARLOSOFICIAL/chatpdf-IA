<template>
  <div class="settings-panel" :class="{ 'open': isOpen }">
    <button @click="$emit('toggle')" class="settings-trigger" :title="isOpen ? 'Cerrar ajustes' : 'Abrir ajustes'">
      ⚙️
    </button>
    
    <transition name="slide">
      <div v-if="isOpen" class="settings-content">
        <div class="settings-header">
          <h3>⚙️ Configuración</h3>
          <button @click="$emit('toggle')" class="close-btn">✕</button>
        </div>
        
        <div class="settings-body">
          <!-- Temperatura -->
          <div class="setting-group">
            <label class="setting-label">
              🌡️ Temperatura
              <span class="setting-value">{{ temperature }}</span>
            </label>
            <input 
              type="range" 
              :value="temperature" 
              @input="$emit('update:temperature', parseFloat($event.target.value))"
              min="0" 
              max="2" 
              step="0.1"
              class="setting-slider"
            />
            <small class="setting-hint">Controla la creatividad de las respuestas (0 = conservador, 2 = creativo)</small>
          </div>
          
          <!-- Max Tokens -->
          <div class="setting-group">
            <label class="setting-label">
              🔤 Max Tokens
              <span class="setting-value">{{ maxTokens }}</span>
            </label>
            <input 
              type="range" 
              :value="maxTokens" 
              @input="$emit('update:maxTokens', parseInt($event.target.value))"
              min="100" 
              max="4000" 
              step="100"
              class="setting-slider"
            />
            <small class="setting-hint">Longitud máxima de las respuestas</small>
          </div>
          
          <!-- Top K Chunks -->
          <div class="setting-group">
            <label class="setting-label">
              📄 Chunks de Contexto
              <span class="setting-value">{{ topK }}</span>
            </label>
            <input 
              type="range" 
              :value="topK" 
              @input="$emit('update:topK', parseInt($event.target.value))"
              min="1" 
              max="10" 
              step="1"
              class="setting-slider"
            />
            <small class="setting-hint">Cantidad de fragmentos del PDF a usar como contexto</small>
          </div>
          
          <!-- Auto Scroll -->
          <div class="setting-group">
            <label class="setting-checkbox">
              <input 
                type="checkbox" 
                :checked="autoScroll" 
                @change="$emit('update:autoScroll', $event.target.checked)"
              />
              <span class="checkbox-label">📜 Auto-scroll activado</span>
            </label>
          </div>
          
          <!-- Mostrar Timestamps -->
          <div class="setting-group">
            <label class="setting-checkbox">
              <input 
                type="checkbox" 
                :checked="showTimestamps" 
                @change="$emit('update:showTimestamps', $event.target.checked)"
              />
              <span class="checkbox-label">🕐 Mostrar timestamps</span>
            </label>
          </div>
          
          <!-- Sonidos -->
          <div class="setting-group">
            <label class="setting-checkbox">
              <input 
                type="checkbox" 
                :checked="soundEnabled" 
                @change="$emit('update:soundEnabled', $event.target.checked)"
              />
              <span class="checkbox-label">🔔 Sonidos activados</span>
            </label>
          </div>
        </div>
        
        <div class="settings-footer">
          <button @click="$emit('reset')" class="reset-btn">
            🔄 Restaurar valores por defecto
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'SettingsPanel',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    temperature: {
      type: Number,
      default: 0.7
    },
    maxTokens: {
      type: Number,
      default: 1000
    },
    topK: {
      type: Number,
      default: 3
    },
    autoScroll: {
      type: Boolean,
      default: true
    },
    showTimestamps: {
      type: Boolean,
      default: true
    },
    soundEnabled: {
      type: Boolean,
      default: false
    }
  },
  emits: [
    'toggle', 
    'reset',
    'update:temperature',
    'update:maxTokens',
    'update:topK',
    'update:autoScroll',
    'update:showTimestamps',
    'update:soundEnabled'
  ]
};
</script>

<style scoped>
.settings-panel {
  position: fixed;
  top: 5rem;
  right: 1rem;
  z-index: 99;
}

.settings-trigger {
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid #e0e0e0;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  font-size: 1.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.settings-trigger:hover {
  transform: scale(1.1) rotate(90deg);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.settings-content {
  position: absolute;
  top: 60px;
  right: 0;
  width: 320px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #7b1fa2 0%, #1976d2 100%);
  color: #fff;
}

.settings-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: #fff;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.settings-body {
  padding: 1.25rem;
  max-height: 400px;
  overflow-y: auto;
}

.settings-body::-webkit-scrollbar {
  width: 6px;
}

.settings-body::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.settings-body::-webkit-scrollbar-thumb {
  background: #bdbdbd;
  border-radius: 3px;
}

.setting-group {
  margin-bottom: 1.5rem;
}

.setting-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}

.setting-value {
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 700;
}

.setting-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e0e0e0;
  outline: none;
  -webkit-appearance: none;
}

.setting-slider::-webkit-slider-thumb {
  appearance: none;
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1976d2;
  cursor: pointer;
  transition: background 0.2s;
}

.setting-slider::-webkit-slider-thumb:hover {
  background: #7b1fa2;
}

.setting-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #1976d2;
  cursor: pointer;
  border: none;
}

.setting-hint {
  display: block;
  color: #666;
  font-size: 0.8rem;
  margin-top: 0.4rem;
  line-height: 1.3;
}

.setting-checkbox {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.setting-checkbox input[type="checkbox"] {
  width: 20px;
  height: 20px;
  margin-right: 0.6rem;
  cursor: pointer;
  accent-color: #1976d2;
}

.checkbox-label {
  font-weight: 500;
  color: #333;
  font-size: 0.95rem;
}

.settings-footer {
  padding: 1rem 1.25rem;
  background: #f5f5f5;
  border-top: 1px solid #e0e0e0;
}

.reset-btn {
  width: 100%;
  background: #ff9800;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.7rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.reset-btn:hover {
  background: #f57c00;
  transform: translateY(-2px);
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
