<template>
  <div id="app" :class="{ 'dark-mode': isDarkMode }">
    <!-- Background Animated Orbs -->
    <div class="animated-background">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

    <!-- Mobile Menu Toggle -->
    <button class="mobile-menu-toggle" @click="toggleSidebar" :class="{ 'menu-open': !sidebarCollapsed }">
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
      <span class="hamburger-line"></span>
    </button>

    <!-- Main Container -->
    <div class="app-container">
      <!-- Sidebar Navigation -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-header">
          <div class="logo" @click="toggleSidebar">
            <span class="logo-icon">📄</span>
            <span v-if="!sidebarCollapsed" class="logo-text">ChatPDF AI</span>
          </div>
        </div>

        <nav class="sidebar-nav">
          <button class="nav-item" :class="{ active: activeTab === 'chat' }" @click="changeTab('chat')" :title="sidebarCollapsed ? 'Chat' : ''">
            <span class="nav-icon">💬</span>
            <span v-if="!sidebarCollapsed" class="nav-label">Chat</span>
          </button>
          <button class="nav-item" :class="{ active: activeTab === 'documentos' }" @click="changeTab('documentos')" :title="sidebarCollapsed ? 'Documentos' : ''">
            <span class="nav-icon">📄</span>
            <span v-if="!sidebarCollapsed" class="nav-label">Documentos</span>
          </button>
          <button class="nav-item" :class="{ active: activeTab === 'sistema' }" @click="changeTab('sistema')" :title="sidebarCollapsed ? 'Sistema' : ''">
            <span class="nav-icon">⚙️</span>
            <span v-if="!sidebarCollapsed" class="nav-label">Sistema</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <button class="theme-toggle-btn" @click="toggleTheme" :title="isDarkMode ? 'Modo Claro' : 'Modo Oscuro'">
            <span class="theme-icon">{{ isDarkMode ? '' : '' }}</span>
            <span v-if="!sidebarCollapsed" class="theme-label">{{ isDarkMode ? 'Claro' : 'Oscuro' }}</span>
          </button>
        </div>
      </aside>

      <!-- Main Content Area -->
      <main class="main-content">
        <div class="content-wrapper">
          <!-- Chat Panel -->
          <div v-show="activeTab === 'chat'" class="panel chat-panel">
            <div class="panel-header">
              <h1 class="panel-title"> Chat con PDF</h1>
            </div>

            <div class="chat-container">
              <file-uploader
                :is-uploading="isUploading"
                :embedding-type="embeddingType"
                :uploaded-file="uploadedFile"
                @upload="handleUpload"
              />

              <!-- Indicador del modelo activo -->
              <div v-if="uploadedFile" class="model-indicator">
                <span class="indicator-icon">⚡</span>
                <span class="indicator-text">
                  Usando: <strong>{{ embeddingType === 'openai' ? 'OpenAI' : 'Ollama' }}</strong>
                </span>
              </div>

              <chat-history
                :messages="messages"
                :is-typing="isTyping"
              />

              <message-input
                v-model:message="currentMessage"
                :disabled="!pdfId"
                :is-sending="isSending"
                :pdf-uploaded="!!pdfId"
                @send="sendMessage"
              />

              <chat-stats
                :messages="messages"
                :embedding-type="embeddingType"
                :pdf-name="uploadedFile?.name"
              />
            </div>
          </div>

          <!-- Documents Panel -->
          <div v-show="activeTab === 'documentos'" class="panel documents-panel-container">
            <documents-panel
              :documents="documentsList"
              :active-document-id="pdfId ? String(pdfId) : null"
              @upload="handleDocumentUpload"
              @select="handleDocumentSelect"
              @delete="handleDocumentDelete"
              @view="handleDocumentView"
            />
          </div>

          <!-- System Panel -->
          <div v-show="activeTab === 'sistema'" class="panel system-panel-container">
            <system-panel
              :llm-provider="systemConfig.llmProvider"
              :llm-model="systemConfig.llmModel"
              :embedding-model="systemConfig.embeddingModel"
              :embedding-dimension="systemConfig.embeddingDimension"
              :mrl-compression="systemConfig.mrlCompression"
              :vector-count="systemConfig.vectorCount"
              :collection-name="systemConfig.collectionName"
              :metric="systemConfig.metric"
              :top-k="systemConfig.topK"
              :threshold="systemConfig.threshold"
              :temperature="systemConfig.temperature"
              @save-llm-config="handleSaveLlmConfig"
            />
          </div>
        </div>
      </main>
    </div>

    <!-- Toast Notifications -->
    <toast-notification
      :show="showToast"
      :message="toastMessage"
      :type="toastType"
    />

    <!-- Settings Panel (Floating) -->
    <settings-panel
      :is-open="showSettings"
      :temperature="temperature"
      :max-tokens="maxTokens"
      :top-k="topK"
      :auto-scroll="autoScroll"
      :show-timestamps="showTimestamps"
      :sound-enabled="soundEnabled"
      @toggle="showSettings = !showSettings"
      @reset="resetSettings"
      @update:temperature="temperature = $event"
      @update:maxTokens="maxTokens = $event"
      @update:topK="topK = $event"
      @update:autoScroll="autoScroll = $event"
      @update:showTimestamps="showTimestamps = $event"
      @update:soundEnabled="soundEnabled = $event"
    />
  </div>
