<template>
  <div v-if="visible" class="drag-overlay">
    <div class="drag-content">
      <div class="drag-icon">📄</div>
      <h2>Suelta tu PDF aquí</h2>
      <p>Arrastra y suelta para subir tu documento</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DragOverlay',
  props: {
    visible: {
      type: Boolean,
      default: false
    }
  }
};
</script>

<style scoped>
.drag-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(77, 108, 250, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.drag-content {
  text-align: center;
  padding: 48px;
  background: rgba(255, 255, 255, 0.1);
  border: 3px dashed rgba(255, 255, 255, 0.5);
  border-radius: 24px;
  backdrop-filter: blur(20px);
}

.drag-icon {
  font-size: 96px;
  margin-bottom: 24px;
  animation: bounce 0.6s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.drag-content h2 {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin-bottom: 12px;
}

.drag-content p {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.9);
}
</style>
