<template>
  <div class="admin-modal" @click.self="$emit('close')">
    <div class="admin-panel">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3>Panel de Administración</h3>
        <button @click="$emit('close')" class="close-btn">✕</button>
      </div>
      
      <!-- TABS -->
      <div class="tabs">
        <button :class="{active: activeTab === 'users'}" @click="activeTab='users'">Usuarios</button>
        <button :class="{active: activeTab === 'roles'}" @click="activeTab='roles'">Roles</button>
        <button :class="{active: activeTab === 'config'}" @click="activeTab='config'">Configuración</button>
      </div>

      <!-- TAB: USERS -->
      <div v-if="activeTab === 'users'" class="tab-content">
        <h4>Gestión de Usuarios</h4>
        
        <!-- Create User Form -->
        <div class="create-user-form">
          <h5>Crear Nuevo Usuario</h5>
          <input v-model="newUser.username" placeholder="Nombre de usuario" />
          <input v-model="newUser.password" type="password" placeholder="Contraseña" />
          <input v-model="newUser.roles" placeholder="Roles (separados por coma)" />
          <button @click="createUser">Crear Usuario</button>
        </div>

        <!-- User List -->
        <div v-if="loadingUsers">Cargando usuarios...</div>
        <ul v-else class="user-list">
          <li v-for="u in users" :key="u.id" class="user-item">
            <div class="user-info">
              <strong>{{ u.username }}</strong> (ID: {{ u.id }})
              <div class="user-roles">
                <span v-for="r in u.roles" :key="r" class="role-chip">{{ r }}</span>
              </div>
            </div>
            
            <div class="user-actions">
              <div class="role-checkboxes">
                <label v-for="role in roles" :key="role.name" class="role-checkbox">
                  <input type="checkbox" :checked="u.roles.includes(role.name)" @change="toggleUserRole(u.username, role.name, $event.target.checked)" />
                  {{ role.name }}
                </label>
              </div>
              <div class="action-buttons">
                <button @click="openChangePassword(u)" class="btn-edit">Cambiar Contraseña</button>
                <button @click="deleteUser(u)" class="btn-delete">Eliminar</button>
              </div>
            </div>
          </li>
        </ul>

        <!-- Change Password Modal -->
        <div v-if="changingPassword" class="modal-overlay" @click.self="changingPassword = null">
          <div class="modal-box">
            <h5>Cambiar Contraseña de {{ changingPassword.username }}</h5>
            <input v-model="newPassword" type="password" placeholder="Nueva contraseña" />
            <div style="display:flex; gap:8px; margin-top:10px;">
              <button @click="updatePassword">Actualizar</button>
              <button @click="changingPassword = null" class="btn-cancel">Cancelar</button>
            </div>
          </div>
        </div>
      </div>

      <!-- TAB: ROLES -->
      <div v-if="activeTab === 'roles'" class="tab-content">
        <h4>Gestión de Roles</h4>
        <div v-if="loadingRoles">Cargando roles...</div>
        <ul v-else>
          <li v-for="r in roles" :key="r.id">{{ r.name }} (ID: {{ r.id }})</li>
        </ul>
        <div class="create-role">
          <input v-model="newRoleName" placeholder="Nombre del nuevo rol" />
          <button @click="createRole">Crear Rol</button>
        </div>
      </div>

      <!-- TAB: CONFIG -->
      <div v-if="activeTab === 'config'" class="tab-content">
        <h4>Configuración del Sistema</h4>
        <div v-if="loadingConfig">Cargando configuración...</div>
        <div v-else class="config-form">
          <div class="config-field">
            <label>Tipo de Embedding por Defecto:</label>
            <select v-model="config.default_embedding_type" @change="updateConfig('default_embedding_type', config.default_embedding_type)">
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama</option>
            </select>
          </div>

          <div v-if="config.default_embedding_type === 'ollama'" class="config-field">
            <label>Modelo Ollama por Defecto (solo embeddings):</label>
            <p class="hint">⚠️ Solo se muestran modelos de embedding. Los LLMs (qwen2.5vl, qwen3, deepseek, llama) no aparecen aquí.</p>
            <button @click="fetchOllamaModels" class="btn-refresh" :disabled="loadingOllamaModels">
              {{ loadingOllamaModels ? 'Cargando...' : 'Actualizar Lista de Modelos de Embedding' }}
            </button>
            <select v-model="config.default_ollama_model" @change="updateConfig('default_ollama_model', config.default_ollama_model)">
              <option v-for="m in ollamaModels" :key="m" :value="m">{{ m }}</option>
            </select>
            <p v-if="ollamaModels.length === 0" class="warning">No se encontraron modelos de embedding. Instala uno con: <code>ollama pull qwen3-embedding</code></p>
          </div>

          <div v-if="config.default_embedding_type === 'openai'" class="config-field">
            <label>Modelo OpenAI por Defecto:</label>
            <select v-model="config.default_openai_model" @change="updateConfig('default_openai_model', config.default_openai_model)">
              <option value="text-embedding-3-large">text-embedding-3-large</option>
              <option value="text-embedding-3-small">text-embedding-3-small</option>
              <option value="text-embedding-ada-002">text-embedding-ada-002</option>
            </select>
          </div>

          <div class="config-info">
            <p><strong>Configuración actual:</strong></p>
            <pre>{{ JSON.stringify(config, null, 2) }}</pre>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  name: 'AdminPanel',
  data() {
    return {
      activeTab: 'users',
      users: [],
      roles: [],
      loadingUsers: false,
      loadingRoles: false,
      loadingConfig: false,
      loadingOllamaModels: false,
      newRoleName: '',
      newUser: { username: '', password: '', roles: '' },
      changingPassword: null,
      newPassword: '',
      config: {
        default_embedding_type: 'openai',
        default_ollama_model: 'qwen3-embedding:0.6b',
        default_openai_model: 'text-embedding-3-large'
      },
      ollamaModels: []
    }
  },
  methods: {
    async fetchUsers() {
      this.loadingUsers = true
      try {
        const res = await fetch('/admin/users')
        if (!res.ok) throw new Error('No autorizado o error')
        const data = await res.json()
        this.users = data.users || []
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudieron cargar usuarios')
      } finally {
        this.loadingUsers = false
      }
    },
    async fetchRoles() {
      this.loadingRoles = true
      try {
        const res = await fetch('/roles')
        if (!res.ok) throw new Error('No autorizado o error')
        const data = await res.json()
        this.roles = data.roles || []
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudieron cargar roles')
      } finally {
        this.loadingRoles = false
      }
    },
    async fetchConfig() {
      this.loadingConfig = true
      try {
        const res = await fetch('/admin/config')
        if (!res.ok) throw new Error('No autorizado')
        const data = await res.json()
        this.config = { ...this.config, ...data.config }
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo cargar configuración')
      } finally {
        this.loadingConfig = false
      }
    },
    async fetchOllamaModels() {
      this.loadingOllamaModels = true
      try {
        const res = await fetch('/admin/ollama/models')
        if (!res.ok) throw new Error('Error al obtener modelos de Ollama')
        const data = await res.json()
        this.ollamaModels = data.models || []
        if (this.ollamaModels.length > 0 && !this.config.default_ollama_model) {
          this.config.default_ollama_model = this.ollamaModels[0]
        }
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudieron cargar modelos de Ollama')
      } finally {
        this.loadingOllamaModels = false
      }
    },
    async updateConfig(key, value) {
      try {
        const form = new FormData()
        form.append('key', key)
        form.append('value', value)
        const res = await fetch('/admin/config', { method: 'POST', body: form })
        if (!res.ok) throw new Error('Failed')
        this.$emit('info', `Configuración actualizada: ${key} = ${value}`)
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo actualizar configuración')
      }
    },
    async createUser() {
      if (!this.newUser.username || !this.newUser.password) {
        return this.$emit('info', 'Completa usuario y contraseña')
      }
      try {
        const form = new FormData()
        form.append('username', this.newUser.username)
        form.append('password', this.newUser.password)
        form.append('roles', this.newUser.roles)
        const res = await fetch('/admin/users', { method: 'POST', body: form })
        if (!res.ok) throw new Error('Failed')
        const data = await res.json()
        this.$emit('info', `Usuario creado: ${data.username}`)
        this.newUser = { username: '', password: '', roles: '' }
        await this.fetchUsers()
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo crear usuario')
      }
    },
    openChangePassword(user) {
      this.changingPassword = user
      this.newPassword = ''
    },
    async updatePassword() {
      if (!this.newPassword) return this.$emit('info', 'Ingresa una contraseña')
      try {
        const form = new FormData()
        form.append('new_password', this.newPassword)
        const res = await fetch(`/admin/users/${this.changingPassword.id}/password`, { method: 'PUT', body: form })
        if (!res.ok) throw new Error('Failed')
        this.$emit('info', `Contraseña actualizada para ${this.changingPassword.username}`)
        this.changingPassword = null
        this.newPassword = ''
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo actualizar contraseña')
      }
    },
    async deleteUser(user) {
      if (!confirm(`¿Eliminar usuario ${user.username}?`)) return
      try {
        const res = await fetch(`/admin/users/${user.id}`, { method: 'DELETE' })
        if (!res.ok) throw new Error('Failed')
        this.$emit('info', `Usuario eliminado: ${user.username}`)
        await this.fetchUsers()
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo eliminar usuario')
      }
    },
    async toggleUserRole(username, role, checked) {
      try {
        const form = new FormData()
        form.append('username', username)
        form.append('role', role)
        const url = checked ? '/roles/assign' : '/roles/unassign'
        const res = await fetch(url, { method: 'POST', body: form })
        if (!res.ok) throw new Error('Failed')
        this.$emit('info', `${checked ? 'Asignado' : 'Removido'} rol ${role} ${checked ? 'a' : 'de'} ${username}`)
        await this.fetchUsers()
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo actualizar rol del usuario')
      }
    },
    async createRole() {
      if (!this.newRoleName.trim()) return this.$emit('info', 'Nombre de rol vacío')
      const form = new FormData()
      form.append('name', this.newRoleName.trim())
      try {
        const res = await fetch('/roles', { method: 'POST', body: form })
        if (!res.ok) throw new Error('Failed')
        const data = await res.json()
        this.$emit('info', `Rol creado: ${data.name}`)
        this.newRoleName = ''
        await this.fetchRoles()
      } catch (e) {
        console.error(e)
        this.$emit('error', 'No se pudo crear rol')
      }
    }
  },
  mounted() {
    this.fetchUsers()
    this.fetchRoles()
    this.fetchConfig()
  },
  watch: {
    'config.default_embedding_type'(newVal) {
      if (newVal === 'ollama' && this.ollamaModels.length === 0) {
        this.fetchOllamaModels()
      }
    }
  }
}
</script>

