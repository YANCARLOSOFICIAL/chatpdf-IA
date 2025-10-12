<template>
  <div id="app" :class="{ 'dark-mode': isDarkMode, 'light-mode': !isDarkMode, 'dragging': isDragging }">
    <!-- Drag Overlay -->
    <DragOverlay :visible="isDragging && !currentDocument" />

    <!-- Mobile Menu Toggle -->
    <button 
      v-if="isMobile" 
      class="mobile-menu-toggle" 
      @click="sidebarOpen = !sidebarOpen"
      :class="{ 'open': sidebarOpen }"
    >
      <span></span>
      <span></span>
      <span></span>
    </button>

    <!-- Sidebar -->
    <aside class="sidebar" :class="{ 'open': sidebarOpen }">
      <!-- Logo -->
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">📄</span>
          <span class="logo-text">ChatPDF AI</span>
        </div>
      </div>

      <!-- Nuevo Chat Button -->
      <button class="new-chat-btn" @click="startNewChat">
        <span class="icon">➕</span>
        <span>Nuevo Chat</span>
      </button>

      <!-- Documentos Recientes -->
      <DocumentList 
        :documents="recentDocuments"
        :active-document-id="currentDocument ? currentDocument.id : null"
        @select="selectDocument"
      />

      <!-- Footer -->
      <div class="sidebar-footer">
        <button class="footer-btn" @click="toggleTheme">
          <span class="icon" v-html="isDarkMode ? '&#9728;&#65039;' : '&#127769;'"></span>
          <span>{{ isDarkMode ? 'Modo Claro' : 'Modo Oscuro' }}</span>
        </button>
        <button class="footer-btn" @click="openSettings">
          <span class="icon">⚙️</span>
          <span>Configuración</span>
        </button>
        <button class="footer-btn" @click="openHelp">
          <span class="icon">❓</span>
          <span>Ayuda</span>
        </button>
      </div>
    </aside>

    <!-- Overlay para cerrar sidebar en móvil -->
    <div 
      v-if="isMobile && sidebarOpen" 
      class="overlay"
      @click="sidebarOpen = false"
    ></div>

    <!-- Main Content -->
    <main class="main-content">
      <!-- Header con info del documento -->
      <header v-if="currentDocument" class="main-header">
        <button class="close-btn" @click="closeDocument">✕</button>
        <div class="doc-info-header">
          <span class="label">DOCUMENTO ACTUAL</span>
          <div class="doc-name-header">
            <span class="icon">📄</span>
            <span class="name">{{ currentDocument.name }}</span>
          </div>
        </div>
        <div class="doc-pages">
          <span class="icon">📑</span>
          <span>{{ currentDocument.pages }} páginas</span>
        </div>
      </header>

      <!-- Chat Area -->
      <div class="chat-container">
        <!-- Sin documento: Mostrar área de upload -->
        <UploadArea
          v-if="!currentDocument"
          v-model:embedding-type="embeddingType"
          :is-uploading="isUploading"
          :upload-progress="uploadProgress"
          @upload="uploadDocument"
          @error="showToastMessage"
        />

        <!-- Con documento: Mostrar chat -->
        <div v-else class="chat-area">
          <!-- Mensajes -->
          <div class="messages-container" ref="messagesContainer">
            <!-- Mensaje de bienvenida -->
            <WelcomeMessage v-if="messages.length === 0" />

            <!-- Mensajes del chat -->
            <div v-else class="messages-list">
              <ChatMessage
                v-for="(msg, index) in messages"
                :key="index"
                :message="msg"
                :is-copied="copiedMessageIndex === index"
                :show-regenerate-btn="index === messages.length - 1"
                @copy="copyMessage(index, $event)"
                @regenerate="regenerateLastMessage"
              />

              <!-- Typing indicator -->
              <div v-if="isTyping" class="message assistant">
                <div class="message-avatar">🤖</div>
                <div class="message-bubble">
                  <TypingIndicator />
                </div>
              </div>
            </div>
          </div>

          <!-- Input Area -->
          <div class="input-area">
            <div class="input-wrapper">
              <input 
                v-model="messageInput"
                type="text"
                placeholder="Haz una pregunta sobre el documento..."
                @keyup.enter="sendMessage"
                :disabled="isSending"
                class="message-input"
              />
              <button 
                class="send-btn"
                @click="sendMessage"
                :disabled="!messageInput.trim() || isSending"
              >
                {{ isSending ? '⏳' : '➤' }}
              </button>
            </div>
            
            <div class="input-footer">
              <button class="btn-change-pdf" @click="changePDF">
                <span class="icon">📁</span>
                <span>Cambiar PDF</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Toast Notification -->
    <ToastNotification
      :visible="toast.show"
      :message="toast.message"
      :type="toast.type"
      @close="toast.show = false"
    />
  </div>
