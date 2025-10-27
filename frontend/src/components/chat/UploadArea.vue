<template>
  <div class="upload-area">
    <div class="upload-card">
      <div class="upload-icon">📄</div>
      <h2>Sube tu documento PDF</h2>
      <p>Arrastra y suelta archivos o haz clic para seleccionar</p>
      <p class="system-info">El sistema usará el modelo configurado por el administrador</p>
      
      <div class="upload-controls">
        <!-- Subir archivo individual -->
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

        <!-- Subir carpeta completa -->
        <label class="file-input-wrapper">
          <input 
            type="file" 
            webkitdirectory
            directory
            multiple
            @change="handleFolderSelect"
            ref="folderInput"
          />
          <span class="btn-upload folder-btn">
            {{ selectedFolderInfo || '📂 Seleccionar Carpeta' }}
          </span>
        </label>

        <button 
          class="btn-submit"
          @click="handleUpload"
          :disabled="(!selectedFile && !selectedFolder) || isUploading"
        >
          {{ isUploading ? '⏳ Subiendo...' : '↑ Subir Documento(s)' }}
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
    isUploading: {
      type: Boolean,
      default: false
    },
    uploadProgress: {
      type: Number,
      default: 0
    }
  },
  emits: ['upload', 'upload-folder'],
  data() {
    return {
      selectedFile: null,
      selectedFolder: null,
      selectedFolderName: ''
    };
  },
  computed: {
    selectedFileName() {
      return this.selectedFile ? this.selectedFile.name : '';
    },
    selectedFolderInfo() {
      if (this.selectedFolder && this.selectedFolder.length > 0) {
        const pdfCount = this.selectedFolder.filter(f => f.name.toLowerCase().endsWith('.pdf')).length;
        return `📂 ${this.selectedFolderName} (${pdfCount} PDFs)`;
      }
      return '';
    }
  },
  methods: {
    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file && file.type === 'application/pdf') {
        this.selectedFile = file;
        this.selectedFolder = null;
        this.selectedFolderName = '';
        // Clear folder input
        if (this.$refs.folderInput) {
          this.$refs.folderInput.value = '';
        }
      } else {
        this.$emit('error', 'Por favor selecciona un archivo PDF válido');
        event.target.value = '';
      }
    },
    handleFolderSelect(event) {
      const files = Array.from(event.target.files || []);
      console.log('handleFolderSelect: Total files detected:', files.length);
      console.log('handleFolderSelect: Files:', files.map(f => ({ name: f.name, type: f.type, size: f.size, path: f.webkitRelativePath })));
      
      const pdfFiles = files.filter(f => {
        const isPdf = f.name.toLowerCase().endsWith('.pdf') || f.type === 'application/pdf';
        console.log(`File ${f.name}: isPdf=${isPdf}, type=${f.type}`);
        return isPdf;
      });
      
      console.log('handleFolderSelect: PDF files filtered:', pdfFiles.length);
      
      if (pdfFiles.length === 0) {
        this.$emit('error', 'La carpeta no contiene archivos PDF');
        event.target.value = '';
        return;
      }

      // Extract folder name from the first file's path
      if (files.length > 0 && files[0].webkitRelativePath) {
        const pathParts = files[0].webkitRelativePath.split('/');
        this.selectedFolderName = pathParts[0] || 'Carpeta';
      } else {
        this.selectedFolderName = 'Carpeta';
      }

      this.selectedFolder = pdfFiles;
      this.selectedFile = null;
      // Clear file input
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
      
      console.log(`handleFolderSelect: Selected ${pdfFiles.length} PDFs from folder "${this.selectedFolderName}"`);
    },
    handleUpload() {
      if (this.selectedFile) {
        // Upload single file
        this.$emit('upload', {
          file: this.selectedFile
        });
        this.selectedFile = null;
        if (this.$refs.fileInput) {
          this.$refs.fileInput.value = '';
        }
      } else if (this.selectedFolder && this.selectedFolder.length > 0) {
        // Upload folder
        this.$emit('upload-folder', {
          files: this.selectedFolder,
          folderName: this.selectedFolderName
        });
        this.selectedFolder = null;
        this.selectedFolderName = '';
        if (this.$refs.folderInput) {
          this.$refs.folderInput.value = '';
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

.system-info {
  font-size: 13px;
  color: #60a5fa;
  margin-bottom: 16px;
  font-style: italic;
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

.btn-upload.folder-btn {
  border-color: #2a5252;
  background: #1a2d2d;
}

.file-input-wrapper:hover .btn-upload {
  border-color: #4d6cfa;
  color: #e4e6eb;
}

.file-input-wrapper:hover .btn-upload.folder-btn {
  border-color: #10b981;
  color: #e4e6eb;
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

:global(#app.light-mode) .system-info {
  color: #3b82f6;
}

:global(#app.light-mode) .btn-upload {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #718096;
}

:global(#app.light-mode) .btn-upload.folder-btn {
  background: #f0fdf4;
  border-color: #d1fae5;
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

.system-info {
  font-size: 13px;
  color: #60a5fa;
  margin-bottom: 16px;
  font-style: italic;
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

:global(#app.light-mode) .system-info {
  color: #3b82f6;
}

:global(#app.light-mode) .btn-upload {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #718096;
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
