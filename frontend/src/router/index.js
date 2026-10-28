import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginView from '@/views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/dispositivo', name: 'dispositivo', component: () => import('@/views/DispositivoView.vue'), meta: { public: true, device: true } },

    // Carta digital del cliente: sin sesión, el contexto sale del token del QR (doc 10A)
    { path: '/q/:token', name: 'carta', component: () => import('@/views/publico/CartaView.vue'), props: true, meta: { public: true } },
    { path: '/pagar', name: 'pagar', component: () => import('@/views/publico/PagarView.vue'), meta: { public: true } },
    { path: '/pasarela-simulada/:referencia', name: 'pasarela-simulada', component: () => import('@/views/publico/PasarelaSimuladaView.vue'), props: true, meta: { public: true } },
    { path: '/pedido/:seguimiento', name: 'seguimiento', component: () => import('@/views/publico/SeguimientoView.vue'), props: true, meta: { public: true } },

    { path: '/', name: 'inicio', component: () => import('@/views/InicioView.vue') },

    // Pantallas de operación, a pantalla completa
    { path: '/mesas', name: 'mesero', component: () => import('@/views/operacion/MeseroView.vue'), meta: { permiso: 'ordenes.crear_mesa' } },
    { path: '/mesas/:mesaId', name: 'mesa', component: () => import('@/views/operacion/MesaView.vue'), props: true, meta: { permiso: 'ordenes.crear_mesa' } },
    { path: '/mostrador', name: 'mostrador', component: () => import('@/views/operacion/MostradorView.vue'), meta: { permiso: 'ordenes.crear_externa' } },
    { path: '/caja', name: 'caja', component: () => import('@/views/operacion/CajaView.vue'), meta: { permiso: ['caja.cobrar', 'caja.cobrar_externas', 'caja.turno', 'caja.ver'] } },
    { path: '/entregas', name: 'entregas', component: () => import('@/views/operacion/EntregasView.vue'), meta: { permiso: ['domicilios.despachar', 'domicilios.entregar'] } },
    { path: '/bodega', name: 'bodega', component: () => import('@/views/operacion/BodegaView.vue'), meta: { permiso: ['inventario.movimientos', 'inventario.contar', 'compras.recibir'] } },
    { path: '/produccion', name: 'cocina', component: () => import('@/views/operacion/CocinaInicioView.vue'), meta: { permiso: 'cocina.operar' } },
    { path: '/produccion/:puntoId', name: 'cocina-punto', component: () => import('@/views/operacion/CocinaView.vue'), props: true, meta: { permiso: 'cocina.operar' } },

    // Administración del restaurante
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { permiso: ['catalogo.gestionar', 'estructura.gestionar', 'usuarios.gestionar'] },
      children: [
        { path: '', name: 'admin', component: () => import('@/views/admin/HoyView.vue') },
        { path: 'zonas', name: 'admin-zonas', component: () => import('@/views/admin/ZonasView.vue'), meta: { permiso: 'estructura.gestionar' } },
        { path: 'mesas', name: 'admin-mesas', component: () => import('@/views/admin/MesasView.vue'), meta: { permiso: 'estructura.gestionar' } },
        { path: 'qr', name: 'admin-qr', component: () => import('@/views/admin/QrView.vue'), meta: { permiso: 'qr.gestionar' } },
        { path: 'productos', name: 'admin-productos', component: () => import('@/views/admin/ProductosView.vue'), meta: { permiso: 'catalogo.gestionar' } },
        { path: 'categorias', name: 'admin-categorias', component: () => import('@/views/admin/CategoriasView.vue'), meta: { permiso: 'catalogo.gestionar' } },
        { path: 'modificadores', name: 'admin-modificadores', component: () => import('@/views/admin/ModificadoresView.vue'), meta: { permiso: 'catalogo.gestionar' } },
        { path: 'cartas', name: 'admin-cartas', component: () => import('@/views/admin/CartasView.vue'), meta: { permiso: 'catalogo.gestionar' } },
        { path: 'dispositivos', name: 'admin-dispositivos', component: () => import('@/views/admin/DispositivosView.vue'), meta: { permiso: 'estructura.gestionar' } },
        { path: 'produccion', name: 'admin-puntos', component: () => import('@/views/admin/PuntosView.vue'), meta: { permiso: 'estructura.gestionar' } },
        { path: 'usuarios', name: 'admin-usuarios', component: () => import('@/views/admin/UsuariosView.vue'), meta: { permiso: 'usuarios.gestionar' } },
        { path: 'restaurante', name: 'admin-restaurante', component: () => import('@/views/admin/RestauranteView.vue'), meta: { permiso: ['restaurante.configurar', 'restaurante.pausar'] } },
        { path: 'clientes', name: 'admin-clientes', component: () => import('@/views/admin/ClientesView.vue'), meta: { permiso: 'clientes.gestionar' } },
        { path: 'inventario', name: 'admin-inventario', component: () => import('@/views/admin/InventarioView.vue'), meta: { permiso: ['inventario.ver', 'inventario.gestionar'] } },
        { path: 'recetas', name: 'admin-recetas', component: () => import('@/views/admin/RecetasView.vue'), meta: { permiso: ['inventario.ver', 'inventario.gestionar'] } },
        { path: 'plan', name: 'admin-plan', component: () => import('@/views/admin/PlanView.vue'), meta: { permiso: 'restaurante.configurar' } },
        { path: 'liquidaciones', name: 'admin-liquidaciones', component: () => import('@/views/admin/LiquidacionesView.vue'), meta: { permiso: ['liquidaciones.gestionar', 'domicilios.liquidar'] } },
        { path: 'cupones', name: 'admin-cupones', component: () => import('@/views/admin/CuponesView.vue'), meta: { permiso: ['cupones.gestionar', 'cupones.ver'] } },
        { path: 'pagos-linea', name: 'admin-pagos-linea', component: () => import('@/views/admin/PagosLineaView.vue'), meta: { permiso: ['pagos_linea.configurar', 'pagos_linea.conciliar', 'pagos_linea.reembolsar'] } },
        { path: 'avisos', name: 'admin-avisos', component: () => import('@/views/admin/AvisosView.vue'), meta: { permiso: 'notificaciones.configurar' } },
        { path: 'domicilios', name: 'admin-domicilios', component: () => import('@/views/admin/DomiciliosView.vue'), meta: { permiso: 'domicilios.gestionar' } },
        { path: 'compras', name: 'admin-compras', component: () => import('@/views/admin/ComprasView.vue'), meta: { permiso: ['compras.ver', 'compras.registrar', 'compras.recibir'] } },
        { path: 'proveedores', name: 'admin-proveedores', component: () => import('@/views/admin/ProveedoresView.vue'), meta: { permiso: ['compras.ver', 'proveedores.gestionar'] } },
        { path: 'impuestos', name: 'admin-impuestos', component: () => import('@/views/admin/ImpuestosView.vue'), meta: { permiso: 'impuestos.configurar' } },
        { path: 'facturacion', name: 'admin-facturacion', component: () => import('@/views/admin/FacturacionView.vue'), meta: { permiso: ['facturacion.ver', 'facturacion.configurar'] } },
        { path: 'reportes', name: 'admin-reportes', component: () => import('@/views/admin/ReportesView.vue'), meta: { permiso: 'reportes.ver' } },
        { path: 'reportes/mesero', name: 'informe-mesero', component: () => import('@/views/InformeMeseroView.vue'), meta: { permiso: 'reportes.ver' } },
        { path: 'auditoria', name: 'admin-auditoria', component: () => import('@/views/admin/AuditoriaView.vue'), meta: { permiso: 'auditoria.ver' } },
      ],
    },

    { path: '/mis-liquidaciones', name: 'mis-liquidaciones', component: () => import('@/views/MisLiquidacionesView.vue'), meta: { permiso: 'liquidaciones.ver_propia' } },
    { path: '/mi-informe', name: 'mi-informe', component: () => import('@/views/InformeMeseroView.vue'), meta: { permiso: 'reportes.propio' } },

    // Consola del proveedor del software
    { path: '/plataforma', name: 'plataforma', component: () => import('@/views/plataforma/EmpresasView.vue'), meta: { permiso: 'plataforma.gestionar' } },

    { path: '/:pathMatch(.*)*', redirect: { name: 'inicio' } },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if ((to.name === 'login' || to.name === 'dispositivo') && auth.isAuthenticated) return { name: 'inicio' }
    return true
  }
  if (!auth.isAuthenticated) {
    if (auth.deviceToken) return { name: 'dispositivo' }
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  // Cada ruta exige su permiso; la del padre y la de la hija
  const required = to.matched.map((record) => record.meta.permiso).filter(Boolean)
  if (required.some((permiso) => !auth.can(permiso))) {
    return { name: 'inicio' }
  }
  return true
})

export default router