</template>

<script>
import DragOverlay from './components/ui/DragOverlay.vue';
import DocumentList from './components/sidebar/DocumentList.vue';
import UploadArea from './components/chat/UploadArea.vue';
import WelcomeMessage from './components/chat/WelcomeMessage.vue';
import ChatMessage from './components/chat/ChatMessage.vue';
import TypingIndicator from './components/chat/TypingIndicator.vue';
import ToastNotification from './components/ui/ToastNotification.vue';

export default {
  name: 'App',
  components: {
    DragOverlay,
    DocumentList,
    UploadArea,
    WelcomeMessage,
    ChatMessage,
    TypingIndicator,
    ToastNotification
  },
  data() {
    return {
      // UI State
      sidebarOpen: false,
      isMobile: false,
      isDarkMode: true,
      isDragging: false,

      // Document State
      currentDocument: null,
      recentDocuments: [],
      selectedFile: null,
      embeddingType: 'openai',
      isUploading: false,
      uploadProgress: 0,

      // Chat State
      messages: [],
      messageInput: '',
      isSending: false,
      isTyping: false,
      copiedMessageIndex: null,

      // Toast
      toast: {
        show: false,
        message: '',
        type: 'info'
      }
    };
  },

  mounted() {
    this.checkMobile();
    window.addEventListener('resize', this.checkMobile);
    this.loadRecentDocuments();
    this.loadTheme();
    this.setupDragAndDrop();
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.checkMobile);
    this.removeDragAndDrop();
  },

  methods: {
    checkMobile() {
      this.isMobile = window.innerWidth <= 1024;
      if (!this.isMobile) {
        this.sidebarOpen = false;
      }
    },

    // Document Management
    loadRecentDocuments() {
      const saved = localStorage.getItem('chatpdf-documents');
      if (saved) {
        this.recentDocuments = JSON.parse(saved);
      }
    },

    saveRecentDocuments() {
      localStorage.setItem('chatpdf-documents', JSON.stringify(this.recentDocuments));
    },

    handleFileSelect(event) {
      const file = event.target.files[0];
      if (file && file.type === 'application/pdf') {
        this.selectedFile = file;
      } else {
        this.showToastMessage('Por favor selecciona un archivo PDF válido', 'error');
        event.target.value = '';
      }
    },

    // Drag and Drop
    setupDragAndDrop() {
      const app = document.getElementById('app');
      app.addEventListener('dragenter', this.handleDragEnter);
      app.addEventListener('dragover', this.handleDragOver);
      app.addEventListener('dragleave', this.handleDragLeave);
      app.addEventListener('drop', this.handleDrop);
    },

    removeDragAndDrop() {
      const app = document.getElementById('app');
      if (app) {
        app.removeEventListener('dragenter', this.handleDragEnter);
        app.removeEventListener('dragover', this.handleDragOver);
        app.removeEventListener('dragleave', this.handleDragLeave);
        app.removeEventListener('drop', this.handleDrop);
      }
    },

    handleDragEnter(e) {
      e.preventDefault();
      e.stopPropagation();
      if (!this.currentDocument) {
        this.isDragging = true;
      }
    },

    handleDragOver(e) {
      e.preventDefault();
      e.stopPropagation();
    },

    handleDragLeave(e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.target === document.getElementById('app')) {
        this.isDragging = false;
      }
    },

    handleDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      this.isDragging = false;

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        const file = files[0];
        if (file.type === 'application/pdf') {
          const payload = {
            file: file,
            embeddingType: this.embeddingType
          };
          this.uploadDocument(payload);
        } else {
          this.showToastMessage('Por favor arrastra un archivo PDF válido', 'error');
        }
      }
    },

    async uploadDocument(payload) {
      const { file, embeddingType } = payload;
      if (!file) return;

      this.isUploading = true;
      this.uploadProgress = 0;
      this.embeddingType = embeddingType;
      
      const formData = new FormData();
      formData.append('pdf', file);
      formData.append('embedding_type', embeddingType);

      try {
        // Simular progreso
        const progressInterval = setInterval(() => {
          if (this.uploadProgress < 90) {
            this.uploadProgress += 10;
          }
        }, 200);

        const response = await fetch('http://localhost:8000/upload_pdf/', {
          method: 'POST',
          body: formData
        });

        clearInterval(progressInterval);
        this.uploadProgress = 100;

        if (!response.ok) {
          throw new Error('Error al subir el PDF');
        }

        const data = await response.json();
        
        const newDoc = {
          id: data.pdf_id,
          name: file.name,
          pages: 45, // Podrías obtener esto del backend
          date: 'Hoy',
          uploadedAt: new Date().toISOString(),
          embeddingType: embeddingType
        };

        this.currentDocument = newDoc;
        
        // Agregar a documentos recientes
        this.recentDocuments.unshift(newDoc);
        if (this.recentDocuments.length > 10) {
          this.recentDocuments = this.recentDocuments.slice(0, 10);
        }
        this.saveRecentDocuments();

        this.showToastMessage('PDF subido exitosamente', 'success');
        
        setTimeout(() => {
          this.uploadProgress = 0;
        }, 1000);
      } catch (error) {
        console.error('Error:', error);
        this.showToastMessage(error.message || 'Error al subir el PDF', 'error');
        this.uploadProgress = 0;
      } finally {
        this.isUploading = false;
      }
    },

    selectDocument(doc) {
      this.currentDocument = doc;
      this.messages = [];
      this.embeddingType = doc.embeddingType || 'openai';
      if (this.isMobile) {
        this.sidebarOpen = false;
      }
      this.showToastMessage(`Documento "${doc.name}" seleccionado`, 'info');
    },

    closeDocument() {
      this.currentDocument = null;
      this.messages = [];
      this.messageInput = '';
    },

    changePDF() {
      this.currentDocument = null;
      this.messages = [];
      this.messageInput = '';
    },

    startNewChat() {
      this.messages = [];
      this.messageInput = '';
      if (!this.currentDocument) {
        this.showToastMessage('Sube un PDF para comenzar', 'info');
      }
      if (this.isMobile) {
        this.sidebarOpen = false;
      }
    },

    // Chat Methods
    async sendMessage() {
      if (!this.messageInput.trim() || !this.currentDocument) return;

      const userMessage = {
        role: 'user',
        content: this.messageInput,
        timestamp: new Date()
      };

      this.messages.push(userMessage);
      const query = this.messageInput;
      this.messageInput = '';
      this.isSending = true;
      this.isTyping = true;

      this.$nextTick(() => {
        this.scrollToBottom();
      });

      try {
        const formData = new FormData();
        formData.append('query', query);
        formData.append('pdf_id', this.currentDocument.id);
        formData.append('embedding_type', this.embeddingType);

        const response = await fetch('http://localhost:8000/chat/', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error('Error al obtener respuesta');
        }

        const data = await response.json();

        const assistantMessage = {
          role: 'assistant',
          content: data.response,
          timestamp: new Date()
        };

        this.messages.push(assistantMessage);
        
        this.$nextTick(() => {
          this.scrollToBottom();
        });
      } catch (error) {
        console.error('Error:', error);
        this.showToastMessage(error.message || 'Error al enviar el mensaje', 'error');
        // Remover el último mensaje si hubo error
        this.messages.pop();
      } finally {
        this.isSending = false;
        this.isTyping = false;
      }
    },

    scrollToBottom() {
      if (this.$refs.messagesContainer) {
        this.$refs.messagesContainer.scrollTop = this.$refs.messagesContainer.scrollHeight;
      }
    },

    // Utility Methods
    formatTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    },

    showToastMessage(message, type = 'info') {
      this.toast = {
        show: true,
        message,
        type
      };
    },

    // Copy message
    async copyMessage(index, content) {
      try {
        await navigator.clipboard.writeText(content);
        this.copiedMessageIndex = index;
        this.showToastMessage('Mensaje copiado al portapapeles', 'success');
        
        setTimeout(() => {
          this.copiedMessageIndex = null;
        }, 2000);
      } catch (error) {
        this.showToastMessage('Error al copiar el mensaje', 'error');
      }
    },

    // Regenerate last message
    async regenerateLastMessage() {
      if (this.messages.length < 2) return;
      
      // Encontrar el último mensaje del usuario
      let lastUserMessageIndex = -1;
      for (let i = this.messages.length - 1; i >= 0; i--) {
        if (this.messages[i].role === 'user') {
          lastUserMessageIndex = i;
          break;
        }
      }
      
      if (lastUserMessageIndex === -1) return;
      
      const lastUserMessage = this.messages[lastUserMessageIndex];
      
      // Remover mensajes desde el último mensaje de usuario
      this.messages = this.messages.slice(0, lastUserMessageIndex);
      
      // Reenviar el mensaje
      this.messageInput = lastUserMessage.content;
      await this.sendMessage();
    },

    // Theme
    toggleTheme() {
      this.isDarkMode = !this.isDarkMode;
      this.saveTheme();
    },

    loadTheme() {
      const saved = localStorage.getItem('chatpdf-theme');
      if (saved) {
        this.isDarkMode = saved === 'dark';
      }
    },

    saveTheme() {
      localStorage.setItem('chatpdf-theme', this.isDarkMode ? 'dark' : 'light');
    },

    openSettings() {
      this.showToastMessage('Configuración - Próximamente', 'info');
    },

    openHelp() {
      this.showToastMessage('Ayuda - Próximamente', 'info');
    }
  }
};
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  width: 100vw;
  height: 100vh;
  display: flex;
  background: #0a0e27;
  color: #e4e6eb;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  overflow: hidden;
  position: relative;
  transition: background 0.3s ease;
}

