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

      <!-- Filtro por etiqueta -->
      <div v-if="uniqueTags.length > 0" class="tag-filter" style="padding: 8px 12px;">
        <div style="color:#9ca3af; font-size:12px; margin-bottom:8px;">Filtrar por etiqueta</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="tag-chip" :class="{ active: !activeTag }" @click="setActiveTag(null)">Todas</button>
          <button v-for="t in uniqueTags" :key="t" class="tag-chip" :class="{ active: activeTag === t }" @click="setActiveTag(t)">{{ t }} <span class="tag-count">{{ tagCounts[t] || 0 }}</span></button>
        </div>
      </div>

      <!-- Nuevo Chat Button -->
      <button class="new-chat-btn" @click="startNewChat">
        <span class="icon">➕</span>
        <span>Nuevo Chat</span>
      </button>

      <!-- Documentos Recientes -->
      <!-- Favoritos rápido -->
      <div v-if="favoriteDocuments.length > 0" class="favorites-quick">
        <h4 class="fav-title">Favoritos</h4>
        <div class="fav-list">
          <button v-for="f in favoriteDocuments" :key="f.id" class="fav-item" @click="selectDocument(f)">
            📌 {{ f.name }}
          </button>
        </div>
      </div>
      <!-- Carpetas -->
      <FolderList
        :folders="folders"
        :active-folder-id="activeFolderId"
        :documents="recentDocuments"
        @select="selectFolder"
        @new="createFolder"
        @delete="deleteFolder"
        @drop="({ docId, folderId }) => moveDocumentToFolder(docId, folderId)"
        @select-document="selectDocument"
      />

      <!-- Filtro por carpeta (DocumentList pregunta por activeFolderId) -->
      <div class="folder-filter-controls" v-if="folders.length > 0">
        <button class="filter-btn" :class="{ active: !activeFolderId }" @click="selectFolder(null)">Todas</button>
        <button v-for="f in folders" :key="f.id" class="filter-btn" :class="{ active: activeFolderId === f.id }" @click="selectFolder(f.id)">{{ f.name }}</button>
      </div>

      <!-- Mostrar solo favoritos -->
      <div class="favorites-toggle" style="padding: 8px 12px 12px;">
        <label style="color:#9ca3af; font-size:13px; display:flex; gap:8px; align-items:center;"><input type="checkbox" v-model="showOnlyFavorites" /> Mostrar solo favoritos</label>
      </div>

      <DocumentList 
        :documents="recentDocuments"
        :active-document-id="currentDocument ? currentDocument.id : null"
        :active-folder-id="activeFolderId"
        :active-tag="activeTag"
        :show-favorites="showOnlyFavorites"
        @select="selectDocument"
        @toggle-favorite="toggleFavorite"
        @open-tags="openTagsPanel"
        @remove-tag="removeTagFromDoc"
      />

      <!-- Botón para ver historial de conversaciones -->
      <div v-if="currentDocument" class="history-section">
        <button 
          class="history-btn"
          @click="showConversationsPanel = !showConversationsPanel"
          :class="{ 'active': showConversationsPanel }"
        >
          <span class="icon">📚</span>
          <span>Historial de Conversaciones</span>
          <span class="badge" v-if="conversations.length > 0">{{ conversations.length }}</span>
        </button>
      </div>

      <!-- Conversaciones del documento actual (colapsable) -->
      <ConversationList
        v-if="currentDocument && showConversationsPanel && conversations.length > 0"
        :conversations="conversations"
        :active-conversation-id="currentConversationId"
        @select="selectConversation"
        @new="newConversation"
        @delete="deleteConversation"
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

    <!-- PDF History Component -->
    <PDFHistory
      :isOpen="showPdfHistory"
      :pdfs="recentDocuments"
      :currentPdfId="currentDocument ? currentDocument.id : null"
      @toggle="() => { showPdfHistory = !showPdfHistory }"
      @select="selectDocument"
      @delete="deletePdf"
      @clear-all="clearAllPdfs"
    />

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
        <div class="doc-actions">
          <div class="doc-pages">
            <span class="icon">📑</span>
            <span>{{ currentDocument.pages }} páginas</span>
          </div>
          <ExportButton 
            :messages="messages"
            :document-name="currentDocument.name"
            @export="handleExport"
          />
        </div>
      </header>

      <!-- Chat Area -->
      <div class="chat-container" :class="{ 'two-column': currentDocument }">
        <!-- Sin documento: Mostrar área de upload -->
        <UploadArea
          v-if="!currentDocument"
          v-model:embedding-type="embeddingType"
          :is-uploading="isUploading"
          :upload-progress="uploadProgress"
          @upload="uploadDocument"
          @error="showToastMessage"
        />

        <!-- Con documento: PDF izquierda + chat derecha -->
        <div v-if="currentDocument" class="pdf-pane">
          <PdfViewer 
            ref="embeddedPdfViewer" 
            mode="embedded" 
            :pdfUrl="pdfViewerUrl" 
            :startPage="pdfViewerStartPage" 
          />
        </div>

        <!-- Con documento: Mostrar chat -->
        <div v-if="currentDocument" class="chat-area">
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
              <textarea
                v-model="messageInput"
                placeholder="Haz una pregunta sobre el documento... (Ctrl+Enter para enviar)"
                @keydown="handleInputKeydown"
                :disabled="isSending"
                class="message-input"
                rows="1"
                ref="messageTextarea"
              ></textarea>
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
              <div class="keyboard-hints">
                <span class="hint"><kbd>Ctrl</kbd> + <kbd>Enter</kbd> para enviar</span>
                <span class="hint"><kbd>Ctrl</kbd> + <kbd>N</kbd> para nuevo chat</span>
              </div>
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

    <!-- Shortcuts Modal -->
    <ShortcutsModal
      :visible="showShortcutsModal"
      @close="showShortcutsModal = false"
    />

    <!-- Tag Editor Modal -->
    <TagEditor
      :visible="showTagEditor"
      :initial-tags="(recentDocuments.find(d => d.id === tagEditorDocId) || {}).tags || []"
      @close="showTagEditor = false"
      @save="saveTagsForDoc"
      @update="autosaveTagsForDoc"
    />
  </div>
