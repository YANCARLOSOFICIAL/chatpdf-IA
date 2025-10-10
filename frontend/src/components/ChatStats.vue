<template>
  <div class="chat-stats">
    <h4 class="stats-title">📊 Estadísticas</h4>
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-icon">💬</span>
        <div class="stat-info">
          <div class="stat-value">{{ totalMessages }}</div>
          <div class="stat-label">Mensajes</div>
        </div>
      </div>
      
      <div class="stat-card">
        <span class="stat-icon">👤</span>
        <div class="stat-info">
          <div class="stat-value">{{ userMessages }}</div>
          <div class="stat-label">Tus preguntas</div>
        </div>
      </div>
      
      <div class="stat-card">
        <span class="stat-icon">🤖</span>
        <div class="stat-info">
          <div class="stat-value">{{ aiMessages }}</div>
          <div class="stat-label">Respuestas IA</div>
        </div>
      </div>
      
      <div class="stat-card">
        <span class="stat-icon">🔤</span>
        <div class="stat-info">
          <div class="stat-value">{{ estimatedTokens }}</div>
          <div class="stat-label">Tokens (aprox)</div>
        </div>
      </div>
      
      <div class="stat-card">
        <span class="stat-icon">⚡</span>
        <div class="stat-info">
          <div class="stat-value">{{ embeddingType }}</div>
          <div class="stat-label">Modelo</div>
        </div>
      </div>
      
      <div class="stat-card">
        <span class="stat-icon">📄</span>
        <div class="stat-info">
          <div class="stat-value">{{ pdfName || '-' }}</div>
          <div class="stat-label">PDF Actual</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatStats',
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    embeddingType: {
      type: String,
      default: 'openai'
    },
    pdfName: {
      type: String,
      default: ''
    }
  },
  computed: {
    totalMessages() {
      return this.messages.length;
    },
    userMessages() {
      return this.messages.filter(m => m.role === 'user').length;
    },
    aiMessages() {
      return this.messages.filter(m => m.role === 'assistant').length;
    },
    estimatedTokens() {
      // Estimación aproximada: ~4 caracteres por token
      const totalChars = this.messages.reduce((sum, msg) => sum + msg.content.length, 0);
      return Math.ceil(totalChars / 4);
    }
  }
};
</script>

<style scoped>
.chat-stats {
  margin-top: 1.5rem;
  padding: 1rem;
  background: linear-gradient(135deg, #f5f5f5 0%, #e8eaf6 100%);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stats-title {
  color: #7b1fa2;
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 1rem;
  text-align: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.8rem;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  font-size: 1.8rem;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: 700;
  color: #1976d2;
  line-height: 1.2;
  word-break: break-word;
}

.stat-label {
  font-size: 0.75rem;
  color: #666;
  margin-top: 0.2rem;
}
</style>