</template>

<script>
import FileUploader from './components/FileUploader.vue';
import ChatHistory from './components/ChatHistory.vue';
import MessageInput from './components/MessageInput.vue';
import ChatStats from './components/ChatStats.vue';
import ToastNotification from './components/ToastNotification.vue';
import SettingsPanel from './components/SettingsPanel.vue';
import DocumentsPanel from './components/DocumentsPanel.vue';
import SystemPanel from './components/SystemPanel.vue';

export default {
  name: 'App',
  components: {
    FileUploader,
    ChatHistory,
    MessageInput,
    ChatStats,
    ToastNotification,
    SettingsPanel,
    DocumentsPanel,
    SystemPanel
  },
  data() {
    return {
      // UI State
      activeTab: 'chat',
      sidebarCollapsed: false,
      isDarkMode: false,
      showSettings: false,
      showToast: false,
      toastMessage: '',
      toastType: 'success',

      // Chat State
      messages: [],
      currentMessage: '',
      isTyping: false,
      isSending: false,

      // Upload State
      isUploading: false,
      uploadedFile: null,
      pdfId: null,
      embeddingType: 'openai',

      // Settings
      temperature: 0.7,
      maxTokens: 1000,
      topK: 3,
      autoScroll: true,
      showTimestamps: true,
      soundEnabled: false,

      // Documents
      documentsList: [],

      // System Config
      systemConfig: {
        llmProvider: 'ollama',
        llmModel: 'qwen3:4b',
        embeddingModel: 'embeddinggemma',
        embeddingDimension: 768,
        mrlCompression: 33.3,
        vectorCount: 0,
        collectionName: 'pdf_vectors',
        metric: 'cosine',
        topK: 5,
        threshold: 30,
        temperature: 0.7
      }
    };
  },
  mounted() {
    this.loadSettings();
    this.loadDocuments();
  },
  methods: {
    // UI Handlers
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed;
    },

    changeTab(tab) {
      this.activeTab = tab;
      // Cerrar sidebar en móviles al cambiar de tab
      if (window.innerWidth <= 1024) {
        this.sidebarCollapsed = true;
      }
    },

    // Upload Handlers
    async handleUpload({ file, embeddingType }) {
      this.isUploading = true;
      const formData = new FormData();
      formData.append('pdf', file);
      formData.append('embedding_type', embeddingType);

      try {
        const response = await fetch('http://localhost:8000/upload_pdf/', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) throw new Error('Error al subir PDF');

        const data = await response.json();
        this.pdfId = data.pdf_id;
        this.embeddingType = embeddingType; // Sincronizar el tipo de embedding usado
        this.uploadedFile = {
          id: data.pdf_id,
          name: file.name,
          embeddingType: embeddingType,
          uploadedAt: new Date()
        };

        this.showToastMessage('PDF subido exitosamente', 'success');
        this.addDocumentToList(this.uploadedFile);
      } catch (error) {
        this.showToastMessage(error.message, 'error');
      } finally {
        this.isUploading = false;
      }
    },

    async sendMessage(message) {
      if (!this.pdfId || !message.trim()) return;

      this.isSending = true;
      this.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date()
      });

      this.isTyping = true;

      try {
        const formData = new FormData();
        formData.append('query', message);
        formData.append('pdf_id', this.pdfId);
        formData.append('embedding_type', this.embeddingType);

        const response = await fetch('http://localhost:8000/chat/', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMsg = errorData.detail || 'Error al obtener respuesta del servidor';
          throw new Error(errorMsg);
        }

        const data = await response.json();
        this.messages.push({
          role: 'assistant',
          content: data.response,
          timestamp: new Date()
        });
      } catch (error) {
        console.error('Error en chat:', error);
        this.showToastMessage(error.message || 'Error al enviar mensaje', 'error');
        // Remover el último mensaje de usuario si hubo error
        if (this.messages.length > 0 && this.messages[this.messages.length - 1].role === 'user') {
          this.messages.pop();
        }
      } finally {
        this.isSending = false;
        this.isTyping = false;
        this.currentMessage = '';
      }
    },

    // Documents Handlers
    handleDocumentUpload(file) {
      this.activeTab = 'chat';
      this.handleUpload({ file, embeddingType: this.embeddingType });
    },

    handleDocumentSelect(doc) {
      this.pdfId = doc.id;
      this.uploadedFile = doc;
      this.embeddingType = doc.embeddingType;
      this.activeTab = 'chat';
      this.showToastMessage(`Documento "${doc.name}" seleccionado`, 'info');
    },

    handleDocumentDelete(id) {
      this.documentsList = this.documentsList.filter(d => d.id !== id);
      if (this.pdfId === id) {
        this.pdfId = null;
        this.uploadedFile = null;
      }
      this.saveDocuments();
      this.showToastMessage('Documento eliminado', 'info');
    },

    handleDocumentView(doc) {
      this.showToastMessage(`Visualizando: ${doc.name}`, 'info');
    },

    addDocumentToList(doc) {
      if (!this.documentsList.find(d => d.id === doc.id)) {
        this.documentsList.push(doc);
        this.saveDocuments();
      }
    },

    // System Handlers
    handleSaveLlmConfig(config) {
      this.systemConfig.llmProvider = config.provider;
      this.systemConfig.llmModel = config.model;
      this.showToastMessage('Configuración LLM guardada', 'success');
    },

    // Settings
    loadSettings() {
      const saved = localStorage.getItem('chatpdf-settings');
      if (saved) {
        const settings = JSON.parse(saved);
        Object.assign(this, settings);
      }
    },

    saveSettings() {
      localStorage.setItem('chatpdf-settings', JSON.stringify({
        temperature: this.temperature,
        maxTokens: this.maxTokens,
        topK: this.topK,
        autoScroll: this.autoScroll,
        showTimestamps: this.showTimestamps,
        soundEnabled: this.soundEnabled,
        isDarkMode: this.isDarkMode
      }));
    },

    resetSettings() {
      this.temperature = 0.7;
      this.maxTokens = 1000;
      this.topK = 3;
      this.autoScroll = true;
      this.showTimestamps = true;
      this.soundEnabled = false;
      this.saveSettings();
      this.showToastMessage('Configuración restaurada', 'info');
    },

    // Documents Storage
    loadDocuments() {
      const saved = localStorage.getItem('chatpdf-documents');
      if (saved) {
        this.documentsList = JSON.parse(saved);
      }
    },

    saveDocuments() {
      localStorage.setItem('chatpdf-documents', JSON.stringify(this.documentsList));
    },

    // Theme
    toggleTheme() {
      this.isDarkMode = !this.isDarkMode;
      this.saveSettings();
    },

    // Toast
    showToastMessage(message, type = 'success') {
      this.toastMessage = message;
      this.toastType = type;
      this.showToast = true;
      setTimeout(() => {
        this.showToast = false;
      }, 3000);
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
  overflow: hidden;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  position: relative;
}

