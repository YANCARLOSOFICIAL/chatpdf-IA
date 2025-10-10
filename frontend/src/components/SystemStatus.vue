<template>
  <div class="system-status">
    <div class="status-header">
      <h2>Estado del Sistema</h2>
      <span class="status-badge" :class="statusClass">
        <span class="status-dot"></span>
        {{ statusText }}
      </span>
    </div>

    <div class="status-grid">
      <!-- Modelo LLM Card -->
      <div class="status-card llm-card">
        <div class="card-header">
          <span class="card-icon">🤖</span>
          <h3>Modelo LLM</h3>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">Proveedor:</span>
            <span class="value">{{ llmProvider }}</span>
          </div>
          <div class="info-row">
            <span class="label">Modelo:</span>
            <span class="value">{{ llmModel }}</span>
          </div>
        </div>
      </div>

      <!-- Embeddings Card -->
      <div class="status-card embeddings-card">
        <div class="card-header">
          <span class="card-icon">⚡</span>
          <h3>Embeddings</h3>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">Modelo:</span>
            <span class="value">{{ embeddingModel }}</span>
          </div>
          <div class="info-row">
            <span class="label">Dimensión:</span>
            <span class="value">{{ embeddingDimension }}</span>
          </div>
          <div class="info-row">
            <span class="label">MRL:</span>
            <span class="value">
              <span class="status-indicator active"></span>
              Activo ({{ mrlCompression }}% compresión)
            </span>
          </div>
        </div>
      </div>

      <!-- Base de Datos Card -->
      <div class="status-card database-card">
        <div class="card-header">
          <span class="card-icon">🗄️</span>
          <h3>Base de Datos Vectorial</h3>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">Vectores:</span>
            <span class="value">{{ vectorCount }}</span>
          </div>
          <div class="info-row">
            <span class="label">Colección:</span>
            <span class="value">{{ collectionName || 'Default' }}</span>
          </div>
          <div class="info-row">
            <span class="label">Métrica:</span>
            <span class="value">{{ metric }}</span>
          </div>
        </div>
      </div>

      <!-- Configuración de Recuperación Card -->
      <div class="status-card retrieval-card">
        <div class="card-header">
          <span class="card-icon">🔍</span>
          <h3>Configuración de Recuperación</h3>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">Top-K:</span>
            <span class="value">{{ topK }}</span>
          </div>
          <div class="info-row">
            <span class="label">Umbral:</span>
            <span class="value">{{ threshold }}%</span>
          </div>
          <div class="info-row">
            <span class="label">Temperatura:</span>
            <span class="value">{{ temperature }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Configuration Section -->
    <div class="config-section">
      <h3>Configurar Modelos</h3>
      
      <div class="config-grid">
        <div class="config-card">
          <div class="config-header">
            <span class="card-icon">💡</span>
            <h4>Modelo LLM</h4>
          </div>
          <div class="config-body">
            <label>Proveedor</label>
            <select v-model="selectedLlmProvider" class="config-select">
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI</option>
            </select>
            
            <label>Modelo</label>
            <select v-model="selectedLlmModel" class="config-select">
              <option value="qwen3:4b">qwen3:4b</option>
              <option value="llama2">llama2</option>
              <option value="mistral">mistral</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              <option value="gpt-4">GPT-4</option>
            </select>
            
            <button class="save-button" @click="saveLlmConfig">
              <span class="button-icon">💾</span>
              Guardar Configuración LLM
            </button>
          </div>
        </div>

        <div class="config-card">
          <div class="config-header">
            <span class="card-icon">🧬</span>
            <h4>Modelo de Embeddings</h4>
          </div>
          <div class="config-body">
            <label>Proveedor</label>
            <select v-model="selectedEmbProvider" class="config-select">
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI</option>
            </select>
            
            <label>Modelo</label>
            <select v-model="selectedEmbModel" class="config-select">
              <option value="embeddinggemma">embeddinggemma</option>
              <option value="nomic-embed-text">nomic-embed-text</option>
              <option value="text-embedding-ada-002">text-embedding-ada-002</option>
              <option value="text-embedding-3-small">text-embedding-3-small</option>
            </select>

            <div class="warning-box">
              <span class="warning-icon">⚠️</span>
              <span>Cambiar el modelo de embeddings requiere reindexar todos los documentos.</span>
            </div>
            
            <button class="save-button secondary" @click="saveEmbConfig">
              <span class="button-icon">💾</span>
              Guardar Configuración Embeddings
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SystemStatus',
  props: {
    llmProvider: {
      type: String,
      default: 'ollama'
    },
    llmModel: {
      type: String,
      default: 'qwen3:4b'
    },
    embeddingModel: {
      type: String,
      default: 'embeddinggemma'
    },
    embeddingDimension: {
      type: Number,
      default: 512
    },
    mrlCompression: {
      type: Number,
      default: 33.3
    },
    vectorCount: {
      type: Number,
      default: 60
    },
    collectionName: {
      type: String,
      default: ''
    },
    metric: {
      type: String,
      default: 'L2'
    },
    topK: {
      type: Number,
      default: 5
    },
    threshold: {
      type: Number,
      default: 30
    },
    temperature: {
      type: Number,
      default: 0.7
    }
  },
  emits: ['save-llm-config', 'save-emb-config'],
  data() {
    return {
      selectedLlmProvider: this.llmProvider,
      selectedLlmModel: this.llmModel,
      selectedEmbProvider: 'ollama',
      selectedEmbModel: this.embeddingModel,
      isHealthy: true
    };
  },
  computed: {
    statusClass() {
      return this.isHealthy ? 'healthy' : 'error';
    },
    statusText() {
      return this.isHealthy ? 'Healthy' : 'Error';
    }
  },
  methods: {
    saveLlmConfig() {
      this.$emit('save-llm-config', {
        provider: this.selectedLlmProvider,
        model: this.selectedLlmModel
      });
    },
    saveEmbConfig() {
      this.$emit('save-emb-config', {
        provider: this.selectedEmbProvider,
        model: this.selectedEmbModel
      });
    }
  }
};
</script>