</template>

<script>
import DragOverlay from './components/ui/DragOverlay.vue';
import DocumentList from './components/sidebar/DocumentList.vue';
import FolderList from './components/sidebar/FolderList.vue';
import TagEditor from './components/sidebar/TagEditor.vue';
import ConversationList from './components/sidebar/ConversationList.vue';
import UploadArea from './components/chat/UploadArea.vue';
import WelcomeMessage from './components/chat/WelcomeMessage.vue';
import ChatMessage from './components/chat/ChatMessage.vue';
import TypingIndicator from './components/chat/TypingIndicator.vue';
import ToastNotification from './components/ui/ToastNotification.vue';
import ExportButton from './components/chat/ExportButton.vue';
import ShortcutsModal from './components/ui/ShortcutsModal.vue';
import PdfViewer from './components/PdfViewer.vue';
import PDFHistory from './components/PDFHistory.vue';

export default {
  name: 'App',
  components: {
    DragOverlay,
  DocumentList,
  FolderList,
  TagEditor,
    ConversationList,
    UploadArea,
    WelcomeMessage,
    ChatMessage,
    TypingIndicator,
    ToastNotification,
    ExportButton,
    ShortcutsModal,
    PdfViewer
    ,PDFHistory
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

  // Folders / Categories
  folders: [],
  activeFolderId: null,
      showOnlyFavorites: false,

      // Chat State
      messages: [],
      messageInput: '',
      isSending: false,
      isTyping: false,
      copiedMessageIndex: null,

  // Conversations
    showPdfHistory: false,
      conversations: [],
      currentConversationId: null,
      showConversationsPanel: false,

      // Toast
      toast: {
        show: false,
        message: '',
        type: 'info'
      },

      // Modals
      showShortcutsModal: false,
  // Tag editor
  showTagEditor: false,
  tagEditorDocId: null,
  // Tag filter
  activeTag: null,
  // PDF viewer (embedded)
  pdfViewerUrl: '',
  pdfViewerStartPage: 1,

      // Sidebar helpers
      showConversationsPanel: false
    };
  },

  mounted() {
    this.checkMobile();
    window.addEventListener('resize', this.checkMobile);
  this.loadRecentDocuments();
  this.loadDocumentsFromBackend();
  this.loadFolders();
  this.loadConversations();
  this.loadTheme();
    this.setupDragAndDrop();
    this.setupKeyboardShortcuts();
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.checkMobile);
    this.removeDragAndDrop();
    this.removeKeyboardShortcuts();
  },

  computed: {
    favoriteDocuments() {
      return (this.recentDocuments || []).filter(d => d.favorite);
    }
    ,
    uniqueTags() {
      const s = new Set();
      (this.recentDocuments || []).forEach(d => {
        (d.tags || []).forEach(t => s.add(t));
      });
      return Array.from(s);
    }
    ,
    tagCounts() {
      const counts = {};
      (this.recentDocuments || []).forEach(d => {
        (d.tags || []).forEach(t => { counts[t] = (counts[t] || 0) + 1; });
      });
      return counts;
    }
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

    async loadDocumentsFromBackend(folderId = null) {
      try {
        const url = folderId ? `http://localhost:8000/pdfs/?folder_id=${folderId}` : 'http://localhost:8000/pdfs/';
        const res = await fetch(url);
        if (!res.ok) throw new Error('No backend');
        const data = await res.json();
        if (data && Array.isArray(data.pdfs)) {
          // Map backend shape to frontend recentDocuments
          this.recentDocuments = data.pdfs.map(p => ({
            id: p.id,
            name: p.name,
            pages: p.pages || 0,
            date: p.uploadedAt || '',
            uploadedAt: p.uploadedAt || null,
            embeddingType: p.embeddingType || 'openai',
            folderId: p.folderId || null,
            favorite: !!p.favorite,
            tags: p.tags || []
          }));
          this.saveRecentDocuments();
        }
      } catch (err) {
        // keep localStorage data if backend not available
      }
    },

    saveRecentDocuments() {
      localStorage.setItem('chatpdf-documents', JSON.stringify(this.recentDocuments));
    },

    // Folders management
    loadFolders() {
      // Try to fetch folders from backend first
      fetch('http://localhost:8000/folders/')
        .then(res => res.json())
        .then(data => {
          this.folders = data.folders || [];
        })
        .catch(() => {
          const saved = localStorage.getItem('chatpdf-folders');
          this.folders = saved ? JSON.parse(saved) : [];
        });
    },

    saveFolders() {
      localStorage.setItem('chatpdf-folders', JSON.stringify(this.folders));
    },

    createFolder(name) {
      // Create on backend
      const form = new FormData();
      form.append('name', name);
      fetch('http://localhost:8000/folders/', { method: 'POST', body: form })
        .then(r => r.json())
        .then(folder => {
          this.folders.unshift(folder);
          this.showToastMessage(`Carpeta creada: ${name}`, 'success');
        })
        .catch(() => {
          const folder = { id: Date.now(), name };
          this.folders.unshift(folder);
          this.saveFolders();
          this.showToastMessage(`Carpeta creada en local: ${name}`, 'warning');
        });
    },

    deleteFolder(folderId) {
      if (!confirm('Eliminar carpeta y mantener documentos sin carpeta?')) return;
      fetch(`http://localhost:8000/folders/${folderId}`, { method: 'DELETE' })
        .then(() => {
          this.folders = this.folders.filter(f => f.id !== folderId);
          // reload documents from backend to reflect server state
          this.loadDocumentsFromBackend(this.activeFolderId);
          if (this.activeFolderId === folderId) this.activeFolderId = null;
          this.showToastMessage('Carpeta eliminada', 'info');
        })
        .catch(() => {
          this.folders = this.folders.filter(f => f.id !== folderId);
          this.saveFolders();
          this.showToastMessage('Carpeta eliminada localmente', 'warning');
        });
    },

    async deletePdf(pdfId) {
      if (!confirm('¿Eliminar este PDF y todos sus datos asociados? Esta acción no se puede deshacer.')) return;
      try {
        const res = await fetch(`http://localhost:8000/pdfs/${pdfId}`, { method: 'DELETE' });
        if (res.ok) {
          this.recentDocuments = this.recentDocuments.filter(d => d.id !== pdfId);
          if (this.currentDocument && this.currentDocument.id === pdfId) {
            this.closeDocument();
          }
          this.showToastMessage('PDF eliminado', 'info');
        } else {
          // If server returned 404 or other, still remove locally to keep UI responsive
          this.recentDocuments = this.recentDocuments.filter(d => d.id !== pdfId);
          this.showToastMessage('PDF eliminado localmente (server no respondió OK)', 'warning');
        }
      } catch (e) {
        // Best-effort local removal
        this.recentDocuments = this.recentDocuments.filter(d => d.id !== pdfId);
        this.showToastMessage('PDF eliminado localmente (error de red)', 'warning');
      }
    },

    async clearAllPdfs() {
      if (!confirm('¿Eliminar todos los PDFs? Esta acción eliminará permanentemente todos los PDFs en el servidor.')) return;
      const ids = this.recentDocuments.map(d => d.id);
      for (const id of ids) {
        try {
          await fetch(`http://localhost:8000/pdfs/${id}`, { method: 'DELETE' });
        } catch (e) {
          // ignore individual failures
        }
      }
      this.recentDocuments = [];
      this.closeDocument();
      this.showToastMessage('Todos los PDFs eliminados', 'info');
    },

    selectFolder(folderId) {
      // Toggle folder: clicking the active folder will deselect it (close)
      if (this.activeFolderId === folderId) {
        this.activeFolderId = null;
        this.showToastMessage('Carpeta cerrada', 'info');
        // load all documents
        this.loadDocumentsFromBackend(null);
      } else {
        this.activeFolderId = folderId;
        this.showToastMessage('Carpeta seleccionada', 'info');
        // load documents for this folder from backend
        this.loadDocumentsFromBackend(folderId);
      }
      // Close conversations panel when switching folders
      this.showConversationsPanel = false;
    },

    openTagsPanel(docId) {
      this.tagEditorDocId = docId;
      this.showTagEditor = true;
    },

    saveTagsForDoc(tags) {
      const doc = this.recentDocuments.find(d => d.id === this.tagEditorDocId);
      if (!doc) return;
      doc.tags = tags;
      // send to backend
      const payload = JSON.stringify({ tags });
      const form = new FormData(); form.append('metadata', payload);
      fetch(`http://localhost:8000/documents/${doc.id}/metadata`, { method: 'POST', body: form })
        .then(() => {
          this.saveRecentDocuments();
          this.showToastMessage('Etiquetas guardadas', 'success');
          this.showTagEditor = false;
          this.tagEditorDocId = null;
        })
        .catch(() => {
          this.saveRecentDocuments();
          this.showToastMessage('Etiquetas guardadas localmente (sin sync)', 'warning');
          this.showTagEditor = false;
          this.tagEditorDocId = null;
        });
    },

      autosaveTagsForDoc(tags) {
        // Similar to saveTagsForDoc but doesn't close the editor (used for live updates)
        const doc = this.recentDocuments.find(d => d.id === this.tagEditorDocId);
        if (!doc) return;
        doc.tags = tags;
        const payload = JSON.stringify({ tags });
        const form = new FormData(); form.append('metadata', payload);
        fetch(`http://localhost:8000/documents/${doc.id}/metadata`, { method: 'POST', body: form })
          .then(() => {
            this.saveRecentDocuments();
          })
          .catch(() => {
            this.saveRecentDocuments();
          });
      },

    moveDocumentToFolder(documentId, folderId) {
      this.recentDocuments = this.recentDocuments.map(d => d.id === documentId ? { ...d, folderId } : d);
      // Send metadata to backend
      const payload = JSON.stringify({ folderId });
      const form = new FormData(); form.append('metadata', payload);
      fetch(`http://localhost:8000/documents/${documentId}/metadata`, { method: 'POST', body: form })
        .then(() => {
          // reload documents from backend for the active folder (server is source of truth)
          this.loadDocumentsFromBackend(this.activeFolderId);
          this.showToastMessage('Documento movido', 'success');
        })
        .catch(() => {
          this.saveRecentDocuments();
          this.showToastMessage('Documento movido localmente (sin sync)', 'warning');
        });
    },

    removeTagFromDoc({ docId, tag }) {
      const doc = this.recentDocuments.find(d => d.id === docId);
      if (!doc) return;
      doc.tags = (doc.tags || []).filter(t => t !== tag);
      const payload = JSON.stringify({ tags: doc.tags });
      const form = new FormData(); form.append('metadata', payload);
      fetch(`http://localhost:8000/documents/${docId}/metadata`, { method: 'POST', body: form })
        .then(() => {
          this.saveRecentDocuments();
          this.showToastMessage('Etiqueta eliminada', 'success');
        })
        .catch(() => {
          this.saveRecentDocuments();
          this.showToastMessage('Etiqueta eliminada localmente (sin sync)', 'warning');
        });
    },

    toggleFavorite(docId) {
      this.recentDocuments = this.recentDocuments.map(d => d.id === docId ? { ...d, favorite: !d.favorite } : d);
      const doc = this.recentDocuments.find(d => d.id === docId);
      const payload = JSON.stringify({ favorite: !!doc.favorite });
      const form = new FormData(); form.append('metadata', payload);
      fetch(`http://localhost:8000/documents/${docId}/metadata`, { method: 'POST', body: form })
        .then(() => {
          this.loadDocumentsFromBackend(this.activeFolderId);
          this.saveRecentDocuments();
        })
        .catch(() => {
          this.saveRecentDocuments();
          this.showToastMessage('Favorito cambiado localmente (sin sync)', 'warning');
        });
    },

    setActiveTag(tag) {
      this.activeTag = tag;
      // No hacemos fetch al backend; DocumentList hará el filtrado cliente
      this.showToastMessage(tag ? `Filtrando por etiqueta: ${tag}` : 'Filtro de etiqueta desactivado', 'info');
    },


    handleFileSelect(event) {
      const files = Array.from(event.target.files || []);
      const pdfs = files.filter(f => f.type === 'application/pdf');
      if (pdfs.length === 0) {
        this.showToastMessage('Por favor selecciona al menos un archivo PDF válido', 'error');
        event.target.value = '';
        return;
      }
      if (pdfs.length === 1) {
        this.selectedFile = pdfs[0];
      } else {
        // If multiple selected, start multi-upload flow
        this.uploadMultipleDocuments(pdfs.map(f => ({ file: f, embeddingType: this.embeddingType })));
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

      const files = Array.from(e.dataTransfer.files || []);
      const pdfs = files.filter(f => f.type === 'application/pdf');
      if (pdfs.length === 0) {
        this.showToastMessage('Por favor arrastra al menos un archivo PDF válido', 'error');
        return;
      }
      if (pdfs.length === 1) {
        this.uploadDocument({ file: pdfs[0], embeddingType: this.embeddingType });
      } else {
        this.uploadMultipleDocuments(pdfs.map(f => ({ file: f, embeddingType: this.embeddingType })));
      }
    },

    async uploadMultipleDocuments(items) {
      // items: [{file, embeddingType}, ...]
      const filesToUpload = [];
      const hashes = [];

      for (const it of items) {
        try {
          const arrayBuffer = await it.file.arrayBuffer();
          const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
          const hashArray = Array.from(new Uint8Array(hashBuffer));
          const fileHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
          hashes.push(fileHash);
          filesToUpload.push({ file: it.file, embeddingType: it.embeddingType, fileHash });
        } catch (err) {
          // if hashing fails, include the file without hash
          hashes.push(null);
          filesToUpload.push({ file: it.file, embeddingType: it.embeddingType, fileHash: null });
        }
      }

      // Pre-check duplicates in parallel by querying /pdfs/?hash= for each non-null hash
      const existingHashes = new Set();
      await Promise.all(hashes.map(async (h) => {
        if (!h) return;
        try {
          const res = await fetch(`http://localhost:8000/pdfs/?hash=${h}`);
          if (res.ok) {
            const d = await res.json();
            if (d.pdfs && d.pdfs.length > 0) {
              existingHashes.add(h);
            }
          }
        } catch (e) { /* ignore */ }
      }));

      // Build FormData for upload_pdfs endpoint, skipping duplicates
      const form = new FormData();
      form.append('embedding_type', this.embeddingType);
      const fileHashesForForm = [];
      for (const f of filesToUpload) {
        if (f.fileHash && existingHashes.has(f.fileHash)) {
          this.showToastMessage(`Omitido (duplicado): ${f.file.name}`, 'warning');
          continue;
        }
        form.append('pdfs', f.file, f.file.name);
        if (f.fileHash) form.append('file_hashes', f.fileHash);
      }

      try {
        this.isUploading = true;
        const response = await fetch('http://localhost:8000/upload_pdfs/', { method: 'POST', body: form });
        const data = await response.json();
        if (data && data.results) {
          data.results.forEach(r => {
            if (r.status === 'uploaded') {
              this.showToastMessage(`Subido: ${r.filename}`, 'success');
              // Optionally add to recentDocuments
              this.recentDocuments.unshift({ id: r.pdf_id, name: r.filename, pages: 0, uploadedAt: new Date().toISOString(), embeddingType: this.embeddingType, folderId: null, favorite: false, tags: [] });
            } else if (r.status === 'duplicate') {
              this.showToastMessage(`Omitido (duplicado): ${r.filename}`, 'warning');
            } else {
              this.showToastMessage(`Error subiendo ${r.filename}: ${r.detail || 'unknown'}`, 'error');
            }
          });
          this.saveRecentDocuments();
        }
      } catch (err) {
        console.error(err);
        this.showToastMessage('Error al subir archivos', 'error');
      } finally {
        this.isUploading = false;
      }
    },

    async uploadDocument(payload) {
      const { file, embeddingType } = payload;
      if (!file) return;

      // Compute SHA-256 hash of file and check with backend by hash
      let fileHash = null;
      try {
        const arrayBuffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        fileHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

        // Check by hash (more reliable) using the new backend filter
        try {
          if (fileHash) {
            const checkRes = await fetch(`http://localhost:8000/pdfs/?hash=${fileHash}`);
            if (checkRes.ok) {
              const d = await checkRes.json();
              // If any pdf matches this hash, cancel upload
              if (d.pdfs && d.pdfs.length > 0) {
                this.showToastMessage('Este PDF ya existe en la base de datos (por contenido). Subida cancelada.', 'warning');
                return;
              }
            }
          }
        } catch (e) {
          // ignore check errors and proceed with upload; server will still reject duplicates
        }
      } catch (err) {
        // ignore hashing errors and proceed without hash
        fileHash = null;
      }

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

        if (fileHash) formData.append('file_hash', fileHash);
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
          embeddingType: embeddingType,
          folderId: this.activeFolderId || null,
          favorite: false,
          tags: []
        };

        this.currentDocument = newDoc;
        
        // Agregar a documentos recientes
        this.recentDocuments.unshift(newDoc);
        if (this.recentDocuments.length > 10) {
          this.recentDocuments = this.recentDocuments.slice(0, 10);
        }
        this.saveRecentDocuments();

        // Cargar conversaciones del nuevo documento
        this.loadConversations();

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

    async selectDocument(doc) {
      // Guardar conversación actual antes de cambiar de documento
      if (this.messages.length > 0 && this.currentDocument) {
        this.saveCurrentConversation();
      }

      this.currentDocument = doc;
      this.messages = [];
      this.currentConversationId = null;
      this.embeddingType = doc.embeddingType || 'openai';
      
      // Configurar URL del PDF para el visor embebido
      try {
        const base = 'http://localhost:8000'; // usar config si está disponible
        this.pdfViewerUrl = `${base}/pdfs/${doc.id}/file`;
        this.pdfViewerStartPage = 1;
        
        // Dar tiempo al componente para montarse y luego abrir el PDF
        this.$nextTick(() => {
          if (this.$refs.embeddedPdfViewer && typeof this.$refs.embeddedPdfViewer.open === 'function') {
            this.$refs.embeddedPdfViewer.open();
          }
        });
      } catch (e) {
        console.warn('Error configurando visor PDF:', e);
      }
      
      // Cargar conversaciones del nuevo documento
      this.loadConversations();
      
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
      // Guardar conversación actual si hay mensajes
      if (this.messages.length > 0 && this.currentDocument) {
        this.saveCurrentConversation();
      }

      // Crear nueva conversación
      this.currentConversationId = null;
      this.messages = [];
      this.messageInput = '';
      
      if (!this.currentDocument) {
        this.showToastMessage('Sube un PDF para comenzar', 'info');
      }
      if (this.isMobile) {
        this.sidebarOpen = false;
      }
    },

    // Conversation Methods
    loadConversations() {
      if (!this.currentDocument) {
        this.conversations = [];
        return;
      }

      const stored = localStorage.getItem(`conversations_${this.currentDocument.id}`);
      this.conversations = stored ? JSON.parse(stored) : [];
    },

    saveCurrentConversation() {
      if (!this.currentDocument || this.messages.length === 0) return;

      const conversation = {
        id: this.currentConversationId || Date.now(),
        title: this.generateConversationTitle(),
        messages: this.messages,
        messageCount: this.messages.length,
        date: new Date().toLocaleDateString('es-ES'),
        timestamp: new Date()
      };

      // Actualizar o agregar conversación
      const index = this.conversations.findIndex(c => c.id === conversation.id);
      if (index !== -1) {
        this.conversations[index] = conversation;
      } else {
        this.conversations.unshift(conversation);
      }

      // Limitar a 20 conversaciones por documento
      if (this.conversations.length > 20) {
        this.conversations = this.conversations.slice(0, 20);
      }

      // Guardar en localStorage
      localStorage.setItem(
        `conversations_${this.currentDocument.id}`,
        JSON.stringify(this.conversations)
      );

      this.currentConversationId = conversation.id;
    },

    generateConversationTitle() {
      // Usar el primer mensaje del usuario como título
      const firstUserMessage = this.messages.find(m => m.role === 'user');
      if (firstUserMessage) {
        const title = firstUserMessage.content.slice(0, 40);
        return title.length < firstUserMessage.content.length ? title + '...' : title;
      }
      return `Conversación ${new Date().toLocaleTimeString('es-ES')}`;
    },

    selectConversation(conversation) {
      // Guardar conversación actual antes de cambiar
      if (this.messages.length > 0 && this.currentConversationId) {
        this.saveCurrentConversation();
      }

      // Cargar conversación seleccionada
      this.currentConversationId = conversation.id;
      this.messages = conversation.messages || [];
      this.showToastMessage(`Conversación cargada: ${conversation.title}`, 'info');

      // Cerrar el panel de conversaciones después de seleccionar
      this.showConversationsPanel = false;

      if (this.isMobile) {
        this.sidebarOpen = false;
      }
    },

    newConversation() {
      this.startNewChat();
      this.showConversationsPanel = false;
    },

    deleteConversation(conversationId) {
      if (!confirm('¿Estás seguro de eliminar esta conversación?')) return;

      this.conversations = this.conversations.filter(c => c.id !== conversationId);
      
      // Guardar cambios
      if (this.currentDocument) {
        localStorage.setItem(
          `conversations_${this.currentDocument.id}`,
          JSON.stringify(this.conversations)
        );
      }

      // Si se eliminó la conversación actual, limpiar
      if (this.currentConversationId === conversationId) {
        this.messages = [];
        this.currentConversationId = null;
      }

      this.showToastMessage('Conversación eliminada', 'success');
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

      // Reset textarea height
      this.$nextTick(() => {
        const textarea = this.$refs.messageTextarea;
        if (textarea) {
          textarea.style.height = 'auto';
        }
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
        
        // Auto-guardar conversación después de cada respuesta
        this.saveCurrentConversation();
        
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
      this.showShortcutsModal = true;
    },

    handleExport({ format, filename }) {
      this.showToastMessage(`Conversación exportada como ${format.toUpperCase()}`, 'success');
      console.log('Exported:', filename);
    },

    // Keyboard Shortcuts
    setupKeyboardShortcuts() {
      this.handleKeydown = (e) => {
        // Ctrl/Cmd + N: Nuevo chat
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
          e.preventDefault();
          this.startNewChat();
        }
        
        // Ctrl/Cmd + K: Enfocar búsqueda de documentos
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
          e.preventDefault();
          const searchInput = document.querySelector('.search-input');
          if (searchInput) searchInput.focus();
        }
        
        // ?: Mostrar atajos de teclado
        if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
          // Solo si no está escribiendo en un input
          const activeElement = document.activeElement;
          if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            this.showShortcutsModal = true;
          }
        }
        
        // Escape: Cancelar/cerrar
        if (e.key === 'Escape') {
          // Cerrar modal si está abierto
          if (this.showShortcutsModal) {
            this.showShortcutsModal = false;
          }
          // Si hay un documento abierto, cerrar
          else if (this.currentDocument) {
            this.closeDocument();
          }
        }
        
        // Ctrl/Cmd + Enter: Enviar mensaje (se maneja en el textarea)
        // Implementado directamente en el textarea del chat
      };
      
      window.addEventListener('keydown', this.handleKeydown);
    },

    removeKeyboardShortcuts() {
      if (this.handleKeydown) {
        window.removeEventListener('keydown', this.handleKeydown);
      }
    },

    handleInputKeydown(e) {
      // Ctrl/Cmd + Enter: Enviar mensaje
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        this.sendMessage();
        return;
      }
      
      // Auto-resize textarea
      this.$nextTick(() => {
        const textarea = this.$refs.messageTextarea;
        if (textarea) {
          textarea.style.height = 'auto';
          textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
        }
      });
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

