<template>
  <div>
    <!-- Modal mode: overlay -->
    <div v-if="mode === 'modal' && visible" class="pdf-viewer-overlay" @click.self="close">
      <div class="pdf-viewer-content modal">
        <button class="close" @click="close">✕</button>
        <div class="controls">
          <button @click="prevPage" :disabled="page<=1">Anterior</button>
          <span>Página {{ page }} / {{ totalPages }}</span>
          <button @click="nextPage" :disabled="page>=totalPages">Siguiente</button>
          <label>Zoom
            <input type="range" min="0.5" max="2.5" step="0.1" v-model.number="scale" />
          </label>
        </div>
        <div class="canvas-wrap">
          <canvas ref="canvas"></canvas>
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
      </div>
    </div>

    <!-- Embedded mode: render inline (for left pane) -->
    <div v-if="mode === 'embedded'" class="pdf-embedded">
      <div class="embedded-controls">
        <button @click="prevPage" :disabled="page<=1">◀</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button @click="nextPage" :disabled="page>=totalPages">▶</button>
        <button @click="fitWidth">Ajustar</button>
        <label style="margin-left:8px">Zoom
          <input type="range" min="0.5" max="2.5" step="0.1" v-model.number="scale" />
        </label>
      </div>
      <div class="embedded-canvas-wrap">
        <canvas ref="canvasEmbedded"></canvas>
      </div>
      <div v-if="error" class="error-msg">{{ error }}</div>
    </div>
  </div>
</template>

