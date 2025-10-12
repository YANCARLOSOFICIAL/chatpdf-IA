<template>
  <div class="typing-indicator">
    <span></span>
    <span></span>
    <span></span>
  </div>
</template>

<script>
export default {
  name: 'TypingIndicator'
};
</script>

<style scoped>
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 12px 16px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 12px;
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

/* Light mode */
:global(#app.light-mode) .typing-indicator {
  background: #ffffff;
  border-color: #e2e8f0;
}
</style>
