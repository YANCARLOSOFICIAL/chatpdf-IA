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
        <div class="sources-title">📚 Referencias:</div>
        <div class="sources-list">
          <div 
            v-for="(source, idx) in message.sources" 
            :key="idx"
            class="source-item-wrapper"
          >
            <button 
              class="source-item"
              @click="$emit('go-to-source', source)"
              :title="`${source.preview}\n\nHaz clic para navegar a esta página`"
            >
              <span class="source-icon">�</span>
              <span class="source-label">
                <span class="source-main">
                  <span v-if="source.page">Página {{ source.page }}</span>
                  <span v-else>Referencia {{ idx + 1 }}</span>
                </span>
                <span v-if="source.location" class="location-badge">{{ source.location }}</span>
              </span>
            </button>
            <!-- Mostrar preview en hover/tooltip -->
            <div class="source-tooltip">
              <div class="preview-text">{{ source.preview }}</div>
            </div>
          </div>
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
        let html = marked.parse(this.message.content || '');
        
        // Convertir referencias [1], [2], etc. en superíndices clicables
        html = html.replace(/\[(\d+)\]/g, '<sup class="citation-ref" data-source-index="$1">[$1]</sup>');
        
        // Sanitizar HTML para prevenir XSS (si DOMPurify está disponible)
        if (typeof DOMPurify !== 'undefined' && DOMPurify.sanitize) {
          return DOMPurify.sanitize(html, { ADD_ATTR: ['data-source-index'] });
        }
        return html;
      } catch (error) {
        console.error('Error parsing markdown:', error);
        // Fallback a texto plano con conversión de referencias
        let content = this.message.content.replace(/\n/g, '<br>');
        content = content.replace(/\[(\d+)\]/g, '<sup class="citation-ref" data-source-index="$1">[$1]</sup>');
        return content;
      }
    }
  },
  mounted() {
    // Añadir event listener para clics en las referencias inline
    this.$el.addEventListener('click', (event) => {
      const target = event.target;
      if (target.classList.contains('citation-ref')) {
        const sourceIndex = parseInt(target.dataset.sourceIndex, 10);
        if (sourceIndex && this.message.sources && this.message.sources[sourceIndex - 1]) {
          // Scroll suave a la referencia correspondiente
          const sourcesContainer = this.$el.querySelector('.sources-container');
          if (sourcesContainer) {
            const sourceItems = sourcesContainer.querySelectorAll('.source-item');
            if (sourceItems[sourceIndex - 1]) {
              sourceItems[sourceIndex - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
              // Efecto visual temporal
              sourceItems[sourceIndex - 1].classList.add('citation-highlight');
              setTimeout(() => {
                sourceItems[sourceIndex - 1].classList.remove('citation-highlight');
              }, 1500);
            }
          }
        }
      }
    });
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

/* Referencias inline [1], [2], etc. */
.message-text :deep(.citation-ref) {
  color: #4d6cfa;
  cursor: pointer;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
  padding: 0 2px;
  margin: 0 1px;
  position: relative;
  font-size: 0.75em;
  vertical-align: super;
  line-height: 0;
}

.message-text :deep(.citation-ref:hover) {
  color: #5a7bff;
  text-shadow: 0 0 8px rgba(77, 108, 250, 0.5);
  transform: scale(1.1);
}

.message-text :deep(.citation-ref:active) {
  transform: scale(0.95);
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
  gap: 8px;
}

.source-item-wrapper {
  position: relative;
  display: inline-block;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: linear-gradient(135deg, #1e2640 0%, #2a3152 100%);
  border: 1.5px solid #4d6cfa;
  border-radius: 8px;
  color: #e4e6eb;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 4px rgba(77, 108, 250, 0.1);
}

.source-item:hover {
  background: linear-gradient(135deg, #2a3152 0%, #3a4562 100%);
  border-color: #7b8fff;
  color: #7b8fff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(77, 108, 250, 0.2);
}

/* Highlight temporal al hacer clic en referencia inline */
.source-item.citation-highlight {
  animation: citationPulse 1.5s ease-out;
}

@keyframes citationPulse {
  0%, 100% {
    background: linear-gradient(135deg, #1e2640 0%, #2a3152 100%);
    border-color: #4d6cfa;
    box-shadow: 0 2px 4px rgba(77, 108, 250, 0.1);
  }
  50% {
    background: linear-gradient(135deg, #4d6cfa 0%, #5a7bff 100%);
    border-color: #7b8fff;
    box-shadow: 0 0 20px rgba(77, 108, 250, 0.6);
    transform: scale(1.05);
  }
}


.source-icon {
  font-size: 14px;
}

.source-label {
  font-weight: 500;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.source-main {
  font-size: 13px;
  font-weight: 600;
}

.location-badge {
  font-size: 11px;
  opacity: 0.7;
  font-weight: 400;
  color: #9ca3af;
}

/* Tooltip que aparece al pasar el mouse */
.source-tooltip {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  background: #0a0e27;
  border: 1px solid #4d6cfa;
  border-radius: 6px;
  padding: 10px 12px;
  z-index: 1000;
  white-space: normal;
  width: 280px;
  max-height: 150px;
  overflow-y: auto;
  transition: opacity 0.3s, visibility 0.3s;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  pointer-events: none;
}

.source-item-wrapper:hover .source-tooltip {
  visibility: visible;
  opacity: 1;
}

.preview-text {
  font-size: 12px;
  color: #e4e6eb;
  line-height: 1.4;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Arrow del tooltip */
.source-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: #4d6cfa transparent transparent transparent;
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

:global(#app.light-mode) .source-tooltip {
  background: #ffffff;
  border-color: #4d6cfa;
}

:global(#app.light-mode) .preview-text {
  color: #1a202c;
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