<style scoped>
.system-status {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.status-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
}

.status-badge.healthy {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
  border: 1px solid rgba(76, 175, 80, 0.4);
}

.status-badge.error {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
  border: 1px solid rgba(244, 67, 54, 0.4);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.status-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.status-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  border-color: rgba(0, 188, 212, 0.3);
}

.llm-card { border-left: 4px solid #00bcd4; }
.embeddings-card { border-left: 4px solid #9c27b0; }
.database-card { border-left: 4px solid #4caf50; }
.retrieval-card { border-left: 4px solid #ff9800; }

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.card-icon {
  font-size: 28px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.card-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.info-row:last-child {
  border-bottom: none;
}

.label {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  font-weight: 500;
}

.value {
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4caf50;
  animation: pulse 2s ease-in-out infinite;
}

/* Configuration Section */
.config-section {
  margin-top: 32px;
}

.config-section h3 {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 20px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.config-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.config-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(0, 188, 212, 0.2);
}

.config-header h4 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.config-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-body label {
  color: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
}

.config-select {
  width: 100%;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.config-select:hover {
  border-color: rgba(0, 188, 212, 0.5);
  background: rgba(0, 0, 0, 0.4);
}

.config-select:focus {
  outline: none;
  border-color: #00bcd4;
  box-shadow: 0 0 0 3px rgba(0, 188, 212, 0.2);
}

.warning-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 152, 0, 0.1);
  border: 1px solid rgba(255, 152, 0, 0.3);
  border-radius: 8px;
  color: #ffa726;
  font-size: 13px;
  line-height: 1.5;
}

.warning-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.save-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #00bcd4, #0097a7);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 8px;
}

.save-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 188, 212, 0.4);
}

.save-button.secondary {
  background: linear-gradient(135deg, #9c27b0, #7b1fa2);
}

.save-button.secondary:hover {
  box-shadow: 0 6px 20px rgba(156, 39, 176, 0.4);
}

.button-icon {
  font-size: 16px;
}

/* Dark mode */
:deep(.dark-mode) .status-card {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.08);
}

:deep(.dark-mode) .config-card {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.08);
}

@media (max-width: 768px) {
  .system-status {
    padding: 16px;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
