<template>
  <div class="file-uploader">
    <h3 class="section-title">📄 Cargar PDF</h3>
    <form @submit.prevent="handleSubmit" class="upload-form">
      <label class="file-label">
        <span class="file-icon">📎</span>
        <input 
          type="file" 
          @change="handleFileChange" 
          accept=".pdf" 
          class="file-input"
          :disabled="isUploading"
        />
        Seleccionar PDF
      </label>
      
      <span v-if="fileName" class="file-name">{{ fileName }}</span>
      <span v-else class="file-name file-name-empty">No hay archivo seleccionado</span>
      
      <select v-model="localEmbeddingType" class="select-input" :disabled="isUploading">
        <option value="openai">OpenAI</option>
        <option value="ollama">Ollama</option>
      </select>
      
      <button type="submit" class="upload-btn" :disabled="isUploading || !selectedFile">
        <span v-if="!isUploading" class="upload-icon">⬆️</span>
        <span v-else class="spinner"></span>
        {{ isUploading ? 'Subiendo...' : 'Subir PDF' }}
      </button>
    </form>
    
    <p class="help-text">Selecciona un archivo PDF y el modelo de IA para comenzar (máx {{ maxSizeMB }}MB)</p>
    
    <div v-if="uploadedFile" class="file-info">
      <div class="info-card">
        <span class="info-icon">✅</span>
        <div class="info-content">
          <strong>PDF Cargado:</strong> {{ uploadedFile.name }}
          <br>
          <small>Modelo: {{ uploadedFile.embeddingType }} | ID: {{ uploadedFile.id }}</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileUploader',
  props: {
    isUploading: {
      type: Boolean,
      default: false
    },
    embeddingType: {
      type: String,
      default: 'openai'
    },
    maxSizeMB: {
      type: Number,
      default: 10
    },
    uploadedFile: {
      type: Object,
      default: null
    }
  },
  emits: ['upload', 'error'],
  data() {
    return {
      selectedFile: null,
      fileName: '',
      localEmbeddingType: this.embeddingType
    };
  },
  watch: {
    embeddingType(newVal) {
      this.localEmbeddingType = newVal;
    },
    localEmbeddingType(newVal) {
      this.$emit('update:embeddingType', newVal);
    }
  },
  methods: {
    handleFileChange(event) {
      this.selectedFile = event.target.files[0];
      this.fileName = this.selectedFile ? this.selectedFile.name : '';
      
      if (this.selectedFile) {
        const maxSize = this.maxSizeMB * 1024 * 1024;
        if (this.selectedFile.size > maxSize) {
          this.$emit('error', `El archivo es demasiado grande. Máximo ${this.maxSizeMB}MB`);
          this.selectedFile = null;
          this.fileName = '';
          event.target.value = '';
        }
      }
    },
    handleSubmit() {
      if (!this.selectedFile) {
        this.$emit('error', 'Por favor selecciona un archivo PDF');
        return;
      }
      
      this.$emit('upload', {
        file: this.selectedFile,
        embeddingType: this.localEmbeddingType
      });
    }
  }
};
</script>

<style scoped>
.file-uploader {
  margin-bottom: 2rem;
}

.section-title {
  color: #7b1fa2;
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 1rem;
}

.upload-form {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  animation: fadeInUp 0.7s;
}

.file-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #ede7f6;
  border-radius: 8px;
  padding: 0.7rem 1.2rem;
  cursor: pointer;
  font-weight: 500;
  border: 2px dashed #7b1fa2;
  min-width: 160px;
  transition: border-color 0.2s, background 0.2s;
}

.file-label:hover {
  border-color: #1976d2;
  background: #e1f5fe;
}

.file-icon {
  font-size: 1.3rem;
}

.file-input {
  display: none;
}

.file-name {
  font-size: 1rem;
  color: #1976d2;
  font-weight: 600;
  margin-left: 0.5rem;
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-name-empty {
  color: #888;
  font-weight: 400;
}

.select-input {
  padding: 0.6rem;
  border-radius: 6px;
  border: 1px solid #90caf9;
  background: #f7f7f7;
  font-size: 1rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.select-input:hover {
  border-color: #1976d2;
}

.upload-btn {
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.9rem 1.7rem;
  font-size: 1.1rem;
  cursor: pointer;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 2px 8px rgba(25, 118, 210, 0.10);
  transition: background 0.2s, transform 0.2s;
}

.upload-btn:hover:not(:disabled) {
  background: #7b1fa2;
  transform: scale(1.05);
}

.upload-btn:disabled {
  background: #bdbdbd;
  cursor: not-allowed;
  transform: scale(1);
}

.upload-icon {
  font-size: 1.3rem;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.help-text {
  text-align: center;
  font-size: 0.95rem;
  color: #888;
  margin-top: 0.5rem;
}

.file-info {
  margin-top: 1rem;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  background: #e8f5e9;
  border-left: 4px solid #4caf50;
  padding: 0.8rem 1rem;
  border-radius: 8px;
  animation: fadeIn 0.4s;
}

.info-icon {
  font-size: 1.5rem;
}

.info-content {
  flex: 1;
  font-size: 0.95rem;
  color: #2e7d32;
}

.info-content strong {
  font-weight: 600;
}

.info-content small {
  color: #558b2f;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
