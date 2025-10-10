<template>
  <div class="tab-navigation">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      class="tab-button"
      :class="{ active: activeTab === tab.id }"
      @click="$emit('change', tab.id)"
    >
      <span class="tab-icon" v-html="tab.icon"></span>
      <span class="tab-label">{{ tab.label }}</span>
    </button>
  </div>
</template>

<script>
export default {
  name: 'TabNavigation',
  props: {
    activeTab: {
      type: String,
      default: 'chat'
    }
  },
  emits: ['change'],
  data() {
    return {
      tabs: [
        {
          id: 'chat',
          label: 'Chat',
          icon: '💬'
        },
        {
          id: 'documentos',
          label: 'Documentos',
          icon: '📄'
        },
        {
          id: 'sistema',
          label: 'Sistema',
          icon: '⚙️'
        }
      ]
    };
  }
};
</script>

<style scoped>
.tab-navigation {
  display: flex;
  gap: 0;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px 12px 0 0;
  padding: 4px;
  backdrop-filter: blur(10px);
  border-bottom: 2px solid rgba(0, 188, 212, 0.2);
}

.tab-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 24px;
  background: transparent;
  border: none;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.tab-button::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%) scaleX(0);
  width: 60%;
  height: 3px;
  background: linear-gradient(90deg, #00bcd4, #0097a7);
  border-radius: 3px 3px 0 0;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-button:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}

.tab-button.active {
  background: rgba(0, 188, 212, 0.15);
  color: #00bcd4;
  font-weight: 600;
}

.tab-button.active::after {
  transform: translateX(-50%) scaleX(1);
}

.tab-icon {
  font-size: 20px;
  transition: transform 0.3s ease;
}

.tab-button:hover .tab-icon {
  transform: scale(1.15);
}

.tab-button.active .tab-icon {
  transform: scale(1.2);
  filter: drop-shadow(0 0 8px rgba(0, 188, 212, 0.5));
}

.tab-label {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Dark mode */
:deep(.dark-mode) .tab-navigation {
  background: rgba(255, 255, 255, 0.03);
  border-bottom-color: rgba(0, 188, 212, 0.3);
}

:deep(.dark-mode) .tab-button {
  color: rgba(255, 255, 255, 0.5);
}

:deep(.dark-mode) .tab-button:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.95);
}

:deep(.dark-mode) .tab-button.active {
  background: rgba(0, 188, 212, 0.2);
  color: #4dd0e1;
}

@media (max-width: 768px) {
  .tab-button {
    padding: 12px 16px;
    font-size: 14px;
  }
  
  .tab-icon {
    font-size: 18px;
  }
  
  .tab-label {
    display: none;
  }
}
</style>
