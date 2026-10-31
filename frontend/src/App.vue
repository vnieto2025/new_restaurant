<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import ToastHost from '@/components/ToastHost.vue'
import PrintHost from '@/components/PrintHost.vue'
import AvisoAcceso from '@/components/AvisoAcceso.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { useInactivity } from '@/composables/useInactivity'

// Tablet compartida: tras unos minutos sin uso vuelve al PIN (las pantallas de cocina no se bloquean)
const MINUTOS_INACTIVIDAD = 3
const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()

useInactivity(
  () => auth.isAuthenticated && auth.dispositivo?.tipo === 'zona' && !route.meta.public,
  MINUTOS_INACTIVIDAD,
  () => {
    toast.info('Se cerró tu identificación por inactividad.')
    auth.logout()
  },
)

// Al abrir la aplicación con una sesión guardada: el contrato pudo cambiar mientras tanto
onMounted(() => {
  if (auth.isAuthenticated) auth.refresh().catch(() => {})
})
</script>

<template>
  <AvisoAcceso />
  <RouterView />
  <ToastHost />
  <PrintHost />
</template>
