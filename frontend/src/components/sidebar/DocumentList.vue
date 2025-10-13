<template>
  <div class="document-list">
    <h3 class="section-title">DOCUMENTOS RECIENTES</h3>
    
    <!-- Búsqueda de documentos -->
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input 
        v-model="searchQuery"
        type="text" 
        class="search-input"
        placeholder="Buscar documentos..."
        @input="handleSearch"
      />
      <button 
        v-if="searchQuery"
        @click="clearSearch"
        class="clear-btn"
        title="Limpiar búsqueda"
      >
        ✕
      </button>
    </div>
    
    <div class="docs-list">
      <div 
        v-for="doc in filteredDocuments" 
        :key="doc.id"
        class="doc-item"
        :class="{ 'active': activeDocumentId === doc.id }"
        @click="$emit('select', doc)"
        draggable="true"
        @dragstart="(e) => { e.dataTransfer.setData('text/plain', doc.id); e.dataTransfer.effectAllowed = 'move'; }"
        @dragend="(e) => { /* placeholder for potential cleanup */ }"
      >
        <span class="doc-icon">📄</span>
        <div class="doc-info">
          <div class="doc-name" v-html="highlightText(doc.name)"></div>
          <div class="doc-date">{{ doc.date }}</div>
              <div class="doc-tags">
                <span v-for="(t, idx) in (doc.tags || [])" :key="idx" class="tag-chip-inline">
                  {{ t }}
                  <button class="tag-x" @click.stop.prevent="$emit('remove-tag', { docId: doc.id, tag: t })" title="Eliminar etiqueta">✕</button>
                </span>
              </div>
        </div>

        <div class="doc-actions">
          <button class="tag-btn" @click="openTags(doc, $event)" title="Tags">🏷️</button>
          <button class="fav-btn" @click="toggleFavorite(doc, $event)" :title="doc.favorite ? 'Quitar favorito' : 'Marcar favorito'">
            <span v-if="doc.favorite">⭐</span>
            <span v-else>☆</span>
          </button>
        </div>
      </div>

      <div v-if="filteredDocuments.length === 0 && searchQuery" class="empty-docs">
        <p>No se encontraron documentos</p>
        <button @click="clearSearch" class="clear-search-btn">Limpiar búsqueda</button>
      </div>

      <div v-else-if="documents.length === 0" class="empty-docs">
        <p>No hay documentos recientes</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DocumentList',
  props: {
    documents: {
      type: Array,
      default: () => []
    },
    activeDocumentId: {
      type: [String, Number],
      default: null
    },
    // Filtrar por carpeta
    activeFolderId: {
      type: [String, Number],
      default: null
    },
    // Filtrar por etiqueta (tag)
    activeTag: {
      type: String,
      default: null
    },
    showFavorites: {
      type: Boolean,
      default: false
    }
  },
  emits: ['select', 'toggle-favorite', 'open-tags', 'remove-tag'],
  data() {
    return {
      searchQuery: ''
    };
  },
  computed: {
    filteredDocuments() {
      let docs = this.documents || [];

      // Filtrar por carpeta si se indica
      if (this.activeFolderId) {
        docs = docs.filter(d => (d.folderId || null) === this.activeFolderId);
      }

      // Filtrar por favoritos si se solicita
      if (this.showFavorites) {
        docs = docs.filter(d => d.favorite);
      }

      // Filtrar por búsqueda
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase().trim();
        docs = docs.filter(doc => doc.name.toLowerCase().includes(query));
      }

      // Filtrar por etiqueta si se indicó
      if (this.activeTag) {
        docs = docs.filter(d => Array.isArray(d.tags) && d.tags.includes(this.activeTag));
      }

      // Orden simple: favoritos primero
      docs = docs.slice().sort((a, b) => {
        const aFav = a.favorite ? 0 : 1;
        const bFav = b.favorite ? 0 : 1;
        return aFav - bFav;
      });

      return docs;
    }
  },
  methods: {
    handleSearch() {
      // Evento opcional para tracking
      this.$emit('search', this.searchQuery);
    },
    clearSearch() {
      this.searchQuery = '';
    },
    highlightText(text) {
      if (!this.searchQuery.trim()) {
        return text;
      }
      
      const query = this.searchQuery.trim();
      const regex = new RegExp(`(${query})`, 'gi');
      return text.replace(regex, '<mark>$1</mark>');
    }
  ,
    toggleFavorite(doc, ev) {
      ev.stopPropagation();
      this.$emit('toggle-favorite', doc.id);
    },
    openTags(doc, ev) {
      ev.stopPropagation();
      this.$emit('open-tags', doc.id);
    }
  }
};
</script>

<style scoped>
.document-list {
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
  margin: 0;
}

/* Búsqueda */
.search-box {
  position: relative;
  margin: 0 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  pointer-events: none;
  z-index: 1;
}

.search-input {
  width: 100%;
  padding: 8px 32px 8px 36px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #e4e6eb;
  font-size: 13px;
  outline: none;
  transition: all 0.2s;
}

.search-input::placeholder {
  color: #6b7280;
}

.search-input:focus {
  border-color: #4d6cfa;
  background: #151934;
}

.clear-btn {
  position: absolute;
  right: 8px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #6b7280;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.clear-btn:hover {
  background: #2a3152;
  color: #e4e6eb;
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

.doc-name :deep(mark) {
  background: #4d6cfa;
  color: white;
  padding: 2px 4px;
  border-radius: 3px;
}

.doc-date {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

.doc-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.fav-btn, .tag-btn {
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 14px;
  padding: 6px;
  border-radius: 6px;
}

.fav-btn:hover, .tag-btn:hover { background: #1e2640; color: #4d6cfa; }

.empty-docs {
  padding: 32px 16px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
}

.empty-docs p {
  margin: 0 0 12px 0;
}

.clear-search-btn {
  padding: 6px 12px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 6px;
  color: #e4e6eb;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-search-btn:hover {
  background: #2a3152;
  border-color: #4d6cfa;
}

.doc-tags { margin-top: 6px; display:flex; gap:6px; flex-wrap:wrap; }
.tag-chip-inline { background:#101428; color:#9ca3af; padding:4px 8px; border-radius:12px; font-size:12px; }
.tag-chip-inline:hover { background:#1e2640; color:#e4e6eb; }

.tag-chip.active { background:#4d6cfa; color:white; }

.tag-x { margin-left:8px; background:transparent; border:none; color:#9ca3af; cursor:pointer; padding:2px 6px; border-radius:6px; }
.tag-x:hover { background:#2a3152; color:#e4e6eb; }

/* Light mode */
:global(#app.light-mode) .section-title {
  color: #718096;
}

:global(#app.light-mode) .search-input {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #1a202c;
}

:global(#app.light-mode) .search-input:focus {
  background: #ffffff;
}

:global(#app.light-mode) .clear-btn:hover {
  background: #e2e8f0;
}

:global(#app.light-mode) .doc-item {
  color: #1a202c;
}

:global(#app.light-mode) .doc-item:hover {
  background: #f7fafc;
}

:global(#app.light-mode) .doc-item.active {
  background: #edf2f7;
}

:global(#app.light-mode) .doc-name {
  color: #1a202c;
}

:global(#app.light-mode) .doc-date {
  color: #718096;
}

:global(#app.light-mode) .empty-docs {
  color: #718096;
}

:global(#app.light-mode) .clear-search-btn {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #1a202c;
}

:global(#app.light-mode) .clear-search-btn:hover {
  background: #e2e8f0;
}
</style>
