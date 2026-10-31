<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { postData } from '@/services/api'

const auth = useAuthStore()

// Aviso del estado de la cuenta del servicio: mora, pago por vencer o prueba por terminar (doc 42)
const cuenta = ref(null)
onMounted(async () => {
  if (!auth.can('restaurante.configurar')) return
  const plan = await postData('/restaurante/plan').catch(() => null)
  const c = plan?.cuenta
  if (c && (['en_mora', 'por_vencer', 'prueba_vencida'].includes(c.estado) || (c.estado === 'prueba' && c.dias !== null && c.dias <= 7))) cuenta.value = c
})

// Aviso de lo que falta para abrir (doc 41); se actualiza al moverse entre pantallas hasta terminar el ensayo
const marcha = ref(null)
async function cargarMarcha() {
  if (!auth.can('restaurante.configurar') || marcha.value?.listo) return
  marcha.value = await postData('/restaurante/puesta_en_marcha').catch(() => marcha.value)
}
const rutaActual = useRoute()
watch(() => rutaActual.name, cargarMarcha, { immediate: true })

// Secciones de administración agrupadas como las trabaja el dueño: operación, local, carta, personal
const GRUPOS = [
  {
    titulo: 'Operación',
    items: [
      { name: 'admin', label: 'Hoy', permiso: ['ordenes.ver', 'reportes.ver'] },
      { name: 'admin-reportes', label: 'Reportes', permiso: 'reportes.ver' },
      { name: 'admin-exportar', label: 'Exportar datos', permiso: 'datos.exportar' },
    ],
  },
  {
    titulo: 'El local',
    items: [
      { name: 'admin-zonas', label: 'Zonas', permiso: 'estructura.gestionar' },
      { name: 'admin-mesas', label: 'Mesas', permiso: 'estructura.gestionar' },
      { name: 'admin-qr', label: 'Códigos QR', permiso: 'qr.gestionar' },
      { name: 'admin-puntos', label: 'Cocina y bar', permiso: 'estructura.gestionar' },
      { name: 'admin-dispositivos', label: 'Dispositivos', permiso: 'estructura.gestionar' },
      { name: 'admin-domicilios', label: 'Domicilios', permiso: 'domicilios.gestionar' },
    ],
  },
  {
    titulo: 'La carta',
    items: [
      { name: 'admin-productos', label: 'Productos', permiso: 'catalogo.gestionar' },
      { name: 'admin-categorias', label: 'Categorías', permiso: 'catalogo.gestionar' },
      { name: 'admin-modificadores', label: 'Modificadores', permiso: 'catalogo.gestionar' },
      { name: 'admin-cartas', label: 'Cartas', permiso: 'catalogo.gestionar' },
    ],
  },
  {
    titulo: 'Inventario',
    items: [
      { name: 'admin-inventario', label: 'Existencias', permiso: ['inventario.ver', 'inventario.gestionar'] },
      { name: 'admin-recetas', label: 'Recetas y costos', permiso: ['inventario.ver', 'inventario.gestionar'] },
      { name: 'admin-compras', label: 'Compras', permiso: ['compras.ver', 'compras.registrar'] },
      { name: 'admin-proveedores', label: 'Proveedores', permiso: ['compras.ver', 'proveedores.gestionar'] },
      { name: 'bodega', label: 'Mermas y conteos', permiso: ['inventario.movimientos', 'inventario.contar'] },
    ],
  },
  {
    titulo: 'Restaurante',
    items: [
      { name: 'admin-usuarios', label: 'Personal', permiso: 'usuarios.gestionar' },
      { name: 'admin-clientes', label: 'Clientes', permiso: 'clientes.gestionar' },
      { name: 'admin-liquidaciones', label: 'Propinas y liquidaciones', permiso: ['liquidaciones.gestionar', 'domicilios.liquidar'] },
      { name: 'admin-cupones', label: 'Cupones', permiso: ['cupones.gestionar', 'cupones.ver'] },
      { name: 'admin-avisos', label: 'Avisos por WhatsApp', permiso: 'notificaciones.configurar' },
      { name: 'admin-pagos-linea', label: 'Pagos en línea', permiso: ['pagos_linea.configurar', 'pagos_linea.conciliar', 'pagos_linea.reembolsar'] },
      { name: 'admin-facturacion', label: 'Facturación', permiso: ['facturacion.ver', 'facturacion.configurar'] },
      { name: 'admin-impuestos', label: 'Impuestos', permiso: 'impuestos.configurar' },
      { name: 'admin-marcha', label: 'Puesta en marcha', permiso: 'restaurante.configurar' },
      { name: 'admin-plan', label: 'Mi plan', permiso: 'restaurante.configurar' },
      { name: 'admin-restaurante', label: 'Configuración', permiso: ['restaurante.configurar', 'restaurante.pausar'] },
      { name: 'admin-auditoria', label: 'Auditoría', permiso: 'auditoria.ver' },
    ],
  },
]

