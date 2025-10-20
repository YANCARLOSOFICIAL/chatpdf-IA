<template>
  <div 
    class="message"
    :class="message.role"
  >
    <div class="message-avatar">
      {{ message.role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="message-bubble">
      <div class="message-text" v-html="formattedContent"></div>
      <div v-if="message.role === 'assistant' && (message.usedVlmEnhanced || (message.imagesAnalyzed && message.imagesAnalyzed.length>0))" class="vlm-meta">
        <button class="vlm-badge" @click="$emit('open-image', message.imagesAnalyzed[0])">🖼️ Visión usada</button>
        <span class="vlm-pages">Páginas analizadas: 
          <a v-for="(p, idx) in message.imagesAnalyzed" :key="p" href="#" @click.prevent="$emit('open-image', p)">{{ p }}<span v-if="idx < message.imagesAnalyzed.length-1">, </span></a>
        </span>
      </div>
      <!-- Evidence/Source links -->
      <div v-if="message.role === 'assistant' && message.sources && message.sources.length > 0" class="sources-container">
        <div class="sources-title">📚 Fuentes:</div>
        <div class="sources-list">
          <button 
            v-for="(source, idx) in message.sources" 
            :key="idx"
            class="source-item"
            @click="$emit('go-to-source', source)"
            :title="source.preview"
          >
            <span class="source-icon">📄</span>
            <span class="source-label">
              <span v-if="source.page">Pág. {{ source.page }}</span>
              <span v-else>Fragmento {{ idx + 1 }}</span>
            </span>
          </button>
        </div>
      </div>
      <div class="message-footer">
        <div class="message-time">{{ formattedTime }}</div>
        <button 
          v-if="message.role === 'assistant'" 
          class="copy-btn"
          @click="$emit('copy', message.content)"
          :class="{ 'copied': isCopied }"
          :title="isCopied ? 'Copiado!' : 'Copiar mensaje'"
        >
          {{ isCopied ? '✓' : '📋' }}
        </button>
        <button 
          v-if="message.role === 'assistant' && showRegenerateBtn" 
          class="regenerate-btn"
          @click="$emit('regenerate')"
          title="Regenerar respuesta"
        >
          🔄
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Configurar marked para mejor renderizado
marked.setOptions({
  breaks: true, // Convertir \n en <br>
  gfm: true, // GitHub Flavored Markdown
  headerIds: false,
  mangle: false
});

export default {
  name: 'ChatMessage',
  props: {
    message: {
      type: Object,
      required: true
    },
    isCopied: {
      type: Boolean,
      default: false
    },
    showRegenerateBtn: {
      type: Boolean,
      default: false
    }
  },
  emits: ['copy', 'regenerate', 'go-to-source'],
  computed: {
    formattedTime() {
      if (!this.message.timestamp) return '';
      const date = new Date(this.message.timestamp);
      return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    },
    formattedContent() {
      try {
        // Convertir markdown a HTML usando marked
        const html = marked.parse(this.message.content || '');
        // Sanitizar HTML para prevenir XSS (si DOMPurify está disponible)
        if (typeof DOMPurify !== 'undefined' && DOMPurify.sanitize) {
          return DOMPurify.sanitize(html);
        }
        return html;
      } catch (error) {
        console.error('Error parsing markdown:', error);
        // Fallback a texto plano
        return this.message.content.replace(/\n/g, '<br>');
      }
    }
  }
};
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
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
  max-width: 70%;
}

.message-text {
  padding: 12px 16px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  color: #e4e6eb;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
}

.message-text :deep(strong) {
  font-weight: 700;
  color: #fff;
}

.message-text :deep(em) {
  font-style: italic;
}

.message-text :deep(code) {
  background: #0a0e27;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

/* Bloques de código */
.message-text :deep(pre) {
  background: #0a0e27;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid #1e2640;
}

.message-text :deep(pre code) {
  background: transparent;
  padding: 0;
  font-size: 13px;
  line-height: 1.5;
}

/* Listas */
.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.message-text :deep(li) {
  margin: 4px 0;
}

/* Enlaces */
.message-text :deep(a) {
  color: #4d6cfa;
  text-decoration: underline;
  transition: color 0.2s;
}

.message-text :deep(a:hover) {
  color: #5a7bff;
}

/* Tablas */
.message-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid #2a3152;
  padding: 8px;
  text-align: left;
}

.message-text :deep(th) {
  background: #1e2640;
  font-weight: 600;
}

/* Citas */
.message-text :deep(blockquote) {
  border-left: 3px solid #4d6cfa;
  padding-left: 12px;
  margin: 8px 0;
  color: #9ca3af;
  font-style: italic;
}

/* Párrafos */
.message-text :deep(p) {
  margin: 8px 0;
}

.message-text :deep(p:first-child) {
  margin-top: 0;
}

.message-text :deep(p:last-child) {
  margin-bottom: 0;
}

.message.user .message-text {
  background: #4d6cfa;
  border-color: #5a7bff;
  color: white;
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
}

.message.user .message-footer {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.message-time {
  font-size: 12px;
  color: #6b7280;
}

.copy-btn,
.regenerate-btn {
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

.message:hover .copy-btn,
.message:hover .regenerate-btn {
  opacity: 1;
}

.copy-btn:hover,
.regenerate-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
  transform: scale(1.05);
}

.copy-btn.copied {
  color: #10b981;
  border-color: #10b981;
  opacity: 1;
}

.regenerate-btn:active {
  animation: spin 0.5s ease-in-out;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Light mode */
:global(#app.light-mode) .message-avatar {
  background: #f7fafc;
}

:global(#app.light-mode) .message-text {
  background: #ffffff;
  border-color: #e2e8f0;
  color: #1a202c;
}

:global(#app.light-mode) .message-text :deep(code) {
  background: #f7fafc;
}

:global(#app.light-mode) .message.user .message-text {
  background: #4d6cfa;
  color: white;
}

:global(#app.light-mode) .message-time {
  color: #718096;
}

:global(#app.light-mode) .copy-btn,
:global(#app.light-mode) .regenerate-btn {
  border-color: #e2e8f0;
  color: #4a5568;
}

:global(#app.light-mode) .copy-btn:hover,
:global(#app.light-mode) .regenerate-btn:hover {
  background: #f7fafc;
}

/* Sources styling */
.sources-container {
  margin-top: 12px;
  padding: 12px;
  background: rgba(77, 108, 250, 0.05);
  border: 1px solid #2a3152;
  border-radius: 8px;
}

.sources-title {
  font-size: 12px;
  font-weight: 600;
  color: #9ca3af;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sources-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 6px;
  color: #e4e6eb;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.source-item:hover {
  background: #2a3152;
  border-color: #4d6cfa;
  color: #4d6cfa;
  transform: translateY(-1px);
}

.source-icon {
  font-size: 14px;
}

.source-label {
  font-weight: 500;
}

:global(#app.light-mode) .sources-container {
  background: rgba(77, 108, 250, 0.05);
  border-color: #e2e8f0;
}

:global(#app.light-mode) .sources-title {
  color: #718096;
}

:global(#app.light-mode) .source-item {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #1a202c;
}

:global(#app.light-mode) .source-item:hover {
  background: #edf2f7;
  border-color: #4d6cfa;
  color: #4d6cfa;
}

.vlm-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px;
  background: rgba(77, 108, 250, 0.08);
  border-radius: 6px;
  font-size: 13px;
}

.vlm-badge {
  padding: 4px 10px;
  background: #4d6cfa;
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.vlm-pages {
  color: #9ca3af;
  font-size: 12px;
}

.vlm-pages a {
  color: #4d6cfa;
  text-decoration: none;
  font-weight: 500;
}

.vlm-pages a:hover {
  text-decoration: underline;
}
</style>
