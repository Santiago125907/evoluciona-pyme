"""
Script para crear workspace y servicios de ejemplo en el portal.
Ejecutar con:
  bench --site comando.evolucionapyme.cl execute evoluciona_pyme_v2.evoluciona_pyme_v2.setup_portal_data.run
"""
import frappe


# ── Workspace ──────────────────────────────────────────────────────────────────

def create_workspace():
    label = "Portal Evoluciona Pyme"
    if frappe.db.exists("Workspace", label):
        frappe.delete_doc("Workspace", label, force=True, ignore_permissions=True)
        frappe.db.commit()

    ws = frappe.get_doc({
        "doctype": "Workspace",
        "label": label,
        "title": label,
        "module": "Evoluciona Pyme V2",
        "public": 1,
        "icon": "home",
        "links": [
            # ── Servicios Portal ──
            {"type": "Card Break", "label": "Servicios Portal",       "hidden": 0},
            {"type": "Link", "label": "Servicios Portal",         "link_type": "DocType", "link_to": "Servicio_Portal",           "onboard": 1},
            {"type": "Link", "label": "Solicitudes de Servicios", "link_type": "DocType", "link_to": "Solicitud_Servicio_Portal",  "onboard": 1},
            # ── Declaraciones ──
            {"type": "Card Break", "label": "Declaraciones",          "hidden": 0},
            {"type": "Link", "label": "Declaraciones Mensuales",  "link_type": "DocType", "link_to": "Declaracion_Mensual",        "onboard": 1},
            {"type": "Link", "label": "Postergaciones IVA",       "link_type": "DocType", "link_to": "Postergacion_IVA"},
            {"type": "Link", "label": "Registro Remuneraciones",  "link_type": "DocType", "link_to": "Registro_Remuneraciones"},
            # ── Contabilidad ──
            {"type": "Card Break", "label": "Contabilidad",           "hidden": 0},
            {"type": "Link", "label": "Libro de Compras",         "link_type": "DocType", "link_to": "Libro_de_Compras_Cliente"},
            {"type": "Link", "label": "Libro de Honorarios",      "link_type": "DocType", "link_to": "Libro_de_Honorarios_Cliente"},
            {"type": "Link", "label": "Libro de Gastos",          "link_type": "DocType", "link_to": "Libro_de_Gastos_Cliente"},
            {"type": "Link", "label": "Cobranza Cliente",         "link_type": "DocType", "link_to": "Cobranza_Cliente"},
            # ── Clientes & Portal ──
            {"type": "Card Break", "label": "Clientes y Portal",      "hidden": 0},
            {"type": "Link", "label": "Fichas de Clientes",       "link_type": "DocType", "link_to": "Ficha_Cliente",             "onboard": 1},
            {"type": "Link", "label": "Sesiones Portal",          "link_type": "DocType", "link_to": "Portal_Session"},
        ],
    })
    ws.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"✅ Workspace '{label}' creado")


# ── Servicios de ejemplo ───────────────────────────────────────────────────────

