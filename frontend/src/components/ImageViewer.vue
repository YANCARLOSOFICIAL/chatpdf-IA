<template>
  <div v-if="visible" class="image-viewer-overlay" @click.self="close">
    <div class="image-viewer-content">
      <button class="close" @click="close">✕</button>
      <button v-if="page && page > 1" class="nav-btn prev" @click.stop="goto(page - 1)">◀</button>
      <img :src="computedSrc" alt="Página del PDF" @error="onError" />
      <button v-if="page" class="nav-btn next" @click.stop="goto(page + 1)">▶</button>
      <div class="caption">Página {{ page }}</div>
      <div v-if="error" class="error-msg">{{ error }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ImageViewer',
  props: {
    visible: { type: Boolean, default: false },
    src: { type: String, default: '' },
    page: { type: Number, default: null },
    pdfId: { type: [Number, String], required: false }
  },
  emits: ['close', 'navigate'],
  data() {
    return { error: null }
  },
  computed: {
    computedSrc() {
      if (this.src) return this.src
      if (!this.pdfId || !this.page) return ''
      try {
        const base = require('../config').default.API_BASE_URL || 'http://localhost:8000'
        return `${base}/pdfs/${this.pdfId}/images/${this.page}`
      } catch (e) {
        return `/pdfs/${this.pdfId}/images/${this.page}`
      }
    }
  },
  methods: {
    close() {
      this.$emit('close')
    },
    goto(p) {
      this.error = null
      this.$emit('navigate', p)
    },
    onError() {
      this.error = 'No se pudo cargar la imagen. Puede que no exista para esta página.'
    }
  }
}
</script>

<style scoped>
.image-viewer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.image-viewer-content {
  position: relative;
  background: #0b0f1a;
  padding: 16px;
  border-radius: 8px;
  max-width: 90%;
  max-height: 90%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.image-viewer-content img {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 6px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.6);
}
.image-viewer-content .caption {
  margin-top: 8px;
  color: #cbd5e1;
}
.close {
  position: absolute;
  top: 8px;
  right: 8px;
  background: transparent;
  border: none;
  color: #cbd5e1;
  font-size: 18px;
  cursor: pointer;
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(0,0,0,0.5);
  color: #fff;
  border: none;
  padding: 8px 10px;
  cursor: pointer;
  border-radius: 4px;
}
.nav-btn.prev { left: 8px }
.nav-btn.next { right: 8px }

.error-msg { color: #ff7b7b; margin-top: 8px }
</style>