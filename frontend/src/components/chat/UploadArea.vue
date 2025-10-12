<template>
  <div class="upload-area">
    <div class="upload-card">
      <div class="upload-icon">📄</div>
      <h2>Sube tu documento PDF</h2>
      <p>Arrastra y suelta un archivo o haz clic para seleccionar</p>
      
      <div class="upload-controls">
        <label class="file-input-wrapper">
          <input 
            type="file" 
            accept=".pdf" 
            @change="handleFileSelect"
            ref="fileInput"
          />
          <span class="btn-upload">
            {{ selectedFileName || '📁 Seleccionar PDF' }}
          </span>
        </label>

        <select 
          v-model="localEmbeddingType" 
          class="select-embedding"
          @change="$emit('update:embeddingType', localEmbeddingType)"
        >
          <option value="openai">OpenAI Embeddings</option>
          <option value="ollama">Ollama Embeddings</option>
        </select>

        <button 
          class="btn-submit"
          @click="handleUpload"
          :disabled="!selectedFile || isUploading"
        >
          {{ isUploading ? '⏳ Subiendo...' : '↑ Subir Documento' }}
        </button>

        <ProgressBar :progress="uploadProgress" :visible="isUploading" />
      </div>
    </div>
  </div>
</template>

<script>
import ProgressBar from '../ui/ProgressBar.vue';

export default {
  name: 'UploadArea',
  components: {
    ProgressBar
  },
  props: {
    embeddingType: {
      type: String,
      default: 'openai'
    },
    isUploading: {
      type: Boolean,
      default: false
    },
    uploadProgress: {
      type: Number,
      default: 0
    }
  },
  emits: ['upload', 'update:embeddingType'],
  data() {
    return {
      selectedFile: null,
      localEmbeddingType: this.embeddingType
    };
  },
  computed: {
    selectedFileName() {
      return this.selectedFile ? this.selectedFile.name : '';
    }
  },
  watch: {
    embeddingType(newVal) {
      this.localEmbeddingType = newVal;
    }
  },
  methods: {
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file && file.type === 'application/pdf') {
        this.selectedFile = file;
      } else {
        this.$emit('error', 'Por favor selecciona un archivo PDF válido');
        event.target.value = '';
      }
    },
    handleUpload() {
      if (this.selectedFile) {
        this.$emit('upload', {
          file: this.selectedFile,
          embeddingType: this.localEmbeddingType
        });
        this.selectedFile = null;
        if (this.$refs.fileInput) {
          this.$refs.fileInput.value = '';
        }
      }
    }
  }
};
</script>

<style scoped>
.upload-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.upload-card {
  max-width: 500px;
  width: 100%;
  padding: 48px 40px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 16px;
  text-align: center;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.upload-icon {
  font-size: 64px;
  margin-bottom: 24px;
}

.upload-card h2 {
  font-size: 24px;
  font-weight: 700;
  color: #e4e6eb;
  margin-bottom: 12px;
}

.upload-card p {
  font-size: 15px;
  color: #9ca3af;
  margin-bottom: 32px;
}

.upload-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.file-input-wrapper {
  position: relative;
  cursor: pointer;
}

.file-input-wrapper input[type="file"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.btn-upload {
  display: block;
  padding: 14px 20px;
  background: #1e2640;
  border: 2px dashed #2a3152;
  border-radius: 8px;
  color: #9ca3af;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-input-wrapper:hover .btn-upload {
  border-color: #4d6cfa;
  color: #e4e6eb;
}

.select-embedding {
  padding: 14px 16px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #e4e6eb;
  font-size: 15px;
  font-family: inherit;
  cursor: pointer;
  outline: none;
  transition: all 0.2s;
}

.select-embedding:focus {
  border-color: #4d6cfa;
}

.btn-submit {
  padding: 14px 20px;
  background: #4d6cfa;
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}

.btn-submit:hover:not(:disabled) {
  background: #5a7bff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(77, 108, 250, 0.4);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Light mode */
:global(#app.light-mode) .upload-card {
  background: #ffffff;
  border-color: #e2e8f0;
}

:global(#app.light-mode) .upload-card h2 {
  color: #1a202c;
}

:global(#app.light-mode) .upload-card p {
  color: #718096;
}

:global(#app.light-mode) .btn-upload {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #718096;
}

:global(#app.light-mode) .select-embedding {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #1a202c;
}

@media (max-width: 768px) {
  .upload-area {
    padding: 16px;
  }

  .upload-card {
    padding: 32px 24px;
  }

  .upload-icon {
    font-size: 48px;
  }

  .upload-card h2 {
    font-size: 20px;
  }

  .upload-card p {
    font-size: 14px;
  }
}
</style>
