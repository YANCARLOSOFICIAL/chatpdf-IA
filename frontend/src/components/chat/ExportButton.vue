<template>
  <div class="export-container">
    <button 
      class="export-btn"
      @click="toggleMenu"
      :disabled="!hasMessages"
      :title="hasMessages ? 'Exportar conversación' : 'No hay mensajes para exportar'"
    >
      <span class="icon">📥</span>
      <span class="text">Exportar</span>
    </button>

    <div v-if="showMenu" class="export-menu" @click.stop>
      <div class="menu-header">
        <span>Exportar como:</span>
        <button @click="closeMenu" class="close-btn">✕</button>
      </div>
      
      <button 
        class="menu-item"
        @click="exportAs('txt')"
      >
        <span class="item-icon">📝</span>
        <div class="item-info">
          <div class="item-title">Texto plano</div>
          <div class="item-desc">Archivo .txt simple</div>
        </div>
      </button>

      <button 
        class="menu-item"
        @click="exportAs('markdown')"
      >
        <span class="item-icon">📄</span>
        <div class="item-info">
          <div class="item-title">Markdown</div>
          <div class="item-desc">Archivo .md con formato</div>
        </div>
      </button>

      <button 
        class="menu-item"
        @click="exportAs('json')"
      >
        <span class="item-icon">💾</span>
        <div class="item-info">
          <div class="item-title">JSON</div>
          <div class="item-desc">Datos estructurados</div>
        </div>
      </button>

      <button 
        class="menu-item"
        @click="exportAs('html')"
      >
        <span class="item-icon">🌐</span>
        <div class="item-info">
          <div class="item-title">HTML</div>
          <div class="item-desc">Página web</div>
        </div>
      </button>
    </div>

    <!-- Backdrop -->
    <div 
      v-if="showMenu" 
      class="backdrop"
      @click="closeMenu"
    ></div>
  </div>
</template>

