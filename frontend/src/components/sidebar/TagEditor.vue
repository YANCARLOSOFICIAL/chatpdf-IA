<template>
  <div v-if="visible" class="tag-editor-backdrop" @click.self="close">
    <div class="tag-editor">
      <div class="header">
        <h3>Editar etiquetas</h3>
        <button class="close" @click="close">✕</button>
      </div>

      <div class="content">
        <div class="existing-tags">
          <span v-for="(tag, idx) in tags" :key="idx" class="tag-chip">
            {{ tag }}
            <button class="x" @click="removeTag(idx)">✕</button>
          </span>
        </div>

        <div class="add-area">
          <input v-model="newTag" @keyup.enter="addTag" placeholder="Agregar etiqueta y presionar Enter" />
          <button @click="addTag">Agregar</button>
        </div>

        <div class="suggestions">
          <h4>Sugerencias</h4>
          <div class="suggestion-list">
            <button v-for="s in suggestions" :key="s" class="suggestion" @click="addSuggested(s)"># {{ s }}</button>
          </div>
        </div>
      </div>

      <div class="actions">
        <button class="btn" @click="save">Guardar</button>
        <button class="btn ghost" @click="close">Cancelar</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TagEditor',
  props: {
    visible: { type: Boolean, default: false },
    initialTags: { type: Array, default: () => [] }
  },
  emits: ['close', 'save'],
  data() {
    return {
      tags: [...this.initialTags],
      newTag: '',
      suggestions: ['important', 'review', 'invoice', 'research']
    };
  },
  methods: {
    addTag() {
      const t = this.newTag.trim();
      if (!t) return;
      if (!this.tags.includes(t)) this.tags.push(t);
      this.newTag = '';
    },
    addSuggested(s) {
      if (!this.tags.includes(s)) this.tags.push(s);
    },
    removeTag(idx) {
      this.tags.splice(idx, 1);
    },
    save() {
      this.$emit('save', this.tags);
      this.close();
    },
    close() {
      this.$emit('close');
    }
  }
};
</script>

<style scoped>
.tag-editor-backdrop {
  position: fixed;
  left: 0; right: 0; top: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.tag-editor {
  width: 420px;
  background: #0a0e27;
  border: 1px solid #1e2640;
  border-radius: 12px;
  padding: 12px;
}
.header { display:flex; align-items:center; justify-content:space-between; }
.header h3 { margin:0; }
.header .close { background:transparent; border:none; color:#9ca3af; cursor:pointer; }
.content { margin-top:12px; }
.existing-tags { display:flex; gap:8px; flex-wrap:wrap; }
.tag-chip { background:#151934; padding:6px 8px; border-radius:999px; display:flex; gap:8px; align-items:center; }
.tag-chip .x { background:transparent; border:none; color:#9ca3af; cursor:pointer; }
.add-area { display:flex; gap:8px; margin-top:12px; }
.add-area input { flex:1; padding:8px; border-radius:8px; border:1px solid #2a3152; background:#071029; color:#e4e6eb; }
.add-area button { padding:8px 12px; border-radius:8px; border:1px solid #2a3152; background:#1e2640; color:#e4e6eb; }
.suggestions { margin-top:12px; }
.suggestion-list { display:flex; gap:8px; flex-wrap:wrap; }
.suggestion { background:transparent; border:1px solid #2a3152; padding:6px 8px; border-radius:8px; color:#9ca3af; cursor:pointer; }
.actions { display:flex; gap:8px; justify-content:flex-end; margin-top:12px; }
.btn { padding:8px 12px; border-radius:8px; background:#4d6cfa; border:none; color:white; }
.btn.ghost { background:transparent; border:1px solid #2a3152; color:#9ca3af; }
</style>