/* ==================== THEME MODES ==================== */
#app.light-mode {
  background: #f5f7fa;
  color: #1a202c;
}

#app.light-mode .sidebar {
  background: #ffffff;
  border-right-color: #e2e8f0;
}

#app.light-mode .sidebar-header {
  border-bottom-color: #e2e8f0;
}

#app.light-mode .logo-text {
  color: #1a202c;
}

#app.light-mode .section-title {
  color: #718096;
}

#app.light-mode .doc-item {
  color: #1a202c;
}

#app.light-mode .doc-item:hover {
  background: #f7fafc;
}

#app.light-mode .doc-item.active {
  background: #edf2f7;
}

#app.light-mode .doc-name {
  color: #1a202c;
}

#app.light-mode .doc-date {
  color: #718096;
}

#app.light-mode .footer-btn {
  color: #4a5568;
}

#app.light-mode .footer-btn:hover {
  background: #f7fafc;
  color: #1a202c;
}

#app.light-mode .sidebar-footer {
  border-top-color: #e2e8f0;
}

#app.light-mode .main-header {
  background: #ffffff;
  border-bottom-color: #e2e8f0;
}

#app.light-mode .close-btn {
  border-color: #e2e8f0;
  color: #718096;
}

#app.light-mode .close-btn:hover {
  background: #f7fafc;
  color: #1a202c;
}

