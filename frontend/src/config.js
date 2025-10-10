// Configuración global de la aplicación

export const API_BASE_URL = 'http://localhost:8000';

export const DEFAULT_SETTINGS = {
  temperature: 0.7,
  maxTokens: 1000,
  topK: 3,
  autoScroll: true,
  showTimestamps: true,
  soundEnabled: false
};

export const EMBEDDING_TYPES = [
  { value: 'openai', label: 'OpenAI', icon: '🤖' },
  { value: 'ollama', label: 'Ollama', icon: '🦙' }
];

export const FILE_CONSTRAINTS = {
  maxSize: 10 * 1024 * 1024, // 10MB
  acceptedFormats: ['.pdf'],
  acceptedMimeTypes: ['application/pdf']
};

export const MESSAGE_CONSTRAINTS = {
  maxChars: 2000,
  minChars: 1
};

export const TOAST_DURATION = 3000; // ms

export const NOTIFICATION_SOUNDS = {
  success: { frequency: 800, duration: 0.1 },
  error: { frequency: 200, duration: 0.1 },
  info: { frequency: 600, duration: 0.1 },
  warning: { frequency: 400, duration: 0.1 }
};

export const STORAGE_KEYS = {
  settings: 'chatpdf-settings',
  theme: 'chatpdf-theme',
  history: 'chatpdf-history'
};

export const ROUTES = {
  uploadPdf: '/upload_pdf/',
  chat: '/chat/'
};

export const TIME_FORMATS = {
  relative: true, // "Hace 5 min" vs "14:30"
  showSeconds: false
};

export const THEME_COLORS = {
  light: {
    primary: '#7b1fa2',
    secondary: '#1976d2',
    background: 'linear-gradient(135deg, #7b1fa2 0%, #1976d2 100%)',
    surface: '#fff',
    text: '#212121'
  },
  dark: {
    primary: '#bb86fc',
    secondary: '#03dac6',
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    surface: '#1e1e1e',
    text: '#e0e0e0'
  }
};

export const ANIMATIONS = {
  duration: {
    fast: 200,
    normal: 300,
    slow: 500
  },
  easing: {
    easeOut: 'cubic-bezier(0.25, 0.8, 0.25, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
  }
};

export const KEYBOARD_SHORTCUTS = {
  send: 'Enter',
  newLine: 'Shift+Enter',
  clearChat: 'Ctrl+L',
  openSettings: 'Ctrl+,',
  toggleTheme: 'Ctrl+D'
};

// Validadores
export const validators = {
  isValidPdfFile(file) {
    if (!file) return false;
    return FILE_CONSTRAINTS.acceptedMimeTypes.includes(file.type) &&
           file.size <= FILE_CONSTRAINTS.maxSize;
  },
  
  isValidMessage(message) {
    if (!message || typeof message !== 'string') return false;
    const trimmed = message.trim();
    return trimmed.length >= MESSAGE_CONSTRAINTS.minChars &&
           trimmed.length <= MESSAGE_CONSTRAINTS.maxChars;
  },
  
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }
};

// Utilidades de tiempo
export const timeUtils = {
  formatRelativeTime(date) {
    if (!date) return '-';
    const d = new Date(date);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Hace un momento';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    if (diffDays < 7) return `Hace ${diffDays}d`;
    
    return d.toLocaleDateString();
  },
  
  formatTimestamp(date) {
    if (!date) return '';
    const d = new Date(date);
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  }
};

// Estimación de tokens (aproximado)
export const tokenUtils = {
  estimateTokens(text) {
    if (!text) return 0;
    // Aproximación: ~4 caracteres por token
    return Math.ceil(text.length / 4);
  },
  
  estimateCost(tokens, model = 'gpt-3.5-turbo') {
    // Precios aproximados (actualizar según sea necesario)
    const prices = {
      'gpt-3.5-turbo': 0.002 / 1000, // $0.002 por 1K tokens
      'gpt-4': 0.03 / 1000
    };
    
    const pricePerToken = prices[model] || 0;
    return (tokens * pricePerToken).toFixed(4);
  }
};

export default {
  API_BASE_URL,
  DEFAULT_SETTINGS,
  EMBEDDING_TYPES,
  FILE_CONSTRAINTS,
  MESSAGE_CONSTRAINTS,
  TOAST_DURATION,
  NOTIFICATION_SOUNDS,
  STORAGE_KEYS,
  ROUTES,
  TIME_FORMATS,
  THEME_COLORS,
  ANIMATIONS,
  KEYBOARD_SHORTCUTS,
  validators,
  timeUtils,
  tokenUtils
};
