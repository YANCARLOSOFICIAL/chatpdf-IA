<template>
  <div class="system-panel">
    <div class="system-grid">
      <!-- Status Card -->
      <div class="system-card status-card">
        <div class="card-header">
          <span class="card-icon">🟢</span>
          <h3>Estado del Sistema</h3>
        </div>
        <div class="card-body">
          <div class="status-item">
            <span class="status-label">Estado:</span>
            <span class="status-value healthy">Healthy</span>
          </div>
          <div class="status-item">
            <span class="status-label">Backend:</span>
            <span class="status-value">✓ Conectado</span>
          </div>
          <div class="status-item">
            <span class="status-label">Base de Datos:</span>
            <span class="status-value">✓ PostgreSQL</span>
          </div>
          <div class="status-item">
            <span class="status-label">Vector DB:</span>
            <span class="status-value">✓ pgvector</span>
          </div>
        </div>
      </div>

      <!-- LLM Config -->
      <div class="system-card llm-card">
        <div class="card-header">
          <span class="card-icon">🤖</span>
          <h3>Configuración LLM</h3>
        </div>
        <div class="card-body">
          <div class="config-group">
            <label>Proveedor:</label>
            <select v-model="localLlmProvider" class="config-select">
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI (API)</option>
            </select>
          </div>
          <div class="config-group">
            <label>Modelo:</label>
            <input v-model="localLlmModel" type="text" class="config-input">
          </div>
          <button @click="saveLlm" class="btn-save">💾 Guardar</button>
        </div>
      </div>

      <!-- Embeddings Config -->
      <div class="system-card embeddings-card">
        <div class="card-header">
          <span class="card-icon">⚡</span>
          <h3>Embeddings</h3>
        </div>
        <div class="card-body">
          <div class="embed-info">
            <span class="info-label">Modelo:</span>
            <span class="info-value">{{ embeddingModel }}</span>
          </div>
          <div class="embed-info">
            <span class="info-label">Dimensión:</span>
            <span class="info-value">{{ embeddingDimension }}</span>
          </div>
          <div class="embed-info">
            <span class="info-label">MRL:</span>
            <span class="info-value">{{ mrlCompression }}%</span>
          </div>
        </div>
      </div>

      <!-- Vector DB Info -->
      <div class="system-card vector-card">
        <div class="card-header">
          <span class="card-icon">🗄️</span>
          <h3>Base de Datos Vectorial</h3>
        </div>
        <div class="card-body">
          <div class="db-info">
            <span class="info-label">Vectores:</span>
            <span class="info-value">{{ vectorCount }}</span>
          </div>
          <div class="db-info">
            <span class="info-label">Colección:</span>
            <span class="info-value">{{ collectionName || 'N/A' }}</span>
          </div>
          <div class="db-info">
            <span class="info-label">Métrica:</span>
            <span class="info-value">{{ metric }}</span>
          </div>
        </div>
      </div>

      <!-- Recovery Config -->
      <div class="system-card recovery-card">
        <div class="card-header">
          <span class="card-icon">🔍</span>
          <h3>Recuperación</h3>
        </div>
        <div class="card-body">
          <div class="config-group">
            <label>Top-K:</label>
            <input v-model.number="localTopK" type="number" min="1" max="20" class="config-input">
          </div>
          <div class="config-group">
            <label>Umbral:</label>
            <input v-model.number="localThreshold" type="number" min="0" max="100" step="5" class="config-input">
          </div>
          <div class="config-group">
            <label>Temperatura:</label>
            <input v-model.number="localTemperature" type="number" min="0" max="2" step="0.1" class="config-input">
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SystemPanel',
  props: {
    llmProvider: String,
    llmModel: String,
    embeddingModel: String,
    embeddingDimension: Number,
    mrlCompression: Number,
    vectorCount: Number,
    collectionName: String,
    metric: String,
    topK: Number,
    threshold: Number,
    temperature: Number
  },
  emits: ['save-llm-config', 'save-emb-config'],
  data() {
    return {
      localLlmProvider: this.llmProvider || 'ollama',
      localLlmModel: this.llmModel || 'qwen3:4b',
      localTopK: this.topK || 3,
      localThreshold: this.threshold || 30,
      localTemperature: this.temperature || 0.7
    };
  },
  methods: {
    saveLlm() {
      this.$emit('save-llm-config', {
        provider: this.localLlmProvider,
        model: this.localLlmModel
      });
    }
  }
};
</script>

<style scoped>
.system-panel {
  padding: 1rem;
}

.system-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.system-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.system-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid rgba(0, 0, 0, 0.05);
}

.card-icon {
  font-size: 1.5rem;
}

.card-header h3 {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-item,
.embed-info,
.db-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
}

.status-label,
.info-label {
  font-weight: 600;
  color: #555;
}

.status-value {
  color: #27ae60;
  font-weight: 600;
}

.status-value.healthy {
  color: #27ae60;
}

.info-value {
  color: #667eea;
  font-weight: 600;
}

.config-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-group label {
  font-weight: 600;
  color: #555;
  font-size: 0.9rem;
}

.config-select,
.config-input {
  padding: 0.75rem;
  border: 2px solid rgba(102, 126, 234, 0.2);
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
}

.config-select:focus,
.config-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.btn-save {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-save:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.dark-mode .system-card {
  background: rgba(255, 255, 255, 0.05);
}

.dark-mode .card-header h3 {
  color: white;
}

.dark-mode .status-label,
.dark-mode .info-label,
.dark-mode .config-group label {
  color: rgba(255, 255, 255, 0.7);
}

.dark-mode .config-select,
.dark-mode .config-input {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-color: rgba(255, 255, 255, 0.2);
}
</style>
