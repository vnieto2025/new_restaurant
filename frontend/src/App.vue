<script setup>
import { onMounted, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ToastHost from '@/components/ToastHost.vue'
import PrintHost from '@/components/PrintHost.vue'
import AvisoAcceso from '@/components/AvisoAcceso.vue'
import AvisoPractica from '@/components/AvisoPractica.vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { useInactivity } from '@/composables/useInactivity'

// Tablet compartida: tras unos minutos sin uso vuelve al PIN (las pantallas de cocina no se bloquean)
const MINUTOS_INACTIVIDAD = 3
const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

useInactivity(
  () => auth.isAuthenticated && auth.dispositivo?.tipo === 'zona' && !route.meta.public,
  MINUTOS_INACTIVIDAD,
  () => {
    toast.info('Se cerró tu identificación por inactividad.')
    auth.logout()
  },
)

// Restaurante suspendido o cancelado: se esconde lo que guarda datos (ADR-055); la API igual lo rechaza
watchEffect(() => {
  const lectura = auth.isAuthenticated && !route.meta.public && !!auth.acceso && auth.acceso.modo !== 'completo'
  document.documentElement.classList.toggle('solo-lectura', lectura)
})

// La empresa empezó a exigir la verificación en dos pasos con la sesión abierta (ADR-054)
watchEffect(() => {
  if (auth.isAuthenticated && auth.seguridad.debe_activar && route.name && route.name !== 'cuenta') router.replace({ name: 'cuenta' })
})

// Al abrir la aplicación con una sesión guardada: el contrato pudo cambiar mientras tanto
onMounted(() => {
  if (auth.isAuthenticated) auth.refresh().catch(() => {})
})
</script>

<template>
  <AvisoPractica />
  <AvisoAcceso />
  <RouterView />
  <ToastHost />
  <PrintHost />
</template>