/* Animated Background */
.animated-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  z-index: 0;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  top: -10%;
  left: -10%;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  top: 50%;
  right: -5%;
  animation-delay: 7s;
}

.orb-3 {
  width: 450px;
  height: 450px;
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  bottom: -10%;
  left: 30%;
  animation-delay: 14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

/* Mobile Menu Toggle */
.mobile-menu-toggle {
  display: none;
  position: fixed;
  top: 16px;
  left: 16px;
  z-index: 1001;
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  cursor: pointer;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
}

.mobile-menu-toggle:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: scale(1.05);
}

.hamburger-line {
  width: 24px;
  height: 2px;
  background: #fff;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.mobile-menu-toggle.menu-open .hamburger-line:nth-child(1) {
  transform: translateY(8px) rotate(45deg);
}

.mobile-menu-toggle.menu-open .hamburger-line:nth-child(2) {
  opacity: 0;
}

.mobile-menu-toggle.menu-open .hamburger-line:nth-child(3) {
  transform: translateY(-8px) rotate(-45deg);
}

/* App Container */
.app-container {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  height: 100%;
}

/* Sidebar */
.sidebar {
  width: 250px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar.collapsed {
  width: 80px;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: transform 0.2s;
}

.logo:hover {
  transform: scale(1.05);
}

.logo-icon {
  font-size: 32px;
  line-height: 1;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: 20px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: transparent;
  border: none;
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  white-space: nowrap;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
  color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.nav-icon {
  font-size: 24px;
  line-height: 1;
}

.sidebar-footer {
  padding: 20px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.theme-toggle-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.theme-toggle-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.theme-icon {
  font-size: 20px;
}

/* Main Content */
.main-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.content-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

.panel {
  max-width: 1400px;
  margin: 0 auto;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.panel-header {
  margin-bottom: 32px;
}

.panel-title {
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.chat-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Model Indicator */
.model-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(102, 126, 234, 0.15);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 8px;
  backdrop-filter: blur(10px);
  animation: fadeIn 0.4s;
}

.indicator-icon {
  font-size: 20px;
}

.indicator-text {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.indicator-text strong {
  color: #667eea;
  font-weight: 700;
  text-transform: uppercase;
}

/* Dark Mode */
.dark-mode {
  background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
}

.dark-mode .sidebar {
  background: rgba(0, 0, 0, 0.3);
}

.dark-mode .nav-item.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.3), rgba(118, 75, 162, 0.3));
}

/* Responsive Design */
@media (max-width: 1400px) {
  .app-container {
    font-size: 14px;
  }
  
  .sidebar {
    width: 200px;
  }
  
  .sidebar.collapsed {
    width: 70px;
  }
}

@media (max-width: 1024px) {
  /* Tablet - ocultar sidebar por defecto */
  .mobile-menu-toggle {
    display: flex;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100%;
    z-index: 1000;
    width: 280px;
    transform: translateX(-100%);
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3);
  }

  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }
  
  .sidebar.collapsed {
    transform: translateX(-100%);
  }

  /* Overlay cuando sidebar está abierto */
  .sidebar:not(.collapsed)::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: -1;
  }

  .main-content {
    margin-left: 0 !important;
    width: 100%;
  }

  .content-wrapper {
    padding: 20px;
    padding-top: 80px; /* espacio para botón hamburger */
    max-width: 100%;
  }

  .tab-panel {
    padding: 16px;
  }

  .panel-title {
    font-size: 24px;
  }
}