#app.light-mode .doc-info-header .label {
  color: #718096;
}

#app.light-mode .doc-name-header .name {
  color: #1a202c;
}

#app.light-mode .doc-pages {
  background: #f7fafc;
  color: #4a5568;
}

#app.light-mode .upload-card {
  background: #ffffff;
  border-color: #e2e8f0;
}

#app.light-mode .upload-card h2 {
  color: #1a202c;
}

#app.light-mode .upload-card p {
  color: #718096;
}

#app.light-mode .btn-upload {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #718096;
}

#app.light-mode .select-embedding {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #1a202c;
}

#app.light-mode .welcome-card {
  background: #ffffff;
  border-color: #e2e8f0;
}

#app.light-mode .welcome-text {
  color: #4a5568;
}

#app.light-mode .message-avatar {
  background: #f7fafc;
}

#app.light-mode .message-text {
  background: #ffffff;
  border-color: #e2e8f0;
  color: #1a202c;
}

#app.light-mode .message.user .message-text {
  background: #4d6cfa;
  color: white;
}

#app.light-mode .message-time {
  color: #718096;
}

#app.light-mode .typing-indicator {
  background: #ffffff;
  border-color: #e2e8f0;
}

#app.light-mode .input-area {
  background: #ffffff;
  border-top-color: #e2e8f0;
}

#app.light-mode .input-wrapper {
  background: #f7fafc;
  border-color: #e2e8f0;
}

#app.light-mode .message-input {
  color: #1a202c;
}

#app.light-mode .message-input::placeholder {
  color: #a0aec0;
}

#app.light-mode .btn-change-pdf {
  border-color: #e2e8f0;
  color: #4a5568;
}

