<template>
  <div class="container">
    <h1>ChatPDF con IA</h1>
    <form @submit.prevent="handleUpload">
      <input type="file" @change="onFileChange" accept="application/pdf" />
      <select v-model="embeddingType">
  <option value="ollama">Embeddings Locales (Ollama)</option>
  <option value="openai">Embeddings en la Nube (OpenAI)</option>
      </select>
      <button type="submit">Subir PDF</button>
    </form>
    <div v-if="pdfUploaded">
      <h2>Chat</h2>
      <div v-for="msg in chatHistory" :key="msg.id" class="chat-msg">
        <strong>{{ msg.role }}:</strong> {{ msg.text }}
      </div>
      <form @submit.prevent="sendMessage">
        <input v-model="userMessage" placeholder="Escribe tu pregunta..." />
        <button type="submit">Enviar</button>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      embeddingType: 'ollama',
      selectedFile: null,
      pdfUploaded: false,
      chatHistory: [],
      userMessage: '',
      pdfId: null,
    };
  },
  methods: {
    onFileChange(e) {
      this.selectedFile = e.target.files[0];
    },
    async handleUpload() {
      if (!this.selectedFile) return;
      const formData = new FormData();
      formData.append('pdf', this.selectedFile);
      formData.append('embedding_type', this.embeddingType);
      const res = await fetch('http://localhost:8000/upload_pdf/', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      this.pdfUploaded = true;
      this.pdfId = data.pdf_id || 1;
      this.chatHistory = [];
    },
    async sendMessage() {
      if (!this.userMessage) return;
      const formData = new FormData();
      formData.append('query', this.userMessage);
      formData.append('pdf_id', this.pdfId);
      formData.append('embedding_type', this.embeddingType);
      const res = await fetch('http://localhost:8000/chat/', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      this.chatHistory.push({ role: 'Usuario', text: this.userMessage, id: Date.now() });
      this.chatHistory.push({ role: 'IA', text: data.response, id: Date.now() + 1 });
      this.userMessage = '';
    },
  },
};
</script>

<style>
.container {
  max-width: 600px;
  margin: auto;
  padding: 2rem;
}
.chat-msg {
  margin-bottom: 1rem;
}
</style>
