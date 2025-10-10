<template>
  <div class="documents-panel">
    <div class="panel-header">
      <h2>📄 Gestión de Documentos</h2>
      <button class="refresh-button" @click="refreshDocuments">
        <span class="refresh-icon">🔄</span>
        Actualizar
      </button>
    </div>

    <!-- Upload Section -->
    <div class="upload-section">
      <div class="upload-card">
        <div class="upload-icon">📤</div>
        <h3>Cargar Nuevo Documento</h3>
        <p>Sube archivos PDF para consultar con IA</p>
        
        <div class="upload-area" 
             @dragover.prevent="isDragging = true"
             @dragleave="isDragging = false"
             @drop.prevent="handleDrop"
             :class="{ dragging: isDragging }">
          <input 
            type="file" 
            ref="fileInput"
            accept=".pdf"
            @change="handleFileSelect"
            style="display: none"
          />
          <div class="upload-content">
            <span class="upload-emoji">📁</span>
            <p class="upload-text">Arrastra un PDF aquí o</p>
            <button class="browse-button" @click="$refs.fileInput.click()">
              Seleccionar archivo
            </button>
            <p class="upload-hint">Máximo 10MB • Solo PDF</p>
          </div>
        </div>

        <div v-if="selectedFile" class="selected-file">
          <span class="file-icon">📄</span>
          <div class="file-info">
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
          </div>
          <button class="remove-file" @click="selectedFile = null">✕</button>
        </div>

        <button 
          class="upload-button" 
          :disabled="!selectedFile || isUploading"
          @click="uploadDocument"
        >
          <span v-if="!isUploading">⬆️ Cargar Documento</span>
          <span v-else class="loading-text">
            <span class="spinner"></span>
            Procesando...
          </span>
        </button>
      </div>
    </div>

    <!-- Documents List -->
    <div class="documents-list">
      <div class="list-header">
        <h3>📚 Documentos Cargados ({{ documents.length }})</h3>
        <div class="list-actions">
          <button class="action-button" @click="sortBy = 'date'">
            📅 Fecha
          </button>
          <button class="action-button" @click="sortBy = 'name'">
            🔤 Nombre
          </button>
          <button class="action-button danger" @click="clearAllDocuments">
            🗑️ Limpiar Todo
          </button>
        </div>
      </div>

      <div v-if="documents.length === 0" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>No hay documentos cargados</p>
        <p class="empty-hint">Carga tu primer PDF para comenzar</p>
      </div>

      <div v-else class="documents-grid">
        <div 
          v-for="doc in sortedDocuments" 
          :key="doc.id"
          class="document-card"
          :class="{ active: doc.id === activeDocumentId }"
        >
          <div class="doc-header">
            <span class="doc-icon">📄</span>
            <div class="doc-status" :class="doc.status">
              <span class="status-dot"></span>
              {{ getStatusText(doc.status) }}
            </div>
          </div>
          
          <div class="doc-body">
            <h4 class="doc-name" :title="doc.name">{{ doc.name }}</h4>
            <div class="doc-meta">
              <span class="meta-item">
                <span class="meta-icon">📊</span>
                {{ doc.pages }} páginas
              </span>
              <span class="meta-item">
                <span class="meta-icon">💾</span>
                {{ formatFileSize(doc.size) }}
              </span>
              <span class="meta-item">
                <span class="meta-icon">🕐</span>
                {{ formatDate(doc.uploadedAt) }}
              </span>
            </div>
            
            <div class="doc-info">
              <span class="info-item">
                <strong>Chunks:</strong> {{ doc.chunks || 0 }}
              </span>
              <span class="info-item">
                <strong>Vectores:</strong> {{ doc.vectors || 0 }}
              </span>
              <span class="info-item">
                <strong>Modelo:</strong> {{ doc.embeddingModel }}
              </span>
            </div>
          </div>
          
          <div class="doc-actions">
            <button 
              class="doc-button primary"
              @click="selectDocument(doc)"
              :disabled="doc.id === activeDocumentId"
            >
              💬 Usar
            </button>
            <button class="doc-button secondary" @click="viewDocument(doc)">
              👁️ Ver
            </button>
            <button class="doc-button danger" @click="deleteDocument(doc.id)">
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DocumentsPanel',
  props: {
    documents: {
      type: Array,
      default: () => []
    },
    activeDocumentId: {
      type: String,
      default: null
    }
  },
  emits: ['upload', 'select', 'delete', 'view', 'refresh', 'clear-all'],
  data() {
    return {
      selectedFile: null,
      isUploading: false,
      isDragging: false,
      sortBy: 'date'
    };
  },
  computed: {
    sortedDocuments() {
      const docs = [...this.documents];
      if (this.sortBy === 'date') {
        return docs.sort((a, b) => new Date(b.uploadedAt) - new Date(a.uploadedAt));
      } else {
        return docs.sort((a, b) => a.name.localeCompare(b.name));
      }
    }
  },
  methods: {
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file && file.type === 'application/pdf') {
        this.selectedFile = file;
      }
    },
    handleDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer.files[0];
      if (file && file.type === 'application/pdf') {
        this.selectedFile = file;
      }
    },
    async uploadDocument() {
      if (!this.selectedFile) return;
      this.isUploading = true;
      this.$emit('upload', this.selectedFile);
      // Reset after a delay (parent should handle actual upload)
      setTimeout(() => {
        this.isUploading = false;
        this.selectedFile = null;
      }, 2000);
    },
    selectDocument(doc) {
      this.$emit('select', doc);
    },
    viewDocument(doc) {
      this.$emit('view', doc);
    },
    deleteDocument(id) {
      if (confirm('¿Estás seguro de eliminar este documento?')) {
        this.$emit('delete', id);
      }
    },
    refreshDocuments() {
      this.$emit('refresh');
    },
    clearAllDocuments() {
      if (confirm('¿Estás seguro de eliminar TODOS los documentos?')) {
        this.$emit('clear-all');
      }
    },
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    },
    formatDate(date) {
      const now = new Date();
      const diffMs = now - new Date(date);
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      if (diffMins < 60) return `Hace ${diffMins} min`;
      if (diffHours < 24) return `Hace ${diffHours}h`;
      if (diffDays < 7) return `Hace ${diffDays}d`;
      return new Date(date).toLocaleDateString();
    },
    getStatusText(status) {
      const statusMap = {
        'ready': 'Listo',
        'processing': 'Procesando',
        'error': 'Error'
      };
      return statusMap[status] || 'Desconocido';
    }
  }
};
</script>