#app.light-mode .btn-change-pdf:hover {
  background: #f7fafc;
  color: #1a202c;
}

#app.light-mode .toast {
  background: #ffffff;
  border-color: #e2e8f0;
}

#app.light-mode .toast-message {
  color: #1a202c;
}

/* ==================== DRAG OVERLAY ==================== */
.drag-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(77, 108, 250, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  animation: fadeIn 0.2s ease-out;
}

.drag-content {
  text-align: center;
  padding: 48px;
  background: rgba(255, 255, 255, 0.1);
  border: 3px dashed rgba(255, 255, 255, 0.5);
  border-radius: 24px;
  backdrop-filter: blur(20px);
}

.drag-icon {
  font-size: 96px;
  margin-bottom: 24px;
  animation: bounce 0.6s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.drag-content h2 {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin-bottom: 12px;
}

.drag-content p {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
}

/* ==================== SIDEBAR ==================== */
.sidebar {
  width: 280px;
  background: #151934;
  border-right: 1px solid #1e2640;
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;
  z-index: 100;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #1e2640;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #e4e6eb;
  letter-spacing: -0.5px;
}

/* New Chat Button */
.new-chat-btn {
  margin: 20px;
  padding: 14px 20px;
  background: #4d6cfa;
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(77, 108, 250, 0.3);
}

.new-chat-btn:hover {
  background: #5a7bff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(77, 108, 250, 0.4);
}

.new-chat-btn .icon {
  font-size: 18px;
}

/* Recent Documents */
.recent-docs {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  letter-spacing: 0.5px;
  padding: 16px 12px 12px;
}

.docs-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.doc-item:hover {
  background: #1e2640;
}

.doc-item.active {
  background: #1e2640;
  border-left: 3px solid #4d6cfa;
}

.doc-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-name {
  font-size: 14px;
  font-weight: 500;
  color: #e4e6eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-date {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

.empty-docs {
  padding: 32px 16px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #1e2640;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.footer-btn {
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #9ca3af;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
}

.footer-btn:hover {
  background: #1e2640;
  color: #e4e6eb;
}

.footer-btn .icon {
  font-size: 18px;
}

/* ==================== MAIN CONTENT ==================== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Main Header */
.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: #151934;
  border-bottom: 1px solid #1e2640;
  min-height: 72px;
  gap: 20px;
}

.close-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #9ca3af;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #e4e6eb;
}

.doc-info-header {
  flex: 1;
  min-width: 0;
}

.doc-info-header .label {
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}

.doc-name-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-name-header .icon {
  font-size: 18px;
}

.doc-name-header .name {
  font-size: 15px;
  font-weight: 600;
  color: #e4e6eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-pages {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1e2640;
  border-radius: 6px;
  font-size: 14px;
  color: #9ca3af;
  flex-shrink: 0;
}

/* ==================== CHAT CONTAINER ==================== */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Upload Section */
.upload-section {
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
}

.btn-submit:hover:not(:disabled) {
  background: #5a7bff;
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Progress Bar */
.progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #1e2640;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4d6cfa, #5a7bff);
  border-radius: 4px;
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-text {
  font-size: 13px;
  font-weight: 600;
  color: #4d6cfa;
  min-width: 45px;
  text-align: right;
}

/* ==================== CHAT AREA ==================== */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

/* Welcome Card */
.welcome-card {
  max-width: 800px;
  margin: 0 auto;
  padding: 48px 32px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 16px;
  text-align: center;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 24px;
  animation: wave 2s ease-in-out infinite;
}

@keyframes wave {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(20deg); }
  75% { transform: rotate(-20deg); }
}

.welcome-text {
  font-size: 20px;
  font-weight: 500;
  color: #9ca3af;
  line-height: 1.6;
}