SERVICIOS = [
    {
        "nombre": "Creación de Empresas",
        "descripcion_corta": "Constituye tu empresa en línea. Sociedad SPA, EIRL o limitada con todo incluido.",
        "descripcion_larga": "Nos encargamos de todo el proceso de constitución de tu empresa. Desde la redacción de los estatutos hasta la obtención del RUT, inscripción en el Registro de Comercio y primera declaración de inicio de actividades. Sin complicaciones, sin filas.",
        "categoria": "Legal",
        "tipo": "Propio",
        "activo": 1,
        "destacado": 1,
        "orden": 1,
        "icono": "Edificio",
        "color": "#3B82F6",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [
            {"nombre_plan": "SPA Básica",     "precio": 150000, "precio_unidad": "única vez", "descripcion": "Constitución SPA con 1 socio, estatutos estándar, RUT y inicio de actividades", "destacado": 0},
            {"nombre_plan": "SPA Pro",        "precio": 250000, "precio_unidad": "única vez", "descripcion": "Constitución SPA hasta 5 socios, estatutos personalizados, poderes notariales incluidos", "destacado": 1},
            {"nombre_plan": "Limitada",       "precio": 320000, "precio_unidad": "única vez", "descripcion": "Sociedad de Responsabilidad Limitada, ideal para negocios familiares o con socios igualitarios", "destacado": 0},
        ],
    },
    {
        "nombre": "Página Web Profesional",
        "descripcion_corta": "Diseño y desarrollo de sitios web modernos, rápidos y con dominio propio.",
        "descripcion_larga": "Creamos tu presencia digital con un sitio web profesional adaptado a tu negocio. Incluye diseño personalizado, dominio .cl, hosting por 1 año, formulario de contacto y optimización para móviles. Entregamos en 7 días hábiles.",
        "categoria": "Marketing",
        "tipo": "Socio",
        "activo": 1,
        "destacado": 1,
        "orden": 2,
        "icono": "Computador",
        "color": "#F97316",
        "nombre_socio": "WebPyme",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [
            {"nombre_plan": "Landing Page",  "precio": 280000, "precio_unidad": "única vez", "descripcion": "1 página de presentación + formulario de contacto + dominio + hosting 1 año", "destacado": 0},
            {"nombre_plan": "Sitio Completo","precio": 490000, "precio_unidad": "única vez", "descripcion": "Hasta 5 secciones, blog, galería, formularios y SEO básico", "destacado": 1},
            {"nombre_plan": "E-commerce",    "precio": 890000, "precio_unidad": "única vez", "descripcion": "Tienda online completa con carrito, pasarela de pagos y gestión de productos", "destacado": 0},
        ],
    },
    {
        "nombre": "Trámites Adicionales SII",
        "descripcion_corta": "Modificaciones de actividades, cambio de razón social, timbraje de documentos y más.",
        "descripcion_larga": "Realizamos por ti todos los trámites ante el SII que tu empresa necesite: modificación o ampliación de giro, cambio de razón social o domicilio, timbraje electrónico de boletas y facturas, solicitud de certificados tributarios y más. Rápido y sin errores.",
        "categoria": "Contabilidad",
        "tipo": "Propio",
        "activo": 1,
        "destacado": 0,
        "orden": 3,
        "icono": "Documento",
        "color": "#00C4CC",
        "precio": 35000,
        "precio_oferta": 0,
        "precio_unidad": "por trámite",
        "accion": "Formulario",
        "planes": [],
    },
    {
        "nombre": "Asesoría Laboral RRHH",
        "descripcion_corta": "Liquidaciones de sueldo, contratos, finiquitos y cumplimiento laboral completo.",
        "descripcion_larga": "Gestionamos todos los aspectos laborales de tu empresa: elaboración de contratos de trabajo, liquidaciones de sueldo mensuales, cálculo de finiquitos, previred, mutualidad y cumplimiento de normativa laboral vigente. Ideal para empresas con trabajadores.",
        "categoria": "RRHH",
        "tipo": "Propio",
        "activo": 1,
        "destacado": 0,
        "orden": 4,
        "icono": "Personas",
        "color": "#8B5CF6",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [
            {"nombre_plan": "1-3 trabajadores",  "precio": 45000, "precio_unidad": "/ mes", "descripcion": "Liquidaciones, contratos, previred y AFP para hasta 3 trabajadores", "destacado": 0},
            {"nombre_plan": "4-10 trabajadores", "precio": 85000, "precio_unidad": "/ mes", "descripcion": "Gestión completa para hasta 10 trabajadores + asesoría laboral mensual", "destacado": 1},
            {"nombre_plan": "+10 trabajadores",  "precio": 140000,"precio_unidad": "/ mes", "descripcion": "Hasta 25 trabajadores + reporte de dotación + capacitaciones SENCE", "destacado": 0},
        ],
    },
    {
        "nombre": "Marketing Digital",
        "descripcion_corta": "Redes sociales, Google Ads y estrategia digital para hacer crecer tu negocio.",
        "descripcion_larga": "Nuestro equipo de marketing digital gestiona tu presencia en redes sociales, crea campañas de publicidad en Google y Meta, y desarrolla una estrategia de contenido alineada con los objetivos de tu negocio. Informes mensuales incluidos.",
        "categoria": "Marketing",
        "tipo": "Socio",
        "activo": 1,
        "destacado": 0,
        "orden": 5,
        "icono": "Gráfico",
        "color": "#F97316",
        "nombre_socio": "Creativo Digital",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [
            {"nombre_plan": "Social Media",   "precio": 120000, "precio_unidad": "/ mes", "descripcion": "Gestión de 2 redes sociales + 12 publicaciones mensuales + informes", "destacado": 0},
            {"nombre_plan": "Digital Full",   "precio": 250000, "precio_unidad": "/ mes", "descripcion": "Social media + Google Ads + Meta Ads + estrategia SEO + reportes semanales", "destacado": 1},
        ],
    },
    {
        "nombre": "Firma Electrónica Avanzada",
        "descripcion_corta": "Firma documentos legalmente válidos desde cualquier dispositivo, sin papel.",
        "descripcion_larga": "Con nuestra solución de firma electrónica avanzada puedes firmar contratos, finiquitos, poderes y cualquier documento legal con plena validez jurídica. Compatible con todos los dispositivos y sin necesidad de notaría para la mayoría de los actos.",
        "categoria": "Legal",
        "tipo": "Socio",
        "activo": 1,
        "destacado": 0,
        "orden": 6,
        "icono": "Cerradura",
        "color": "#3B82F6",
        "nombre_socio": "FirmaYa",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [
            {"nombre_plan": "Starter",    "precio": 15000, "precio_oferta": 9900, "precio_unidad": "/ mes", "descripcion": "Hasta 10 firmas mensuales", "destacado": 0},
            {"nombre_plan": "Pyme",       "precio": 35000, "precio_oferta": 0,    "precio_unidad": "/ mes", "descripcion": "Hasta 50 firmas mensuales + gestión de documentos", "destacado": 1},
            {"nombre_plan": "Ilimitado",  "precio": 65000, "precio_oferta": 0,    "precio_unidad": "/ mes", "descripcion": "Firmas ilimitadas + API + workflow de aprobaciones", "destacado": 0},
        ],
    },
    {
        "nombre": "Software de Gestión Pyme",
        "descripcion_corta": "ERP en la nube para gestionar ventas, inventario, compras y finanzas en un solo lugar.",
        "descripcion_larga": "Implementamos y capacitamos a tu equipo en el uso de Frappe/ERPNext, el sistema ERP open-source más completo del mercado. Gestiona cotizaciones, órdenes de venta, inventario, compras, contabilidad y recursos humanos desde la nube.",
        "categoria": "Tecnología",
        "tipo": "Propio",
        "activo": 1,
        "destacado": 0,
        "orden": 7,
        "icono": "Engranaje",
        "color": "#10B981",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [
            {"nombre_plan": "Básico",    "precio": 89000, "precio_unidad": "/ mes", "descripcion": "Hasta 3 usuarios, módulos de ventas e inventario", "destacado": 0},
            {"nombre_plan": "Estándar",  "precio": 169000,"precio_unidad": "/ mes", "descripcion": "Hasta 10 usuarios, todos los módulos + soporte prioritario", "destacado": 1},
            {"nombre_plan": "Avanzado",  "precio": 290000,"precio_unidad": "/ mes", "descripcion": "Usuarios ilimitados + personalización + capacitación incluida", "destacado": 0},
        ],
    },
    {
        "nombre": "Seguro de Cesantía y Protección",
        "descripcion_corta": "Asesoría en seguros laborales, ACHS y protección financiera para tu empresa.",
        "descripcion_larga": "Te asesoramos en la contratación de seguros de cesantía complementarios, seguros de vida para trabajadores, protección de deudas y seguros de activos para tu empresa. Comparamos opciones del mercado y te recomendamos la mejor cobertura al mejor precio.",
        "categoria": "RRHH",
        "tipo": "Socio",
        "activo": 1,
        "destacado": 0,
        "orden": 8,
        "icono": "Escudo",
        "color": "#8B5CF6",
        "nombre_socio": "Asesores Seguros",
        "precio": 0,
        "precio_oferta": 0,
        "precio_unidad": "",
        "accion": "Formulario",
        "planes": [],
    },
]