#app.light-mode .history-section {
  border-top-color: #e2e8f0;
}

#app.light-mode .history-btn {
  border-color: #e2e8f0;
  color: #1a202c;
}

#app.light-mode .history-btn:hover {
  background: #f7fafc;
}

#app.light-mode .history-btn.active {
  background: #edf2f7;
  color: #4d6cfa;
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

.favorites-quick {
  padding: 0 12px 12px;
}
.fav-title { font-size: 12px; color: #9ca3af; margin: 0 0 6px; }
.fav-list { display:flex; flex-direction:column; gap:6px; }
.fav-item { background: transparent; border: none; color: #e4e6eb; text-align: left; padding: 8px; border-radius: 8px; cursor: pointer; }
.fav-item:hover { background: #1e2640; }

.tag-chip { background: transparent; border: 1px solid #2a3152; color: #9ca3af; padding: 6px 8px; border-radius: 12px; cursor: pointer; font-size: 13px; }
.tag-chip.active { background: #4d6cfa; color: white; border-color: #4d6cfa; }
.tag-count { margin-left: 6px; background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 8px; font-size: 12px; }

/* History Section */
.history-section {
  padding: 12px 20px;
  border-top: 1px solid #2a3152;
}

.history-btn {
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #e4e6eb;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.2s;
  position: relative;
}

.history-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
}

.history-btn.active {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
}

.history-btn .icon {
  font-size: 16px;
}

.history-btn .badge {
  margin-left: auto;
  background: #4d6cfa;
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
  min-width: 20px;
  text-align: center;
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

.doc-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
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

/* Two-column layout: PDF + Chat */
.chat-container.two-column {
  flex-direction: row;
  gap: 0;
}

.pdf-pane {
  width: 45%;
  min-width: 400px;
  border-right: 1px solid #1e2640;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.chat-container.two-column .chat-area {
  width: 55%;
  flex: 1;
}

/* Responsive: stack vertically on small screens */
@media (max-width: 1024px) {
  .chat-container.two-column {
    flex-direction: column;
  }
  
  .pdf-pane {
    width: 100%;
    height: 40vh;
    border-right: none;
    border-bottom: 1px solid #1e2640;
  }
  
  .chat-container.two-column .chat-area {
    width: 100%;
    height: 60vh;
  }
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
  resize: none;
  min-height: 44px;
  max-height: 200px;
  line-height: 1.5;
  overflow-y: auto;
}

.message-input::placeholder {
  color: #6b7280;
}

/* Scrollbar para el textarea */
.message-input::-webkit-scrollbar {
  width: 6px;
}

.message-input::-webkit-scrollbar-track {
  background: transparent;
}

.message-input::-webkit-scrollbar-thumb {
  background: #2a3152;
  border-radius: 3px;
}

.message-input::-webkit-scrollbar-thumb:hover {
  background: #4d6cfa;
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
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.keyboard-hints {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
}

.keyboard-hints .hint {
  display: flex;
  align-items: center;
  gap: 4px;
}

.keyboard-hints kbd {
  padding: 2px 6px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 4px;
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  color: #e4e6eb;
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

/* ==================== PDF VIEWER EMBEDDED STYLES ==================== */
.pdf-embedded {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0e27;
}

.embedded-controls {
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #151934;
  border-bottom: 1px solid #1e2640;
  flex-shrink: 0;
}

.embedded-controls button {
  padding: 8px 16px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 6px;
  color: #e4e6eb;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.embedded-controls button:hover:not(:disabled) {
  background: #2a3152;
  border-color: #4d6cfa;
}

.embedded-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.embedded-controls span {
  color: #9ca3af;
  font-size: 14px;
}

.embedded-controls label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9ca3af;
  font-size: 13px;
}

.embedded-controls input[type="range"] {
  width: 100px;
}

.embedded-canvas-wrap {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.embedded-canvas-wrap canvas {
  display: block;
  max-width: 100%;
  height: auto;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.error-msg {
  color: #ff7b7b;
  padding: 12px;
  text-align: center;
  font-size: 14px;
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