/* Messages List */
.messages-list {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Smooth Entry Animation for Messages */
.message {
  animation: messageSlideIn 0.3s ease-out;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Messages List (continued) */
.messages-list {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1e2640;
  border-radius: 50%;
  font-size: 20px;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #4d6cfa;
}

.message-bubble {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-text {
  padding: 12px 16px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  color: #e4e6eb;
  font-size: 15px;
  line-height: 1.5;
}

.message.user .message-text {
  background: #4d6cfa;
  border-color: #5a7bff;
  color: white;
}

.message-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.message.user .message-footer {
  flex-direction: row-reverse;
}

.message-time {
  font-size: 12px;
  color: #6b7280;
  padding: 0 4px;
}

.copy-btn {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  opacity: 0;
}

.message:hover .copy-btn {
  opacity: 1;
}

.copy-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
  transform: scale(1.05);
}

.copy-btn:active {
  transform: scale(0.95);
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 12px 16px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

/* ==================== INPUT AREA ==================== */
.input-area {
  padding: 24px 32px;
  background: #151934;
  border-top: 1px solid #1e2640;
}

.input-wrapper {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  gap: 12px;
  align-items: center;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 12px;
  padding: 6px;
  transition: all 0.2s;
}

.input-wrapper:focus-within {
  border-color: #4d6cfa;
  box-shadow: 0 0 0 3px rgba(77, 108, 250, 0.1);
}

.message-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e4e6eb;
  font-size: 15px;
  padding: 12px 16px;
  font-family: inherit;
}

.message-input::placeholder {
  color: #6b7280;
}

.send-btn {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #4d6cfa;
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #5a7bff;
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-footer {
  max-width: 1000px;
  margin: 16px auto 0;
  display: flex;
  justify-content: center;
}

.btn-change-pdf {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #9ca3af;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-change-pdf:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #e4e6eb;
}

.btn-change-pdf .icon {
  font-size: 16px;
}

/* ==================== TOAST ==================== */
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 9999;
}

.toast.success {
  border-color: #10b981;
}

.toast.error {
  border-color: #ef4444;
}

.toast.info {
  border-color: #3b82f6;
}

.toast-icon {
  font-size: 24px;
}

.toast-message {
  font-size: 14px;
  color: #e4e6eb;
  font-weight: 500;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  transform: translateX(400px);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(400px);
  opacity: 0;
}

/* ==================== MOBILE ==================== */
.mobile-menu-toggle {
  display: none;
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: 1001;
  width: 44px;
  height: 44px;
  background: #151934;
  border: 1px solid #2a3152;
  border-radius: 8px;
  cursor: pointer;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  transition: all 0.3s;
}

.mobile-menu-toggle span {
  width: 20px;
  height: 2px;
  background: #e4e6eb;
  border-radius: 2px;
  transition: all 0.3s;
}

.mobile-menu-toggle.open span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}

.mobile-menu-toggle.open span:nth-child(2) {
  opacity: 0;
}

.mobile-menu-toggle.open span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

.overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 99;
}

@media (max-width: 1024px) {
  .mobile-menu-toggle {
    display: flex;
  }

  .overlay {
    display: block;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100%;
    z-index: 1000;
    transform: translateX(-100%);
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.5);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .main-header {
    padding-left: 72px;
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 85%;
    max-width: 300px;
  }

  .main-header {
    padding: 12px 16px 12px 64px;
    min-height: 64px;
  }

  .doc-pages {
    display: none;
  }

  .messages-container {
    padding: 20px 16px;
  }

  .input-area {
    padding: 16px;
  }

  .upload-card {
    padding: 32px 24px;
  }

  .welcome-card {
    padding: 32px 24px;
  }

  .welcome-icon {
    font-size: 48px;
  }

  .welcome-text {
    font-size: 18px;
  }
}

/* ==================== SCROLLBAR ==================== */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #0a0e27;
}

::-webkit-scrollbar-thumb {
  background: #2a3152;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #3a4162;
}

/* ==================== RIPPLE EFFECT ==================== */
.new-chat-btn,
.btn-submit,
.send-btn {
  position: relative;
  overflow: hidden;
}

.new-chat-btn::after,
.btn-submit::after,
.send-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.new-chat-btn:active::after,
.btn-submit:active::after,
.send-btn:active::after {
  width: 300px;
  height: 300px;
}

/* ==================== SMOOTH TRANSITIONS ==================== */
* {
  transition-property: background-color, border-color, color, opacity;
  transition-duration: 0.2s;
  transition-timing-function: ease;
}

button,
input,
select,
.doc-item,
.message-avatar,
.copy-btn {
  transition: all 0.2s ease;
}

/* ==================== LIGHT MODE SCROLLBAR ==================== */
#app.light-mode ::-webkit-scrollbar-track {
  background: #f5f7fa;
}

#app.light-mode ::-webkit-scrollbar-thumb {
  background: #cbd5e0;
}

#app.light-mode ::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}

/* ==================== ACCESSIBILITY ==================== */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Focus visible for accessibility */
button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 2px solid #4d6cfa;
  outline-offset: 2px;
}
</style>