<style scoped>
.documents-panel {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.panel-header h2 {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.refresh-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(0, 188, 212, 0.2);
  border: 1px solid rgba(0, 188, 212, 0.4);
  border-radius: 8px;
  color: #00bcd4;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.refresh-button:hover {
  background: rgba(0, 188, 212, 0.3);
  transform: rotate(180deg);
}

/* Upload Section */
.upload-section {
  margin-bottom: 32px;
}

.upload-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 32px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.upload-card h3 {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px 0;
}

.upload-card p {
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 24px 0;
}

.upload-area {
  border: 2px dashed rgba(0, 188, 212, 0.3);
  border-radius: 12px;
  padding: 40px;
  background: rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  cursor: pointer;
}

.upload-area.dragging {
  border-color: #00bcd4;
  background: rgba(0, 188, 212, 0.1);
  transform: scale(1.02);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-emoji {
  font-size: 64px;
}

.upload-text {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.browse-button {
  padding: 10px 24px;
  background: linear-gradient(135deg, #00bcd4, #0097a7);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.browse-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 188, 212, 0.4);
}

.upload-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding: 16px;
  background: rgba(0, 188, 212, 0.1);
  border: 1px solid rgba(0, 188, 212, 0.3);
  border-radius: 8px;
}

.file-icon {
  font-size: 32px;
}

.file-info {
  flex: 1;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  color: #fff;
  font-weight: 600;
  font-size: 14px;
}

.file-size {
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.remove-file {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
  cursor: pointer;
  transition: all 0.3s ease;
}

.remove-file:hover {
  background: rgba(244, 67, 54, 0.3);
  transform: rotate(90deg);
}

.upload-button {
  width: 100%;
  margin-top: 20px;
  padding: 14px;
  background: linear-gradient(135deg, #00bcd4, #0097a7);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 600;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 188, 212, 0.4);
}

.upload-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Documents List */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.list-header h3 {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.list-actions {
  display: flex;
  gap: 8px;
}

.action-button {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.action-button.danger {
  border-color: rgba(244, 67, 54, 0.3);
  color: #f44336;
}

.action-button.danger:hover {
  background: rgba(244, 67, 54, 0.1);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 72px;
  margin-bottom: 16px;
  display: block;
}

.empty-state p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 16px;
  margin: 8px 0;
}

.empty-hint {
  font-size: 14px !important;
  color: rgba(255, 255, 255, 0.4) !important;
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.document-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.document-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  border-color: rgba(0, 188, 212, 0.3);
}

.document-card.active {
  border-color: #00bcd4;
  background: rgba(0, 188, 212, 0.08);
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.doc-icon {
  font-size: 32px;
}

.doc-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.doc-status.ready {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.doc-status.processing {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.doc-status.error {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s ease-in-out infinite;
}

.doc-body {
  margin-bottom: 16px;
}

.doc-name {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
}

.meta-icon {
  font-size: 14px;
}

.doc-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.info-item {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}

.info-item strong {
  color: #00bcd4;
}

.doc-actions {
  display: flex;
  gap: 8px;
}

.doc-button {
  flex: 1;
  padding: 8px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.doc-button.primary {
  background: linear-gradient(135deg, #00bcd4, #0097a7);
  color: #fff;
}

.doc-button.primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 188, 212, 0.4);
}

.doc-button.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.doc-button.secondary {
  background: rgba(156, 39, 176, 0.2);
  border: 1px solid rgba(156, 39, 176, 0.4);
  color: #9c27b0;
}

.doc-button.secondary:hover {
  background: rgba(156, 39, 176, 0.3);
}

.doc-button.danger {
  background: rgba(244, 67, 54, 0.2);
  border: 1px solid rgba(244, 67, 54, 0.4);
  color: #f44336;
}

.doc-button.danger:hover {
  background: rgba(244, 67, 54, 0.3);
}

@media (max-width: 768px) {
  .documents-panel {
    padding: 16px;
  }
  
  .documents-grid {
    grid-template-columns: 1fr;
  }
  
  .list-actions {
    flex-direction: column;
    width: 100%;
  }
  
  .action-button {
    width: 100%;
  }
}
</style>
