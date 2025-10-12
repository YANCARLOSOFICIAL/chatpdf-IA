<template>
  <div class="document-list">
    <h3 class="section-title">DOCUMENTOS RECIENTES</h3>
    
    <div class="docs-list">
      <div 
        v-for="doc in documents" 
        :key="doc.id"
        class="doc-item"
        :class="{ 'active': activeDocumentId === doc.id }"
        @click="$emit('select', doc)"
      >
        <span class="doc-icon">📄</span>
        <div class="doc-info">
          <div class="doc-name">{{ doc.name }}</div>
          <div class="doc-date">{{ doc.date }}</div>
        </div>
      </div>

      <div v-if="documents.length === 0" class="empty-docs">
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
  emits: ['select']
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

.empty-docs p {
  margin: 0;
}

/* Light mode */
:global(#app.light-mode) .section-title {
  color: #718096;
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
</style>
