<template>
  <div class="conversation-history">
    <div class="history-header">
      <h3>Historial de Conversaciones</h3>
      <button @click="$emit('close')" class="close-btn">✕</button>
    </div>

    <div v-if="loading" class="loading-state">
      Cargando conversaciones...
    </div>

    <div v-else-if="conversations.length === 0" class="empty-state">
      <p>No tienes conversaciones guardadas aún.</p>
      <p class="hint">Empieza a chatear con tus documentos para crear historial.</p>
    </div>

    <div v-else class="conversations-list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conversation-item"
        :class="{ active: conv.id === activeConversationId }"
        @click="$emit('load-conversation', conv)"
      >
        <div class="conversation-info">
          <div class="conversation-title">{{ conv.title }}</div>
          <div class="conversation-meta">
            <span class="pdf-name">📄 {{ conv.pdf_filename || 'Sin documento' }}</span>
            <span class="date">{{ formatDate(conv.updated_at) }}</span>
          </div>
        </div>
        <button
          @click.stop="deleteConversation(conv.id)"
          class="delete-btn"
          title="Eliminar conversación"
        >
          🗑️
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConversationHistory',
  props: {
    activeConversationId: {
      type: Number,
      default: null
    }
  },
  emits: ['close', 'load-conversation', 'conversation-deleted'],
  data() {
    return {
      conversations: [],
      loading: false
    }
  },
  mounted() {
    this.loadConversations()
  },
  methods: {
    async loadConversations() {
      this.loading = true
      try {
        const token = localStorage.getItem('chatpdf_token')
        if (!token) {
          throw new Error('No autenticado')
        }

        const response = await fetch('http://localhost:8000/conversations/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          throw new Error('Error al cargar conversaciones')
        }

        const data = await response.json()
        this.conversations = data.conversations || []
      } catch (error) {
        console.error('Error cargando conversaciones:', error)
        this.$emit('error', error.message)
      } finally {
        this.loading = false
      }
    },

    async deleteConversation(conversationId) {
      if (!confirm('¿Estás seguro de eliminar esta conversación?')) {
        return
      }

      try {
        const token = localStorage.getItem('chatpdf_token')
        if (!token) {
          throw new Error('No autenticado')
        }

        const response = await fetch(`http://localhost:8000/conversations/${conversationId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!response.ok) {
          throw new Error('Error al eliminar conversación')
        }

        // Recargar lista
        await this.loadConversations()
        this.$emit('conversation-deleted', conversationId)
      } catch (error) {
        console.error('Error eliminando conversación:', error)
        alert('Error al eliminar la conversación')
      }
    },

    formatDate(dateString) {
      if (!dateString) return ''
      
      const date = new Date(dateString)
      const now = new Date()
      const diffMs = now - date
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return 'Ahora'
      if (diffMins < 60) return `Hace ${diffMins} min`
      if (diffHours < 24) return `Hace ${diffHours}h`
      if (diffDays < 7) return `Hace ${diffDays}d`
      
      return date.toLocaleDateString('es-ES', { 
        day: 'numeric', 
        month: 'short',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
      })
    }
  }
}
</script>

<style scoped>
.conversation-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.history-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
  padding: 4px 8px;
  line-height: 1;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #111827;
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px 20px;
  color: #6b7280;
}

.empty-state p {
  margin: 8px 0;
  text-align: center;
}

.empty-state .hint {
  font-size: 14px;
  color: #9ca3af;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.conversation-item:hover {
  background: #f3f4f6;
  border-color: #e5e7eb;
}

.conversation-item.active {
  background: #eff6ff;
  border-color: #3b82f6;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-weight: 500;
  color: #111827;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: #6b7280;
}

.pdf-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.date {
  color: #9ca3af;
}

.delete-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 4px 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  transform: scale(1.1);
}

/* Scrollbar styling */
.conversations-list::-webkit-scrollbar {
  width: 6px;
}

.conversations-list::-webkit-scrollbar-track {
  background: transparent;
}

.conversations-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.conversations-list::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>