const grupos = computed(() =>
  GRUPOS.map((g) => ({ ...g, items: g.items.filter((i) => auth.can(i.permiso)) })).filter((g) => g.items.length))
</script>

<template>
  <div class="admin">
    <aside class="menu no-print">
      <RouterLink :to="{ name: 'inicio', query: { menu: 1 } }" class="marca">
        <strong>{{ auth.restaurante?.nombre }}</strong>
        <span>Cambiar de pantalla</span>
      </RouterLink>
      <nav aria-label="Administración">
        <div v-for="grupo in grupos" :key="grupo.titulo" class="grupo">
          <p class="grupo-titulo">{{ grupo.titulo }}</p>
          <RouterLink v-for="item in grupo.items" :key="item.name" :to="{ name: item.name }" class="enlace"
                      exact-active-class="activo">
            {{ item.label }}
          </RouterLink>
        </div>
      </nav>
      <button class="salir" type="button" @click="auth.logout()">Salir ({{ auth.user?.nombre }})</button>
    </aside>
    <main class="contenido">
      <p v-if="marcha && !marcha.listo && $route.name !== 'admin-marcha'" class="aviso-marcha" role="status">
        <strong>Puesta en marcha:</strong> {{ marcha.hechos }} de {{ marcha.total }} pasos.
        <RouterLink :to="{ name: 'admin-marcha' }">Continuar</RouterLink>
      </p>
      <p v-if="cuenta && $route.name !== 'admin-plan'" class="aviso-cuenta" :class="cuenta.estado" role="status">
        {{ cuenta.estado === 'en_mora' ? 'Tu pago del servicio está pendiente.' : cuenta.texto + '.' }}
        <RouterLink :to="{ name: 'admin-plan' }">Ver mi plan</RouterLink>
      </p>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin {
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr);
  min-height: 100dvh;
}

.menu {
  position: sticky;
  top: 0;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--tinta);
  color: #fff;
  overflow-y: auto;
}

.marca {
  display: flex;
  flex-direction: column;
  padding: var(--space-2);
  text-decoration: none;
}

.marca strong {
  font-size: var(--text-xl);
  font-stretch: 72%;
  line-height: 1.1;
}

.marca span {
  color: #aab4b8;
  font-size: var(--text-sm);
}

.grupo {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: var(--space-3);
}

.grupo-titulo {
  padding: var(--space-1) var(--space-2);
  color: #8f9a9f;
  font-size: var(--text-sm);
}

.enlace {
  display: flex;
  align-items: center;
  min-height: 2.75rem;
  padding: 0 var(--space-3);
  border-radius: var(--radio-sm);
  color: #e6eaeb;
  text-decoration: none;
  font-weight: 500;
}

.enlace:hover {
  background: var(--tinta-suave);
}

.enlace.activo {
  background: var(--papel);
  color: var(--tinta);
  font-weight: 700;
}

.salir {
  margin-top: auto;
  min-height: var(--toque);
  border: 1px solid #4a5458;
  border-radius: var(--radio-sm);
  background: transparent;
  color: #cfd6d9;
  cursor: pointer;
}

.contenido {
  padding: var(--space-6) var(--space-5);
  max-width: 76rem;
  width: 100%;
}

@media (max-width: 56rem) {
  .admin {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto 1fr;
  }

  .menu {
    position: sticky;
    top: 0;
    z-index: 10;
    height: auto;
    flex-direction: row;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    overflow-x: auto;
  }

  .marca span,
  .grupo-titulo,
  .salir {
    display: none;
  }

  .marca strong {
    font-size: var(--text-lg);
    white-space: nowrap;
  }

  nav,
  .grupo {
    display: flex;
    flex-direction: row;
    gap: 2px;
    margin: 0;
  }

  .enlace {
    white-space: nowrap;
  }

  .contenido {
    padding: var(--space-5) var(--space-4);
  }
}

.aviso-marcha {
  margin-bottom: var(--space-4);
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--accion);
  border-radius: var(--radio-sm);
  background: var(--superficie);
}

.aviso-cuenta {
  margin-bottom: var(--space-4);
  padding: var(--space-2) var(--space-3);
  border-left: 4px solid var(--estado-pendiente);
  border-radius: var(--radio-sm);
  background: var(--estado-pendiente-suave);
}

.aviso-cuenta.en_mora,
.aviso-cuenta.prueba_vencida {
  border-left-color: var(--estado-cancelado);
  background: var(--estado-cancelado-suave);
}
</style>