<script>
// Minimal PDF.js viewer using the pdfjs-dist UMD build via CDN
export default {
  name: 'PdfViewer',
  props: {
    visible: { type: Boolean, default: false },
    pdfUrl: { type: String, default: '' },
    startPage: { type: Number, default: 1 },
    mode: { type: String, default: 'modal' } // 'modal' or 'embedded'
  },
  emits: ['close'],
  data() {
    return { pdfDoc: null, page: this.startPage, totalPages: 0, scale: 1.0, error: null, _triedDisableWorker: false }
  },
  watch: {
    visible(n) {
      if (n && this.mode === 'modal') this.open();
      if (!n && this.mode === 'modal') this.cleanup();
    },
    startPage(v) { this.page = v }
  },
  mounted() {
    // If embedded mode, open on mount
    if (this.mode === 'embedded') this.open();
  },
  methods: {
    async open() {
      this.error = null;
      // Try image-first strategy: if server provided extracted images, render them directly
      try {
        const m = String(this.pdfUrl).match(/\/pdfs\/(\d+)\/file/);
        if (m) {
          const id = m[1];
          const infoRes = await fetch(`${new URL(this.pdfUrl).origin}/pdfs/${id}/info`);
          if (infoRes.ok) {
            const info = await infoRes.json();
            if (info && Array.isArray(info.images) && info.images.length > 0) {
              // Use image list to render pages
              this.totalPages = info.pages || info.images.length;
              this.page = Math.max(1, Math.min(this.startPage || 1, this.totalPages));
              this._imageList = info.images.sort((a,b)=> (a.page||0)-(b.page||0));
              // render the current page as image
              await this._renderImageFallback(this.page);
              return;
            }
          }
        }
      } catch (e) {
        // ignore and fallback to PDF.js
        console.info('Image-first check failed, falling back to PDF.js', e);
      }
      try {
        if (!window['pdfjsLib']) {
          await new Promise((resolve, reject) => {
        const s = document.createElement('script');
          // Use a stable 2.x PDF.js build (UMD) which is generally more compatible with the worker build
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
  // Fetch PDF bytes and provide ArrayBuffer to PDF.js to avoid worker/proxy issues
  const resp = await fetch(this.pdfUrl);
  if (!resp.ok) throw new Error(`Failed to fetch PDF: ${resp.status}`);
  const arrayBuffer = await resp.arrayBuffer();
  // Force disableWorker to avoid worker/runtime mismatches that can cause
  // 'Cannot read private member' errors in some environments.
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer, disableWorker: true });
  this.pdfDoc = await loadingTask.promise;
        this.totalPages = this.pdfDoc.numPages;
        this.page = Math.max(1, Math.min(this.startPage || 1, this.totalPages));
        this.renderPage();
      } catch (e) {
        console.error('PdfViewer open error', e);
        // If there was an error possibly caused by worker/class mismatch, retry without worker once
        if (!this._triedDisableWorker) {
          this._triedDisableWorker = true;
          try {
            console.info('Retrying PDF.js load with disableWorker=true using ArrayBuffer');
            const resp2 = await fetch(this.pdfUrl);
            if (!resp2.ok) throw new Error(`Failed to fetch PDF: ${resp2.status}`);
            const arrayBuffer2 = await resp2.arrayBuffer();
            const loadingTask2 = pdfjsLib.getDocument({ data: arrayBuffer2, disableWorker: true });
            this.pdfDoc = await loadingTask2.promise;
            this.totalPages = this.pdfDoc.numPages;
            this.page = Math.max(1, Math.min(this.startPage || 1, this.totalPages));
            this.renderPage();
            return;
          } catch (e2) {
            console.error('Retry without worker also failed', e2);
            this.error = e2.message || String(e2);
            return;
          }
        }
        this.error = e.message || String(e);
      }
    },

    // Public method to render current page as image when image-first mode is active
    async renderImagePage(pageNum) {
      try {
        await this._renderImageFallback(pageNum);
      } catch (e) {
        console.error('renderImagePage failed', e);
        throw e;
      }
    },
    async renderPage() {
      if (!this.pdfDoc) return;
      try {
        const pageObj = await this.pdfDoc.getPage(this.page);
        const viewport = pageObj.getViewport({ scale: this.scale });
        const canvas = this.mode === 'embedded' ? this.$refs.canvasEmbedded : this.$refs.canvas;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext('2d');
        const renderContext = { canvasContext: ctx, viewport };
        await pageObj.render(renderContext).promise;
      } catch (e) {
        console.error('Render page error', e);
        // Try fallback: if server exposes per-page images, render that image into the canvas
        try {
          await this._renderImageFallback(this.page);
          this.error = null;
          return;
        } catch (imgErr) {
          console.error('Image fallback also failed', imgErr);
        }
        this.error = 'Error rendering page';
      }
    },

    // Attempt to fetch /pdfs/{id}/images/{page} and draw onto canvas
    async _renderImageFallback(pageNum) {
      // extract pdf id from pdfUrl like /pdfs/{id}/file
      try {
        const m = String(this.pdfUrl).match(/\/pdfs\/(\d+)\/file/);
        if (!m) throw new Error('Could not extract pdf id from url');
        const id = m[1];
        // Build image URL using the same origin as the PDF URL (handles dev server origins)
        const pdfOrigin = (new URL(String(this.pdfUrl))).origin;
        const imageUrl = `${pdfOrigin}/pdfs/${id}/images/${pageNum}`;
        const resp = await fetch(imageUrl);
        if (!resp.ok) throw new Error('Image not available');
        const blob = await resp.blob();
        // Use createImageBitmap which is faster and avoids crossOrigin/image onerror quirks
        const bitmap = await createImageBitmap(blob);
        const canvas = this.mode === 'embedded' ? this.$refs.canvasEmbedded : this.$refs.canvas;
        // Preserve aspect ratio using bitmap dimensions
        canvas.width = Math.round(bitmap.width * this.scale);
        canvas.height = Math.round(bitmap.height * this.scale);
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        return true;
      } catch (e) {
        throw e;
      }
    },
    prevPage() {
      if (this.page <= 1) return; this.page--; this.renderPage();
    },
    nextPage() {
      if (this.page >= this.totalPages) return; this.page++; this.renderPage();
    },
    fitWidth() {
      // approximate fit width by setting scale to 1.0 and re-render
      this.scale = 1.0; this.renderPage();
    },
    close() { this.$emit('close') },
    cleanup() {
      try { this.pdfDoc = null; } catch (e) {}
      this.error = null;
    }
  }
}
</script>

<style scoped>
.pdf-viewer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; z-index:3000 }
.pdf-viewer-content { background: #0b0f1a; padding: 12px; border-radius:8px; width: 90%; max-height: 90%; display:flex; flex-direction:column; align-items:center }
.pdf-viewer-content .controls { display:flex; gap:12px; align-items:center; margin-bottom:8px }
.canvas-wrap { overflow:auto; max-height: 75vh; }
canvas { display:block; margin:auto; border-radius:4px; box-shadow:0 8px 30px rgba(0,0,0,0.6) }
.close { position:absolute; right:12px; top:12px; background:transparent; border:none; color:#fff; font-size:18px }
.error-msg { color:#ff7b7b; margin-top:8px }
</style>
