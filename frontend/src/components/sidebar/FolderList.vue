<template>
  <div class="folder-list">
    <div class="folder-header">
      <h3 class="section-title">CARPETAS</h3>
      <button class="add-folder-btn" @click="promptNewFolder">➕</button>
    </div>

    <div class="folders">
      <div
        v-for="folder in folders"
        :key="folder.id"
        class="folder-item"
        :class="{ active: activeFolderId === folder.id, 'drag-over': hoverFolderId === folder.id }"
        @click="$emit('select', folder.id)"
        @dragover.prevent="(e) => { e.dataTransfer.dropEffect = 'move'; }"
        @dragenter="(e) => onDragEnter(folder.id, e)"
        @dragleave="(e) => onDragLeave(folder.id, e)"
        @drop="(e) => onDrop(folder.id, e)"
      >
        <span class="folder-icon">📂</span>
        <span class="folder-chevron" v-if="activeFolderId === folder.id">▾</span>
        <span class="folder-chevron" v-else>▸</span>
        <div class="folder-name">{{ folder.name }}</div>
        <button class="chat-folder-btn" @click.stop="$emit('chat-folder', folder)" title="Chatear con esta carpeta">💬</button>
        <button class="del-btn" @click.stop="$emit('delete', folder.id)" title="Eliminar carpeta">✕</button>

        <!-- Expanded docs for this folder -->
        <div v-if="activeFolderId === folder.id" class="folder-docs">
          <div v-for="doc in documents.filter(d => (d.folderId || null) === folder.id)" :key="doc.id" class="folder-doc-item" @click.stop="$emit('select-document', doc)">
            <span class="doc-icon">📄</span>
            <span class="doc-name">{{ doc.name }}</span>
          </div>
          <div v-if="documents.filter(d => (d.folderId || null) === folder.id).length === 0" class="empty-folder-docs">No hay documentos en esta carpeta</div>
        </div>
      </div>

      <div v-if="folders.length === 0" class="empty-folders">No hay carpetas</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FolderList',
  props: {
    folders: { type: Array, default: () => [] },
    activeFolderId: { type: [String, Number], default: null },
    documents: { type: Array, default: () => [] }
  },
  emits: ['select', 'new', 'delete', 'drop', 'select-document', 'chat-folder'],
  data() {
    return {
      hoverFolderId: null
    };
  },
  methods: {
    promptNewFolder() {
      const name = prompt('Nombre de la nueva carpeta:');
      if (name && name.trim()) {
        this.$emit('new', name.trim());
      }
    },
    onDragEnter(folderId, e) {
      e.preventDefault();
      this.hoverFolderId = folderId;
    },
    onDragLeave(folderId, e) {
      e.preventDefault();
      if (this.hoverFolderId === folderId) this.hoverFolderId = null;
    },
    onDrop(folderId, e) {
      e.preventDefault();
      const docId = e.dataTransfer.getData('text/plain');
      this.hoverFolderId = null;
      if (docId) this.$emit('drop', { docId: Number(docId), folderId });
    }
  }
};
</script>

<style scoped>
.folder-list {
  padding: 12px;
  border-bottom: 1px solid #2a3152;
}

.folder-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
}

.add-folder-btn {
  background: transparent;
  border: 1px solid #2a3152;
  color: #9ca3af;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.folders {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.folder-item:hover { background: #1e2640; }
.folder-item.active { background: #1e2640; border-left: 3px solid #4d6cfa; }

.folder-icon { font-size: 16px; }
.folder-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-folder-btn {
  background: transparent;
  border: 1px solid #4d6cfa;
  color: #4d6cfa;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}
.chat-folder-btn:hover {
  background: #4d6cfa;
  color: white;
}
.del-btn { background: transparent; border: none; color: #6b7280; cursor: pointer; }

.empty-folders { color: #6b7280; padding: 8px 0; }

.folder-item.drag-over {
  background: #24304f;
  border-left-color: #6fb0ff;
}

.folder-chevron { margin-right: 6px; color: #9ca3af; }
.folder-docs { margin-left: 20px; margin-top: 6px; display: flex; flex-direction: column; gap: 6px; }
.folder-doc-item { display:flex; gap:8px; align-items:center; padding:6px 8px; border-radius:6px; cursor:pointer; }
.folder-doc-item:hover { background:#1e2640; }
.doc-icon { font-size:14px; }
.doc-name { color:#e4e6eb; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.empty-folder-docs { color:#6b7280; padding:6px 8px; }
</style>