@media (max-width: 768px) {
  /* Mobile - diseño optimizado */
  #app {
    font-size: 14px;
  }

  .mobile-menu-toggle {
    top: 12px;
    left: 12px;
    width: 44px;
    height: 44px;
  }

  .hamburger-line {
    width: 20px;
  }

  .app-container {
    flex-direction: column;
  }

  .sidebar {
    width: 85%;
    max-width: 320px;
    height: 100%;
    position: fixed;
    left: 0;
    top: 0;
    bottom: auto;
    transform: translateX(-100%);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
    border-top: none;
    z-index: 1000;
  }

  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }

  .sidebar-header {
    padding: 20px 16px;
  }

  .logo {
    cursor: pointer;
  }

  .logo-icon {
    font-size: 28px;
  }

  .logo-text {
    font-size: 18px;
  }

  .sidebar-nav {
    flex: 1;
    overflow-y: auto;
  }

  .nav-item {
    padding: 14px 16px;
    margin: 4px 12px;
    font-size: 15px;
  }

  .nav-icon {
    font-size: 22px;
  }

  .nav-label {
    font-size: 14px;
  }

  .main-content {
    width: 100%;
    margin-left: 0;
  }

  .content-wrapper {
    padding: 8px;
    padding-top: 68px; /* espacio para botón hamburger */
  }

  .panel-header {
    margin-bottom: 16px;
  }

  .panel-title {
    font-size: 22px;
  }

  .tab-navigation {
    width: 100%;
    padding: 2px;
  }

  .tab-button {
    padding: 12px 16px;
    font-size: 14px;
  }

  .tab-icon {
    font-size: 18px;
  }

  .tab-panel {
    padding: 12px;
    max-height: calc(100vh - 180px);
    overflow-y: auto;
  }

  /* Ajustar componentes específicos del chat */
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 120px);
  }

  .panel-content {
    flex: 1;
    overflow-y: auto;
  }

  /* File Uploader */
  .file-uploader {
    margin-bottom: 1rem;
  }

  .upload-form {
    flex-direction: column;
    gap: 0.8rem;
  }

  .file-label {
    width: 100%;
    justify-content: center;
  }

  .file-name {
    max-width: 100%;
    text-align: center;
  }

  .select-input {
    width: 100%;
  }

  .upload-btn {
    width: 100%;
  }

  /* Chat Messages */
  .chat-history {
    max-height: 300px;
  }

  .chat-msg {
    padding: 0.6rem 0.9rem;
    font-size: 0.95rem;
  }

  /* Message Input */
  .message-form {
    gap: 0.8rem;
  }

  .message-input {
    font-size: 15px;
    padding: 12px;
  }

  .send-btn {
    width: 100%;
    padding: 12px;
  }

  /* Stats */
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  /* Documents Panel */
  .documents-grid {
    grid-template-columns: 1fr;
  }

  .document-card {
    padding: 16px;
  }

  /* System Panel */
  .system-grid {
    grid-template-columns: 1fr;
  }

  .system-card {
    padding: 16px;
  }

  /* Ocultar elementos menos importantes en móvil */
  .sidebar-footer {
    padding: 12px;
  }

  /* Orbs más pequeños en móvil */
  .orb-1, .orb-2, .orb-3 {
    width: 250px !important;
    height: 250px !important;
    filter: blur(60px);
    opacity: 0.2;
  }
}

