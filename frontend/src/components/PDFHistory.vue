<template>
  <div class="pdf-history" :class="{ 'open': isOpen }">
    <button @click="$emit('toggle')" class="history-trigger" :title="isOpen ? 'Cerrar historial' : 'Ver historial de PDFs'">
      📚
    </button>
    
    <transition name="slide-left">
      <div v-if="isOpen" class="history-content">
        <div class="history-header">
          <h3>📚 Historial de PDFs</h3>
          <button @click="$emit('toggle')" class="close-btn">✕</button>
        </div>
        
        <div class="history-body">
          <div v-if="pdfs.length === 0" class="empty-state">
            <div class="empty-icon">📭</div>
            <p class="empty-text">No hay PDFs en el historial</p>
            <small class="empty-hint">Los PDFs que subas aparecerán aquí</small>
          </div>
          
          <div v-else class="pdf-list">
            <div 
              v-for="pdf in pdfs" 
              :key="pdf.id"
              class="pdf-item"
              :class="{ 'active': pdf.id === currentPdfId }"
              @click="$emit('select', pdf)"
            >
              <div class="pdf-item-icon">📄</div>
              <div class="pdf-item-info">
                <div class="pdf-item-name">{{ pdf.name }}</div>
                <div class="pdf-item-meta">
                  <span class="meta-item">
                    <span class="meta-icon">🆔</span>
                    {{ pdf.id }}
                  </span>
                  <span class="meta-item">
                    <span class="meta-icon">⚡</span>
                    {{ pdf.embeddingType }}
                  </span>
                </div>
                <div class="pdf-item-date">
                  {{ formatDate(pdf.uploadedAt) }}
                </div>
              </div>
              <div class="pdf-item-actions">
                <button 
                  @click.stop="$emit('delete', pdf.id)" 
                  class="delete-btn"
                  title="Eliminar PDF"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <div class="history-footer">
          <div class="history-stats">
            <span class="stat-badge">
              📊 Total: {{ pdfs.length }}
            </span>
            <span v-if="pdfs.length > 0" class="stat-badge">
              🔄 Último: {{ lastUploadTime }}
            </span>
          </div>
          <button 
            v-if="pdfs.length > 0" 
            @click="$emit('clear-all')" 
            class="clear-all-btn"
          >
            🗑️ Limpiar todo
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'PDFHistory',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    pdfs: {
      type: Array,
      default: () => []
    },
    currentPdfId: {
      type: Number,
      default: null
    }
  },
  emits: ['toggle', 'select', 'delete', 'clear-all'],
  computed: {
    lastUploadTime() {
      if (this.pdfs.length === 0) return '-';
      const lastPdf = this.pdfs[this.pdfs.length - 1];
      return this.formatDate(lastPdf.uploadedAt);
    }
  },
  methods: {
    formatDate(date) {
      if (!date) return '-';
      const d = new Date(date);
      const now = new Date();
      const diffMs = now - d;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      if (diffMins < 1) return 'Hace un momento';
      if (diffMins < 60) return `Hace ${diffMins} min`;
      if (diffHours < 24) return `Hace ${diffHours}h`;
      if (diffDays < 7) return `Hace ${diffDays}d`;
      
      return d.toLocaleDateString();
    }
  }
};
</script>

<style scoped>
.pdf-history {
  position: fixed;
  top: 13rem;
  right: 1rem;
  z-index: 97;
}

.history-trigger {
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

.history-trigger:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.history-content {
  position: fixed;
  top: 0;
  right: 0;
  width: 380px;
  height: 100vh;
  background: #fff;
  box-shadow: -4px 0 32px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #7b1fa2 0%, #1976d2 100%);
  color: #fff;
  flex-shrink: 0;
}

.history-header h3 {
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

.history-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.history-body::-webkit-scrollbar {
  width: 6px;
}

.history-body::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.history-body::-webkit-scrollbar-thumb {
  background: #bdbdbd;
  border-radius: 3px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  text-align: center;
}

.empty-icon {
  font-size: 5rem;
  opacity: 0.3;
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1.1rem;
  font-weight: 600;
  color: #666;
  margin: 0 0 0.5rem 0;
}

.empty-hint {
  color: #999;
  font-size: 0.9rem;
}

.pdf-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.pdf-item {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 10px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pdf-item:hover {
  background: #e3f2fd;
  border-color: #90caf9;
  transform: translateX(-4px);
}

.pdf-item.active {
  background: #e8f5e9;
  border-color: #4caf50;
}

.pdf-item-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.pdf-item-info {
  flex: 1;
  min-width: 0;
}

.pdf-item-name {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
  margin-bottom: 0.4rem;
  word-break: break-word;
}

.pdf-item-meta {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 0.3rem;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8rem;
  color: #666;
}

.meta-icon {
  font-size: 0.9rem;
}

.pdf-item-date {
  font-size: 0.75rem;
  color: #999;
}

.pdf-item-actions {
  flex-shrink: 0;
}

.delete-btn {
  background: transparent;
  border: none;
  font-size: 1.3rem;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.2s;
  padding: 0.3rem;
}

.delete-btn:hover {
  opacity: 1;
  transform: scale(1.2);
}

.history-footer {
  padding: 1rem 1.25rem;
  background: #f5f5f5;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.history-stats {
  display: flex;
  gap: 0.6rem;
  margin-bottom: 0.8rem;
  flex-wrap: wrap;
}

.stat-badge {
  background: #fff;
  padding: 0.4rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
  color: #666;
  border: 1px solid #e0e0e0;
}

.clear-all-btn {
  width: 100%;
  background: #f44336;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.7rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.clear-all-btn:hover {
  background: #d32f2f;
  transform: translateY(-2px);
}

.slide-left-enter-active, .slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.slide-left-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

@media (max-width: 768px) {
  .history-content {
    width: 100%;
  }
}
</style>
