<template>
  <div class="welcome-card">
    <div class="welcome-icon">👋</div>
    <h2 class="welcome-text">
      {{ message }}
    </h2>
  </div>
</template>

<script>
export default {
  name: 'WelcomeMessage',
  props: {
    message: {
      type: String,
      default: '¡Hola! Sube un PDF y podré ayudarte a analizarlo y responder preguntas sobre su contenido.'
    }
  }
};
</script>

<style scoped>
.welcome-card {
  max-width: 800px;
  margin: 0 auto;
  padding: 48px 32px;
  background: #151934;
  border: 1px solid #1e2640;
  border-radius: 16px;
  text-align: center;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 24px;
  animation: wave 2s ease-in-out infinite;
}

@keyframes wave {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(20deg); }
  75% { transform: rotate(-20deg); }
}

.welcome-text {
  font-size: 20px;
  font-weight: 500;
  color: #9ca3af;
  line-height: 1.6;
  margin: 0;
}

/* Light mode */
:global(#app.light-mode) .welcome-card {
  background: #ffffff;
  border-color: #e2e8f0;
}

:global(#app.light-mode) .welcome-text {
  color: #4a5568;
}
</style>
