<template>
  <div class="role-panels">
    <h4>Panel de usuario</h4>
    <div class="roles-list">
      <div v-for="r in roles" :key="r" class="role-chip">{{ r }}</div>
    </div>

    <div class="panels">
      <div v-if="roles.includes('admin')" class="panel admin-panel">
        <h5>Admin</h5>
        <button @click="$emit('open-admin', 'users')">Gestionar usuarios</button>
        <button @click="$emit('open-admin', 'roles')">Gestionar roles</button>
        <button @click="$emit('open-admin', 'reprocess')">Reprocesar spans</button>
      </div>

      <div v-if="roles.includes('editor')" class="panel editor-panel">
        <h5>Editor</h5>
        <button @click="$emit('open-editor', 'upload')">Subir PDF</button>
        <button @click="$emit('open-editor', 'edit-metadata')">Editar metadatos</button>
      </div>

      <div v-if="roles.includes('viewer') || roles.length === 0" class="panel viewer-panel">
        <h5>Usuario</h5>
        <p>Acceso de lectura y chat con documentos.</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RolePanels',
  props: { roles: { type: Array, default: () => [] } }
}
</script>

<style scoped>
.role-panels { padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px; color: #e6eef8 }
.roles-list { display:flex; gap:8px; margin-bottom:8px }
.role-chip { background: rgba(77,108,250,0.12); padding:4px 8px; border-radius:6px; font-size:13px }
.panels { display:flex; gap:12px; flex-wrap:wrap }
.panel { background: rgba(255,255,255,0.02); padding:8px; border-radius:8px; min-width:160px }
.panel h5 { margin-bottom:8px; font-size:14px }
.panel button { display:block; margin-bottom:6px; padding:6px 8px; border-radius:6px; border:none; background:#2b3a8a; color:white; cursor:pointer }
</style>