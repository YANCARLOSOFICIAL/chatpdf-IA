<template>
  <div class="conversation-section">
    <div class="section-header">
      <h4 class="section-title">CONVERSACIONES</h4>
      <button 
        class="new-conversation-btn"
        @click="$emit('new')"
        title="Nueva conversación"
      >
        ➕
      </button>
    </div>

    <div class="conversations-list">
      <div 
        v-for="conv in conversations" 
        :key="conv.id"
        class="conversation-item"
        :class="{ 'active': activeConversationId === conv.id }"
        @click="$emit('select', conv)"
      >
        <div class="conversation-info">
          <div class="conversation-title">{{ conv.title }}</div>
          <div class="conversation-meta">
            <span class="message-count">{{ conv.messageCount }} mensajes</span>
            <span class="conversation-date">{{ conv.date }}</span>
          </div>
        </div>
        <button 
          class="delete-conversation-btn"
          @click.stop="$emit('delete', conv.id)"
          title="Eliminar conversación"
        >
          🗑️
        </button>
      </div>

      <div v-if="conversations.length === 0" class="empty-conversations">
        <p>No hay conversaciones guardadas</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConversationList',
  props: {
    conversations: {
      type: Array,
      default: () => []
    },
    activeConversationId: {
      type: [String, Number],
      default: null
    }
  },
  emits: ['select', 'new', 'delete']
};
</script>

<style scoped>
.conversation-section {
  padding: 16px 0;
  border-top: 1px solid #2a3152;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px 12px;
}

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  letter-spacing: 0.5px;
  margin: 0;
}

.new-conversation-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid #2a3152;
  border-radius: 6px;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.new-conversation-btn:hover {
  background: #1e2640;
  border-color: #4d6cfa;
  color: #4d6cfa;
  transform: scale(1.05);
}

.conversations-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
  max-height: 300px;
  overflow-y: auto;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.conversation-item:hover {
  background: #1e2640;
  border-color: #2a3152;
}

.conversation-item.active {
  background: #1e2640;
  border-color: #4d6cfa;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-size: 14px;
  font-weight: 500;
  color: #e4e6eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.conversation-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #6b7280;
}

.message-count {
  display: flex;
  align-items: center;
  gap: 4px;
}

.message-count::before {
  content: '💬';
  font-size: 10px;
}

.conversation-date {
  font-size: 11px;
}

.delete-conversation-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
}

.conversation-item:hover .delete-conversation-btn {
  opacity: 1;
}

.delete-conversation-btn:hover {
  background: #dc2626;
  border-color: #ef4444;
  transform: scale(1.1);
}

.empty-conversations {
  padding: 24px 16px;
  text-align: center;
  color: #6b7280;
  font-size: 12px;
}

.empty-conversations p {
  margin: 0;
}

/* Scrollbar */
.conversations-list::-webkit-scrollbar {
  width: 6px;
}

.conversations-list::-webkit-scrollbar-track {
  background: transparent;
}

.conversations-list::-webkit-scrollbar-thumb {
  background: #2a3152;
  border-radius: 3px;
}

.conversations-list::-webkit-scrollbar-thumb:hover {
  background: #4d6cfa;
}

/* Light mode */
:global(#app.light-mode) .conversation-section {
  border-color: #e2e8f0;
}

:global(#app.light-mode) .section-title {
  color: #718096;
}

:global(#app.light-mode) .new-conversation-btn {
  border-color: #e2e8f0;
  color: #718096;
}

:global(#app.light-mode) .new-conversation-btn:hover {
  background: #f7fafc;
  color: #4d6cfa;
}

:global(#app.light-mode) .conversation-item:hover {
  background: #f7fafc;
  border-color: #e2e8f0;
}

:global(#app.light-mode) .conversation-item.active {
  background: #edf2f7;
}

:global(#app.light-mode) .conversation-title {
  color: #1a202c;
}

:global(#app.light-mode) .conversation-meta {
  color: #718096;
}

:global(#app.light-mode) .delete-conversation-btn:hover {
  background: #dc2626;
}

:global(#app.light-mode) .empty-conversations {
  color: #718096;
}

:global(#app.light-mode) .conversations-list::-webkit-scrollbar-thumb {
  background: #e2e8f0;
}
</style>
