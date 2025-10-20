<template>
  <div class="pdf-viewer-root">
    <!-- Modal mode: overlay -->
    <div v-if="mode === 'modal' && visible" class="pdf-viewer-overlay" @click.self="close">
      <div class="pdf-viewer-content modal">
        <button class="close" @click="close">✕</button>
        <div class="controls">
          <button @click="prevPage" :disabled="page<=1">◀ Anterior</button>
          <span>Página {{ page }} / {{ totalPages }}</span>
          <button @click="nextPage" :disabled="page>=totalPages">Siguiente ▶</button>
          <button @click="zoomIn">🔍+</button>
          <button @click="zoomOut">🔍−</button>
          <button @click="resetZoom">100%</button>
        </div>
        <div class="canvas-container">
          <canvas ref="canvas"></canvas>
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
      </div>
    </div>

    <!-- Embedded mode: render inline (for left pane) -->
    <div v-if="mode === 'embedded'" class="pdf-embedded">
      <div class="embedded-controls">
        <button @click="prevPage" :disabled="page<=1" class="nav-btn">◀</button>
        <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
        <button @click="nextPage" :disabled="page>=totalPages" class="nav-btn">▶</button>
        <div class="spacer"></div>
        <button @click="zoomOut" class="zoom-btn" title="Reducir">−</button>
        <span class="zoom-indicator">{{ Math.round(scale * 100) }}%</span>
        <button @click="zoomIn" class="zoom-btn" title="Ampliar">+</button>
        <button @click="resetZoom" class="zoom-btn" title="Tamaño original">100%</button>
      </div>
      <div class="embedded-canvas-container" ref="canvasContainer">
        <canvas ref="canvasEmbedded"></canvas>
        <!-- Highlight overlay (transient) -->
        <div v-if="_highlight && _highlight.visible" class="highlight-overlay" :style="_highlight.style">
          <div class="highlight-box" />
          <div class="highlight-tooltip">{{ _highlight.text }}</div>
        </div>
      </div>
      <div v-if="error" class="error-msg">{{ error }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PdfViewer',
  props: {
    visible: { type: Boolean, default: false },
    pdfUrl: { type: String, default: '' },
    startPage: { type: Number, default: 1 },
    mode: { type: String, default: 'modal' }
  },
  emits: ['close'],
  data() {
    return { 
      pdfDoc: null,
      page: this.startPage,
      totalPages: 0,
      scale: 1.0,
      error: null,
      _imageMode: false,
      _imageList: null,
      _resizeObserver: null,
      _currentPageDimensions: null,
      // highlight state for quick visual cue when jumping to sources
      _highlight: {
        visible: false,
        style: {},
        text: ''
      }
    }
  },
  watch: {
    visible(n) {
      if (n && this.mode === 'modal') this.open();
      if (!n && this.mode === 'modal') this.cleanup();
    },
    pdfUrl(n) {
      // When the parent changes the pdf URL (selecting a new document), reset and open
      if (!n) return;
      try {
        this.cleanup();
      } catch (e) {}
      // reset minimal state
      this.pdfDoc = null;
      this.totalPages = 0;
      this.page = this.startPage || 1;
      this._imageMode = false;
      // attempt to open the new URL
      this.open();
      // ensure resize observer is active for embedded mode
      if (this.mode === 'embedded') this.setupResizeObserver();
    },
    startPage(v) { 
      this.page = v;
      if (this.pdfDoc || this._imageMode) this.renderPage();
    },
    scale() {
      if (this.pdfDoc || this._imageMode) this.renderPage();
    }
  },
  mounted() {
    if (this.mode === 'embedded') {
      this.open();
      this.setupResizeObserver();
    }
  },
  beforeUnmount() {
    this.cleanup();
  },
  methods: {
    setupResizeObserver() {
      const container = this.$refs.canvasContainer;
      if (!container || !window.ResizeObserver) return;
      
      this._resizeObserver = new ResizeObserver(() => {
        this.autoFitToContainer();
      });
      this._resizeObserver.observe(container);
    },

    async open() {
      this.error = null;
      
      // Strategy 1: Try image-first (more reliable rendering)
      try {
        const m = String(this.pdfUrl).match(/\/pdfs\/(\d+)\/file/);
        if (m) {
          const id = m[1];
          const infoRes = await fetch(`${new URL(this.pdfUrl).origin}/pdfs/${id}/info`);
          if (infoRes.ok) {
            const info = await infoRes.json();
            if (info && Array.isArray(info.images) && info.images.length > 0) {
              this._imageMode = true;
              this._imageList = info.images.sort((a,b)=> (a.page||0)-(b.page||0));
              this.totalPages = info.pages || info.images.length;
              this.page = Math.max(1, Math.min(this.startPage || 1, this.totalPages));
              await this.renderPage();
              return;
            }
            // diagnostic: info present but no images/pages
            console.info('PdfViewer.info returned but no images:', info);
          }
        }
      } catch (e) {
        console.info('Image-first unavailable, trying PDF.js', e);
      }

      // Strategy 2: PDF.js fallback
      try {
        if (!window['pdfjsLib']) {
          await new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.14.305/pdf.min.js';
            s.onload = () => resolve();
            s.onerror = () => reject(new Error('Failed to load PDF.js'));
            document.head.appendChild(s);
          });
        }
        
        const pdfjsLib = window['pdfjsLib'];
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.14.305/pdf.worker.min.js';
        
        if (!this.pdfUrl) {
          this.error = 'No PDF URL provided';
          return;
        }

        const resp = await fetch(this.pdfUrl);
        if (!resp.ok) {
          // Try to extract some body text for debugging (e.g., HTML error page)
          let bodyText = '';
          try { bodyText = await resp.text(); } catch (e) { bodyText = ''; }
          const snippet = bodyText ? (bodyText.substring(0, 300) + (bodyText.length>300? '...':'')) : '';
          const msg = `Failed to fetch PDF: ${resp.status} ${resp.statusText} ${snippet}`;
          console.warn(msg);
          throw new Error(msg);
        }
        const arrayBuffer = await resp.arrayBuffer();
        
        const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer, disableWorker: true });
        this.pdfDoc = await loadingTask.promise;
        this.totalPages = this.pdfDoc.numPages;
        this.page = Math.max(1, Math.min(this.startPage || 1, this.totalPages));
        this._imageMode = false;
        await this.renderPage();
      } catch (e) {
        console.error('PDF.js error', e);
        this.error = e.message || 'Error loading PDF';
      }
    },

    async renderPage() {
      if (this._imageMode) {
        await this.renderImagePage();
      } else if (this.pdfDoc) {
        await this.renderPdfPage();
      }
    },

    async renderImagePage() {
      try {
        const m = String(this.pdfUrl).match(/\/pdfs\/(\d+)\/file/);
        if (!m) throw new Error('Could not extract pdf id');
        const id = m[1];
        
        const pdfOrigin = (new URL(String(this.pdfUrl))).origin;
        const imageUrl = `${pdfOrigin}/pdfs/${id}/images/${this.page}`;
        
        const resp = await fetch(imageUrl);
        if (!resp.ok) throw new Error('Image not available');
        const blob = await resp.blob();
        const bitmap = await createImageBitmap(blob);
        
        const canvas = this.mode === 'embedded' ? this.$refs.canvasEmbedded : this.$refs.canvas;
        if (!canvas) return;

        // Store original dimensions for auto-fit
        this._currentPageDimensions = { width: bitmap.width, height: bitmap.height };
        
        // Calculate render dimensions
        const renderWidth = bitmap.width * this.scale;
        const renderHeight = bitmap.height * this.scale;
        
        const DPR = window.devicePixelRatio || 1;
        canvas.width = Math.round(renderWidth * DPR);
        canvas.height = Math.round(renderHeight * DPR);
        canvas.style.width = `${Math.round(renderWidth)}px`;
        canvas.style.height = `${Math.round(renderHeight)}px`;
        
        const ctx = canvas.getContext('2d');
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        ctx.clearRect(0, 0, renderWidth, renderHeight);
        ctx.drawImage(bitmap, 0, 0, renderWidth, renderHeight);
        
        this.error = null;
      } catch (e) {
        console.error('Image render error', e);
        this.error = 'Error rendering page image';
      }
    },

    async renderPdfPage() {
      if (!this.pdfDoc) return;
      try {
        const pageObj = await this.pdfDoc.getPage(this.page);
        const viewport = pageObj.getViewport({ scale: this.scale });
        
        // Store original dimensions for auto-fit
        this._currentPageDimensions = { width: viewport.width, height: viewport.height };
        
        const canvas = this.mode === 'embedded' ? this.$refs.canvasEmbedded : this.$refs.canvas;
        if (!canvas) return;

        const DPR = window.devicePixelRatio || 1;
        canvas.width = Math.round(viewport.width * DPR);
        canvas.height = Math.round(viewport.height * DPR);
        canvas.style.width = `${Math.round(viewport.width)}px`;
        canvas.style.height = `${Math.round(viewport.height)}px`;
        
        const ctx = canvas.getContext('2d');
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        
        const renderContext = { canvasContext: ctx, viewport };
        await pageObj.render(renderContext).promise;
        
        this.error = null;
      } catch (e) {
        console.error('PDF render error', e);
        // Try image fallback
        if (!this._imageMode) {
          this._imageMode = true;
          await this.renderImagePage();
        } else {
          this.error = 'Error rendering page';
        }
      }
    },

    autoFitToContainer() {
      if (!this._currentPageDimensions) return;
      
      const container = this.mode === 'embedded' ? this.$refs.canvasContainer : null;
      if (!container) return;
      
      const containerWidth = container.clientWidth - 40; // padding
      const containerHeight = container.clientHeight - 40;
      
      const pageWidth = this._currentPageDimensions.width;
      const pageHeight = this._currentPageDimensions.height;
      
      // Calculate scale to fit width
      const scaleToFitWidth = containerWidth / pageWidth;
      const scaleToFitHeight = containerHeight / pageHeight;
      
      // Use the smaller scale to ensure it fits both dimensions
      const newScale = Math.min(scaleToFitWidth, scaleToFitHeight, 2.5);
      
      if (Math.abs(this.scale - newScale) > 0.05) {
        this.scale = Math.max(0.3, newScale);
      }
    },

    prevPage() {
      if (this.page <= 1) return;
      this.page--;
      this.renderPage();
    },
    
    nextPage() {
      if (this.page >= this.totalPages) return;
      this.page++;
      this.renderPage();
    },

    zoomIn() {
      this.scale = Math.min(this.scale + 0.25, 3.0);
    },

    zoomOut() {
      this.scale = Math.max(this.scale - 0.25, 0.3);
    },

    resetZoom() {
      this.scale = 1.0;
    },

    // Public method to jump to specific page
    goToPage(pageNum) {
      if (pageNum >= 1 && pageNum <= this.totalPages) {
        this.page = pageNum;
        this.renderPage();
      }
    },

    // Highlight a source: navigate to page and show a pulsing overlay with preview text
    async highlightSource(source) {
      try {
        if (!source || !source.page) return;
        // Navigate to page
        this.page = source.page;
        await this.renderPage();

        // Find canvas and its container to position overlay
        const canvas = this.mode === 'embedded' ? this.$refs.canvasEmbedded : this.$refs.canvas;
        const container = this.mode === 'embedded' ? this.$refs.canvasContainer : this.$el.querySelector('.canvas-container');
        if (!canvas || !container) return;

        const rect = canvas.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();

        // If backend provided coords (PDF-space), compute precise CSS pixel box
        if (source.coords && this._currentPageDimensions) {
          try {
            // _currentPageDimensions.width/height are page units (PDF points or image px)
            const pageW = this._currentPageDimensions.width;
            const pageH = this._currentPageDimensions.height;

            // CSS width/height of rendered canvas
            const cssW = rect.width;
            const cssH = rect.height;

            // scale from PDF units to CSS pixels
            const scaleX = cssW / pageW;
            const scaleY = cssH / pageH;

            // coords from backend: x,y,w,h
            const cx = source.coords.x || 0;
            const cy = source.coords.y || 0;
            const cw = source.coords.w || 0;
            const ch = source.coords.h || 0;

            // Convert to CSS pixels
            const left = rect.left - containerRect.left + cx * scaleX;
            const top = rect.top - containerRect.top + cy * scaleY;
            const width = Math.max(6, cw * scaleX);
            const height = Math.max(6, ch * scaleY);

            this._setHighlight({ left, top, width, height, text: source.preview || '' });
            return;
          } catch (e) {
            console.warn('Failed to render precise coords, falling back to approximate overlay', e);
          }
        }

        // Fallback: approximate centered pulsing overlay
        // Default highlight box size (in CSS pixels)
        const boxWidth = Math.min(rect.width * 0.8, 800);
        const boxHeight = Math.min(rect.height * 0.25, 300);

        // Position centered horizontally, at 30% from top to emulate content position
        const left = rect.left + (rect.width - boxWidth) / 2 - containerRect.left;
        const top = rect.top + (rect.height * 0.3) - (boxHeight / 2) - containerRect.top;

        this._setHighlight({ left, top, width: boxWidth, height: boxHeight, text: source.preview || '' });
      } catch (e) {
        console.error('highlightSource failed', e);
      }
    },

    _setHighlight({ left, top, width, height, text }) {
      // Create reactive highlight state on the component
      this.$data._highlight = this.$data._highlight || { visible: false, style: {}, text: '' };
      this.$data._highlight.style = { left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` };
      this.$data._highlight.text = text || '';
      this.$data._highlight.visible = true;
      // Auto-hide after 3.5s
      if (this.$data._highlight._timeout) clearTimeout(this.$data._highlight._timeout);
      this.$data._highlight._timeout = setTimeout(() => {
        this.$data._highlight.visible = false;
      }, 3500);
    },

    close() {
      this.$emit('close');
    },

    cleanup() {
      if (this._resizeObserver) {
        this._resizeObserver.disconnect();
        this._resizeObserver = null;
      }
      this.pdfDoc = null;
      this._imageMode = false;
      this._imageList = null;
      this._currentPageDimensions = null;
      this.error = null;
    }
  }
}
</script>

<style scoped>
.pdf-viewer-root {
  width: 100%;
  height: 100%;
}

/* Modal overlay */
.pdf-viewer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 3000;
  backdrop-filter: blur(4px);
}

.pdf-viewer-content {
  background: #0b0f1a;
  padding: 20px;
  border-radius: 12px;
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
}

.close {
  position: absolute;
  right: 16px;
  top: 16px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #fff;
  font-size: 24px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.close:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

.controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  flex-wrap: wrap;
}

.controls button {
  padding: 8px 16px;
  background: #4d6cfa;
  border: none;
  border-radius: 6px;
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.controls button:hover:not(:disabled) {
  background: #5a7bff;
  transform: translateY(-1px);
}

.controls button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.canvas-container {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1f36;
  border-radius: 8px;
  padding: 20px;
}

canvas {
  display: block;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  max-width: 100%;
  height: auto;
}

/* Embedded mode */
.pdf-embedded {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0e27;
}

.embedded-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #151934;
  border-bottom: 1px solid #1e2640;
  flex-shrink: 0;
}

.nav-btn, .zoom-btn {
  background: transparent;
  border: 1px solid #2a3152;
  color: #e4e6eb;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  min-width: 36px;
}

.nav-btn:hover:not(:disabled), .zoom-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-indicator, .zoom-indicator {
  color: #9ca3af;
  font-size: 13px;
  font-weight: 500;
  padding: 0 8px;
  white-space: nowrap;
}

.spacer {
  flex: 1;
}

.embedded-canvas-container {
  flex: 1;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: #0a0e27;
  padding: 20px;
  position: relative;
}

.embedded-canvas-container canvas {
  display: block;
  max-width: 100%;
  height: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

/* Highlight overlay used for quick visual cue when navigating to a source */
.highlight-overlay {
  position: absolute;
  pointer-events: none;
  z-index: 1500;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.highlight-box {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(77,108,250,0.95);
  box-shadow: 0 8px 30px rgba(77,108,250,0.12);
  border-radius: 6px;
  animation: highlightPulse 1.2s ease-out 0s 3;
}

.highlight-tooltip {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  background: rgba(13,18,40,0.95);
  color: #e6eefb;
  padding: 8px 12px;
  border-radius: 6px;
  max-width: 320px;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
  box-shadow: 0 6px 18px rgba(0,0,0,0.6);
  pointer-events: none;
}

@keyframes highlightPulse {
  0% { transform: scale(0.98); opacity: 0.0; }
  10% { transform: scale(1.02); opacity: 1.0; }
  60% { transform: scale(1.0); opacity: 0.9; }
  100% { transform: scale(1.0); opacity: 0.0; }
}

.error-msg {
  color: #ff7b7b;
  background: rgba(255, 123, 123, 0.1);
  padding: 12px 16px;
  border-radius: 6px;
  margin-top: 12px;
  font-size: 14px;
  text-align: center;
}

/* Scrollbar styling */
.canvas-container::-webkit-scrollbar,
.embedded-canvas-container::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.canvas-container::-webkit-scrollbar-track,
.embedded-canvas-container::-webkit-scrollbar-track {
  background: #0a0e27;
}

.canvas-container::-webkit-scrollbar-thumb,
.embedded-canvas-container::-webkit-scrollbar-thumb {
  background: #2a3152;
  border-radius: 4px;
}

.canvas-container::-webkit-scrollbar-thumb:hover,
.embedded-canvas-container::-webkit-scrollbar-thumb:hover {
  background: #4d6cfa;
}
</style>