<script>
export default {
  name: 'ExportButton',
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    documentName: {
      type: String,
      default: 'Conversación'
    }
  },
  emits: ['export'],
  data() {
    return {
      showMenu: false
    };
  },
  computed: {
    hasMessages() {
      return this.messages && this.messages.length > 0;
    }
  },
  methods: {
    toggleMenu() {
      if (this.hasMessages) {
        this.showMenu = !this.showMenu;
      }
    },
    closeMenu() {
      this.showMenu = false;
    },
    exportAs(format) {
      let content = '';
      let filename = `${this.sanitizeFilename(this.documentName)}_${this.getTimestamp()}`;
      let mimeType = 'text/plain';

      switch (format) {
        case 'txt':
          content = this.generateTxt();
          filename += '.txt';
          mimeType = 'text/plain';
          break;
        case 'markdown':
          content = this.generateMarkdown();
          filename += '.md';
          mimeType = 'text/markdown';
          break;
        case 'json':
          content = this.generateJson();
          filename += '.json';
          mimeType = 'application/json';
          break;
        case 'html':
          content = this.generateHtml();
          filename += '.html';
          mimeType = 'text/html';
          break;
      }

      this.downloadFile(content, filename, mimeType);
      this.closeMenu();
      this.$emit('export', { format, filename });
    },
    generateTxt() {
      let txt = `Conversación: ${this.documentName}\n`;
      txt += `Fecha: ${new Date().toLocaleString('es-ES')}\n`;
      txt += `Total de mensajes: ${this.messages.length}\n`;
      txt += '='.repeat(50) + '\n\n';

      this.messages.forEach((msg, index) => {
        const role = msg.role === 'user' ? 'Usuario' : 'Asistente';
        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('es-ES') : '';
        
        txt += `[${index + 1}] ${role}`;
        if (time) txt += ` - ${time}`;
        txt += '\n';
        txt += '-'.repeat(50) + '\n';
        txt += msg.content + '\n\n';
      });

      return txt;
    },
    generateMarkdown() {
      let md = `# ${this.documentName}\n\n`;
      md += `**Fecha:** ${new Date().toLocaleString('es-ES')}  \n`;
      md += `**Total de mensajes:** ${this.messages.length}\n\n`;
      md += '---\n\n';

      this.messages.forEach((msg, index) => {
        const role = msg.role === 'user' ? '👤 Usuario' : '🤖 Asistente';
        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('es-ES') : '';
        
        md += `## ${role}`;
        if (time) md += ` <small>${time}</small>`;
        md += '\n\n';
        md += msg.content + '\n\n';
      });

      return md;
    },
    generateJson() {
      const data = {
        document: this.documentName,
        exportDate: new Date().toISOString(),
        totalMessages: this.messages.length,
        messages: this.messages.map((msg, index) => ({
          index: index + 1,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp
        }))
      };

      return JSON.stringify(data, null, 2);
    },
    generateHtml() {
      let html = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${this.escapeHtml(this.documentName)}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0a0e27;
      color: #e4e6eb;
      padding: 20px;
      line-height: 1.6;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
    }
    .header {
      background: #151934;
      padding: 24px;
      border-radius: 12px;
      margin-bottom: 24px;
      border: 1px solid #1e2640;
    }
    h1 {
      color: #4d6cfa;
      margin-bottom: 12px;
    }
    .meta {
      color: #6b7280;
      font-size: 14px;
    }
    .message {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
      animation: fadeIn 0.3s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .message.user {
      flex-direction: row-reverse;
    }
    .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      flex-shrink: 0;
      background: #1e2640;
    }
    .message.user .avatar {
      background: #4d6cfa;
    }
    .bubble {
      flex: 1;
      max-width: 70%;
    }
    .content {
      padding: 12px 16px;
      background: #151934;
      border: 1px solid #1e2640;
      border-radius: 12px;
      margin-bottom: 8px;
    }
    .message.user .content {
      background: #4d6cfa;
      border-color: #5a7bff;
    }
    .time {
      font-size: 12px;
      color: #6b7280;
      padding: 0 4px;
    }
    .message.user .time {
      text-align: right;
    }
    code {
      background: #0a0e27;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
    }
    pre {
      background: #0a0e27;
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 8px 0;
    }
    pre code {
      background: transparent;
      padding: 0;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${this.escapeHtml(this.documentName)}</h1>
      <div class="meta">
        <div>Fecha de exportación: ${new Date().toLocaleString('es-ES')}</div>
        <div>Total de mensajes: ${this.messages.length}</div>
      </div>
    </div>
`;

      this.messages.forEach(msg => {
        const role = msg.role === 'user' ? 'user' : 'assistant';
        const emoji = msg.role === 'user' ? '👤' : '🤖';
        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('es-ES') : '';
        
        html += `    <div class="message ${role}">
      <div class="avatar">${emoji}</div>
      <div class="bubble">
        <div class="content">${this.escapeHtml(msg.content).replace(/\n/g, '<br>')}</div>
        ${time ? `<div class="time">${time}</div>` : ''}
      </div>
    </div>
`;
      });

      html += `  </div>
</body>
</html>`;

      return html;
    },
    downloadFile(content, filename, mimeType) {
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    sanitizeFilename(name) {
      return name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    },
    getTimestamp() {
      const now = new Date();
      return now.toISOString().replace(/[:.]/g, '-').slice(0, -5);
    },
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }
  }
};
</script>

<style scoped>
.export-container {
  position: relative;
}

.export-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1e2640;
  border: 1px solid #2a3152;
  border-radius: 8px;
  color: #e4e6eb;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.export-btn:hover:not(:disabled) {
  background: #2a3152;
  border-color: #4d6cfa;
  transform: translateY(-2px);
}

.export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon {
  font-size: 16px;
}

.export-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 280px;
  background: #151934;
  border: 1px solid #2a3152;
  border-radius: 12px;
  padding: 8px;
  z-index: 1001;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  animation: menuSlideIn 0.2s ease-out;
}

@keyframes menuSlideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  border-bottom: 1px solid #2a3152;
  margin-bottom: 4px;
}

.close-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #6b7280;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #2a3152;
  color: #e4e6eb;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #e4e6eb;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.menu-item:hover {
  background: #1e2640;
  transform: translateX(4px);
}

.item-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 2px;
}

.item-desc {
  font-size: 12px;
  color: #6b7280;
}

.backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  background: transparent;
}

/* Light mode */
:global(#app.light-mode) .export-btn {
  background: #f7fafc;
  border-color: #e2e8f0;
  color: #1a202c;
}

:global(#app.light-mode) .export-btn:hover:not(:disabled) {
  background: #edf2f7;
}

:global(#app.light-mode) .export-menu {
  background: #ffffff;
  border-color: #e2e8f0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

:global(#app.light-mode) .menu-header {
  border-color: #e2e8f0;
  color: #718096;
}

:global(#app.light-mode) .close-btn:hover {
  background: #f7fafc;
}

:global(#app.light-mode) .menu-item {
  color: #1a202c;
}

:global(#app.light-mode) .menu-item:hover {
  background: #f7fafc;
}

:global(#app.light-mode) .item-desc {
  color: #718096;
}
</style>