@media (max-width: 480px) {
  /* Mobile pequeño - optimizaciones adicionales */
  #app {
    font-size: 13px;
  }

  .sidebar-header {
    padding: 12px;
  }

  .logo-icon {
    font-size: 24px;
  }

  .logo-text {
    font-size: 16px;
  }

  .content-wrapper {
    padding: 8px;
  }

  .tab-panel {
    padding: 8px;
  }

  .tab-button {
    padding: 10px 12px;
    font-size: 13px;
  }

  .tab-icon {
    font-size: 16px;
  }

  /* Reducir tamaños de card */
  .file-uploader,
  .chat-history-container,
  .message-input-container {
    margin-bottom: 1rem;
  }

  .section-title {
    font-size: 1.1rem;
  }

  .chat-msg {
    padding: 0.6rem 0.8rem;
    font-size: 0.9rem;
  }

  /* Botones más grandes para touch */
  button {
    min-height: 44px;
    min-width: 44px;
  }

  .upload-btn,
  .send-btn {
    padding: 12px 16px;
    font-size: 14px;
  }
}

/* Landscape mode en móviles */
@media (max-width: 768px) and (orientation: landscape) {
  .tab-panel {
    max-height: calc(100vh - 120px);
  }

  .sidebar {
    height: 60px;
  }

  .nav-list {
    flex-direction: row;
  }
}

/* Mejoras para pantallas grandes */
@media (min-width: 1920px) {
  .content-wrapper {
    max-width: 1600px;
    margin: 0 auto;
  }

  .tab-panel {
    font-size: 16px;
  }
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
