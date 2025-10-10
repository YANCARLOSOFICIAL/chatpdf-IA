<template>
  <div class="pdf-viewer" :class="{ 'open': isOpen }">
    <button @click="$emit('toggle')" class="viewer-trigger" :title="isOpen ? 'Cerrar vista PDF' : 'Ver PDF'">
      📄
    </button>
    
    <transition name="slide-left">
      <div v-if="isOpen" class="viewer-content">
        <div class="viewer-header">
          <h3>📄 Vista del PDF</h3>
          <button @click="$emit('toggle')" class="close-btn">✕</button>
        </div>
        
        <div class="viewer-body">
          <div v-if="!pdfUrl" class="empty-state">
            <div class="empty-icon">📄</div>
            <p class="empty-text">No hay PDF cargado</p>
            <small class="empty-hint">Sube un PDF para ver su contenido aquí</small>
          </div>
          
          <div v-else class="pdf-container">
            <iframe 
              :src="pdfUrl" 
              class="pdf-frame"
              title="Vista PDF"
            ></iframe>
          </div>
        </div>
        
        <div v-if="pdfInfo" class="viewer-footer">
          <div class="pdf-info-item">
            <span class="info-icon">📝</span>
            <span class="info-text">{{ pdfInfo.name }}</span>
          </div>
          <div class="pdf-info-item">
            <span class="info-icon">🆔</span>
            <span class="info-text">ID: {{ pdfInfo.id }}</span>
          </div>
          <div class="pdf-info-item">
            <span class="info-icon">⚡</span>
            <span class="info-text">{{ pdfInfo.embeddingType }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'PDFViewer',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    pdfUrl: {
      type: String,
      default: null
    },
    pdfInfo: {
      type: Object,
      default: null
    }
  },
  emits: ['toggle']
};
</script>

<style scoped>
.pdf-viewer {
  position: fixed;
  top: 9rem;
  right: 1rem;
  z-index: 98;
}

.viewer-trigger {
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

.viewer-trigger:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

.viewer-content {
  position: fixed;
  top: 0;
  right: 0;
  width: 450px;
  height: 100vh;
  background: #fff;
  box-shadow: -4px 0 32px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #7b1fa2 0%, #1976d2 100%);
  color: #fff;
  flex-shrink: 0;
}

.viewer-header h3 {
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

.viewer-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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

.pdf-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.pdf-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.viewer-footer {
  padding: 1rem 1.25rem;
  background: #f5f5f5;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.pdf-info-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0;
  font-size: 0.9rem;
}

.info-icon {
  font-size: 1.2rem;
}

.info-text {
  color: #666;
  font-weight: 500;
  word-break: break-word;
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
  .viewer-content {
    width: 100%;
  }
}
</style>