<style scoped>
.admin-modal {
  position: fixed;
  inset: 0;
  display:flex;
  align-items:center;
  justify-content:center;
  background: rgba(0,0,0,0.7);
  z-index: 10000;
}
.admin-panel {
  background: #0f1724;
  color: #e6eef8;
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 12px;
  padding: 24px;
}
.close-btn { 
  background:transparent; 
  border:none; 
  color:#cbd5e1; 
  cursor:pointer; 
  font-size:24px;
  transition: color 0.2s;
}
.close-btn:hover { color: #f87171; }

.tabs {
  display: flex;
  gap: 8px;
  margin: 16px 0;
  border-bottom: 2px solid rgba(255,255,255,0.1);
}
.tabs button {
  background: transparent;
  border: none;
  color: #94a3b8;
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tabs button.active {
  color: #60a5fa;
  border-bottom-color: #60a5fa;
}
.tabs button:hover {
  color: #93c5fd;
}

.tab-content {
  margin-top: 20px;
}

.create-user-form, .create-role, .config-form {
  background: rgba(255,255,255,0.03);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}
.create-user-form input, .create-role input, .config-form input, .config-form select {
  display: block;
  width: 100%;
  max-width: 400px;
  margin: 8px 0;
  padding: 8px 12px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: #e6eef8;
}
.create-user-form button, .create-role button {
  margin-top: 10px;
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.create-user-form button:hover, .create-role button:hover {
  background: #2563eb;
}

.user-list {
  list-style: none;
  padding: 0;
}
.user-item {
  background: rgba(255,255,255,0.02);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  border-left: 3px solid #3b82f6;
}
.user-info {
  margin-bottom: 12px;
}
.user-roles {
  margin-top: 8px;
}
.role-chip {
  display: inline-block;
  background: rgba(96,165,250,0.2);
  padding: 4px 10px;
  border-radius: 12px;
  margin-right: 6px;
  font-size: 12px;
}
.user-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.role-checkboxes {
  display:flex;
  gap:8px;
  flex-wrap:wrap;
}
.role-checkbox {
  background: rgba(255,255,255,0.05);
  padding: 6px 10px;
  border-radius: 6px;
  display:flex;
  gap:6px;
  align-items:center;
  cursor: pointer;
  transition: background 0.2s;
}
.role-checkbox:hover {
  background: rgba(255,255,255,0.08);
}
.action-buttons {
  display: flex;
  gap: 8px;
}
.btn-edit, .btn-delete, .btn-cancel, .btn-refresh {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.btn-edit {
  background: #10b981;
  color: white;
}
.btn-edit:hover {
  background: #059669;
}
.btn-delete {
  background: #ef4444;
  color: white;
}
.btn-delete:hover {
  background: #dc2626;
}
.btn-cancel {
  background: #6b7280;
  color: white;
}
.btn-cancel:hover {
  background: #4b5563;
}
.btn-refresh {
  background: #8b5cf6;
  color: white;
  margin-bottom: 8px;
}
.btn-refresh:hover {
  background: #7c3aed;
}
.btn-refresh:disabled {
  background: #4b5563;
  cursor: not-allowed;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
}
.modal-box {
  background: #1e293b;
  padding: 24px;
  border-radius: 10px;
  min-width: 300px;
}
.modal-box h5 {
  margin-top: 0;
}

.config-field {
  margin-bottom: 16px;
}
.config-field label {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
  color: #94a3b8;
}
.config-field .hint {
  font-size: 13px;
  color: #fbbf24;
  margin: 6px 0;
  padding: 8px 12px;
  background: rgba(251, 191, 36, 0.1);
  border-left: 3px solid #fbbf24;
  border-radius: 4px;
}
.config-field .warning {
  font-size: 13px;
  color: #f87171;
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(248, 113, 113, 0.1);
  border-left: 3px solid #f87171;
  border-radius: 4px;
}
.config-field .warning code {
  background: rgba(0,0,0,0.3);
  padding: 2px 6px;
  border-radius: 3px;
  color: #a5f3fc;
  font-family: 'Courier New', monospace;
}
.config-info {
  margin-top: 20px;
  padding: 12px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
}
.config-info pre {
  background: rgba(0,0,0,0.3);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  color: #a5b4fc;
}
</style>