<template>
  <div v-if="visible" class="progress-container">
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: progress + '%' }"></div>
    </div>
    <div class="progress-text">{{ progress }}%</div>
  </div>
</template>

<script>
export default {
  name: 'ProgressBar',
  props: {
    progress: {
      type: Number,
      required: true,
      default: 0
    },
    visible: {
      type: Boolean,
      default: false
    }
  }
};
</script>

<style scoped>
.progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: #1e2640;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4d6cfa, #5a7bff);
  border-radius: 4px;
  transition: width 0.3s ease;
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-text {
  font-size: 13px;
  font-weight: 600;
  color: #4d6cfa;
  min-width: 45px;
  text-align: right;
}
</style>