def create_servicios():
    created = 0
    for data in SERVICIOS:
        planes = data.pop("planes", [])
        nombre = data["nombre"]

        # Verificar si ya existe
        if frappe.db.exists("Servicio_Portal", {"nombre": nombre}):
            print(f"  ⏭  '{nombre}' ya existe, omitiendo")
            continue

        doc = frappe.get_doc({"doctype": "Servicio_Portal", **data})
        for p in planes:
            doc.append("planes", p)
        doc.insert(ignore_permissions=True)
        created += 1
        print(f"  ✅ '{nombre}' creado")

    frappe.db.commit()
    print(f"\n✅ {created} servicio(s) creado(s)")


# ── Punto de entrada ───────────────────────────────────────────────────────────

def add_notificacion_to_workspace():
    """Agrega Notificacion_Push_Portal al workspace si no está."""
    ws_name = "Portal Evoluciona Pyme"
    if not frappe.db.exists("Workspace", ws_name):
        print("Workspace no encontrado")
        return
    ws = frappe.get_doc("Workspace", ws_name)
    # Verificar si ya existe el link
    for link in ws.links:
        if getattr(link, 'link_to', '') == 'Notificacion_Push_Portal':
            print("Ya existe el link")
            return
    # Agregar al grupo de Servicios Portal
    ws.append("links", {
        "type": "Link",
        "label": "Notificaciones Push",
        "link_type": "DocType",
        "link_to": "Notificacion_Push_Portal",
        "onboard": 0,
    })
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    print("✅ Notificacion_Push_Portal agregado al workspace")


def run():
    print("\n=== Configurando Portal Evoluciona Pyme ===\n")
    print("1. Creando workspace...")
    create_workspace()
    print("\n2. Creando servicios de ejemplo...")
    create_servicios()
    print("\n=== ¡Listo! ===\n")
