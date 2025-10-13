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
      >
        <span class="doc-icon">📄</span>
        <div class="doc-info">
          <div class="doc-name" v-html="highlightText(doc.name)"></div>
          <div class="doc-date">{{ doc.date }}</div>
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
    }
  },
  emits: ['select'],
  data() {
    return {
      searchQuery: ''
    };
  },
  computed: {
    filteredDocuments() {
      if (!this.searchQuery.trim()) {
        return this.documents;
      }
      
      const query = this.searchQuery.toLowerCase().trim();
      return this.documents.filter(doc => 
        doc.name.toLowerCase().includes(query)
      );
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
