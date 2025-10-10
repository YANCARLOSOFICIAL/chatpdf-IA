<template>
  <div class="tips-sidebar">
    <div class="tips-card">
      <div class="card-icon">💡</div>
      <h3>Consejos de Uso</h3>
      <ul class="tips-list">
        <li v-for="(tip, index) in tips" :key="index">
          <span class="tip-bullet">•</span>
          <span>{{ tip }}</span>
        </li>
      </ul>
    </div>

    <div class="features-card">
      <div class="card-icon">🎯</div>
      <h3>Características</h3>
      <ul class="features-list">
        <li v-for="(feature, index) in features" :key="index">
          <span class="feature-check">✓</span>
          <span>{{ feature }}</span>
        </li>
      </ul>
    </div>

    <div class="stats-card">
      <div class="card-icon">📊</div>
      <h3>Estadísticas</h3>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-value">{{ totalDocuments }}</span>
          <span class="stat-label">Documentos</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ totalMessages }}</span>
          <span class="stat-label">Mensajes</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ totalTokens }}</span>
          <span class="stat-label">Tokens</span>
        </div>
      </div>
    </div>

    <div class="shortcuts-card">
      <div class="card-icon">⌨️</div>
      <h3>Atajos de Teclado</h3>
      <ul class="shortcuts-list">
        <li v-for="(shortcut, index) in shortcuts" :key="index">
          <kbd>{{ shortcut.keys }}</kbd>
          <span>{{ shortcut.action }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TipsSidebar',
  props: {
    totalDocuments: {
      type: Number,
      default: 0
    },
    totalMessages: {
      type: Number,
      default: 0
    },
    totalTokens: {
      type: Number,
      default: 0
    }
  },
  data() {
    return {
      tips: [
        'Carga documentos en la pestaña "Documentos"',
        'Haz preguntas específicas sobre el contenido',
        'El sistema citará las fuentes utilizadas',
        'Usa contexto conversacional para mejores respuestas'
      ],
      features: [
        'Local-First con Ollama',
        'EmbeddingGemma con MRL',
        'Milvus Lite VectorDB',
        'Conmutabilidad Cloud/Local',
        'Multimodal (texto + imágenes)'
      ],
      shortcuts: [
        { keys: 'Ctrl+L', action: 'Limpiar chat' },
        { keys: 'Ctrl+K', action: 'Focus input' },
        { keys: 'Ctrl+/', action: 'Configuración' },
        { keys: 'Esc', action: 'Cerrar paneles' }
      ]
    };
  }
};
</script>

<style scoped>
.tips-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.tips-card,
.features-card,
.stats-card,
.shortcuts-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.card-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

h3 {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 16px 0;
}

.tips-list,
.features-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tips-list li,
.features-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  line-height: 1.5;
}

.tip-bullet {
  color: #00bcd4;
  font-size: 20px;
  line-height: 1;
}

.feature-check {
  color: #4caf50;
  font-weight: 700;
  font-size: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  border: 1px solid rgba(0, 188, 212, 0.2);
}

.stat-value {
  color: #00bcd4;
  font-size: 24px;
  font-weight: 700;
}

.stat-label {
  color: rgba(255, 255, 255, 0.6);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.shortcuts-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.shortcuts-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

kbd {
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #00bcd4;
  font-weight: 600;
  min-width: 60px;
  text-align: center;
}

/* Scrollbar */
.tips-sidebar::-webkit-scrollbar {
  width: 6px;
}

.tips-sidebar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.tips-sidebar::-webkit-scrollbar-thumb {
  background: rgba(0, 188, 212, 0.3);
  border-radius: 3px;
}

.tips-sidebar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 188, 212, 0.5);
}

/* Dark mode */
:deep(.dark-mode) .tips-card,
:deep(.dark-mode) .features-card,
:deep(.dark-mode) .stats-card,
:deep(.dark-mode) .shortcuts-card {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.08);
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
