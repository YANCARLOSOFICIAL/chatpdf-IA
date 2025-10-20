<template>
  <div v-if="visible" class="login-modal-overlay">
      <div class="login-modal">
        <div class="modal-header">
          <h3>{{ mode === 'login' ? 'Iniciar sesión' : 'Registrarse' }}</h3>
          <button class="modal-close" @click="$emit('close')">✕</button>
        </div>
        <div class="field">
          <label>Usuario</label>
          <input v-model="username" placeholder="tu.usuario" />
        </div>
        <div class="field">
          <label>Contraseña</label>
          <input type="password" v-model="password" placeholder="••••••••" />
        </div>
        <div v-if="mode === 'register'" class="field">
          <label>Confirmar contraseña</label>
          <input type="password" v-model="password2" placeholder="Repite la contraseña" />
        </div>
        <div class="actions">
          <button @click="submit" :disabled="loading">{{ mode === 'login' ? 'Ingresar' : 'Crear cuenta' }}</button>
          <button @click="$emit('close')" :disabled="loading">Cancelar</button>
        </div>
        <div class="switch-mode">
          <a href="#" @click.prevent="toggleMode">
            {{ mode === 'login' ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión' }}
          </a>
        </div>
        <div v-if="error" class="error">{{ error }}</div>
      </div>
  </div>
</template>

<script>
import api from '../../api'

export default {
  name: 'LoginModal',
  props: { visible: Boolean },
  data() {
    return { username: '', password: '', password2: '', loading: false, error: '', mode: 'login' }
  },
  methods: {
    async submit() {
      this.error = ''
      this.loading = true
      try {
        if (this.mode === 'login') {
          const token = await api.login(this.username, this.password)
          this.$emit('login-success', token)
          this.$emit('close')
        } else {
          // register
          if (this.password !== this.password2) {
            throw new Error('Las contraseñas no coinciden')
          }
          const res = await api.register(this.username, this.password)
          // register() sets token already
          this.$emit('login-success', res.token)
          this.$emit('close')
        }
      } catch (e) {
        this.error = e.message || 'Error de login'
      } finally {
        this.loading = false
      }
      },
    toggleMode() {
      this.mode = this.mode === 'login' ? 'register' : 'login'
      this.error = ''
    }
  }
}
</script>

<style scoped>
.login-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center; z-index:10000 }
.login-modal { background: linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%); color: #111; padding: 18px; border-radius:10px; width: 360px; box-shadow: 0 10px 30px rgba(15,23,42,0.2) }
.modal-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px }
.modal-close { background:transparent; border:none; font-size:16px; cursor:pointer }
.login-modal h3 { margin:0; font-size:18px }
.login-modal .field { margin-bottom:10px }
.login-modal input { width:100%; padding:10px; border-radius:8px; border:1px solid #e6eef8 }
.login-modal .actions { display:flex; gap:8px; justify-content:flex-end; margin-top:12px }
.login-modal .actions button { padding:8px 12px; border-radius:8px; border:none; cursor:pointer }
.login-modal .actions button:first-child { background:#4d6cfa; color:white }
.switch-mode { margin-top:10px; text-align:center }
.switch-mode a { color:#4d6cfa; text-decoration:none; font-size:13px }
.login-modal .error { color: #b00020; margin-top:8px; text-align:center }
</style>
