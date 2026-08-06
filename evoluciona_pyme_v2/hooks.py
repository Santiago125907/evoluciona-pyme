app_name = "evoluciona_pyme_v2"
app_title = "Evoluciona Pyme V2"
app_publisher = "Santiago Romero"
app_description = "Sistema de Contabilidad y Gestión de Clientes para Evoluciona Pyme"
app_email = "sromero1808@gmail.com"
app_license = "mit"
app_home = "/app/panel_app"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "evoluciona_pyme_v2",
		"logo": "/assets/evoluciona_pyme_v2/images/logo.svg",
		"title": "Evoluciona Pyme",
		"route": "/app/panel_app",
		"has_permission": "evoluciona_pyme_v2.evoluciona_pyme_v2.api.has_app_permission"
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/evoluciona_pyme_v2/css/evoluciona_pyme_v2.css"
# app_include_js = "/assets/evoluciona_pyme_v2/js/evoluciona_pyme_v2.js"

# include js, css files in header of web template
# web_include_css = "/assets/evoluciona_pyme_v2/css/evoluciona_pyme_v2.css"
# web_include_js = "/assets/evoluciona_pyme_v2/js/evoluciona_pyme_v2.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "evoluciona_pyme_v2/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "evoluciona_pyme_v2/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "evoluciona_pyme_v2.utils.jinja_methods",
# 	"filters": "evoluciona_pyme_v2.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "evoluciona_pyme_v2.install.before_install"
after_install = "evoluciona_pyme_v2.evoluciona_pyme_v2.setup.after_install"

# Uninstallation
# ------------

# before_uninstall = "evoluciona_pyme_v2.uninstall.before_uninstall"
# after_uninstall = "evoluciona_pyme_v2.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "evoluciona_pyme_v2.utils.before_app_install"
# after_app_install = "evoluciona_pyme_v2.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "evoluciona_pyme_v2.utils.before_app_uninstall"
# after_app_uninstall = "evoluciona_pyme_v2.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "evoluciona_pyme_v2.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Ficha_Cliente": {
		"after_insert": [
			"evoluciona_pyme_v2.evoluciona_pyme_v2.drive.crear_carpeta_cliente",
			"evoluciona_pyme_v2.evoluciona_pyme_v2.asesores.auto_asignar_asesor",
			"evoluciona_pyme_v2.evoluciona_pyme_v2.rcv_api.agregar_cliente_a_tabla_rcv",
		],
		"on_update": [
			"evoluciona_pyme_v2.evoluciona_pyme_v2.portal_auth.enviar_bienvenida_portal",
			"evoluciona_pyme_v2.evoluciona_pyme_v2.rcv_api.agregar_cliente_a_tabla_rcv",
		]
	},
	"Declaracion_Mensual": {
		"on_update": [
			"evoluciona_pyme_v2.evoluciona_pyme_v2.portal_notif.on_declaracion_update",
		]
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	# Cron 1: crea Declaracion_Mensual + Borrador_F29 (una vez al mes, día+hora configurables)
	"hourly_long": [
		"evoluciona_pyme_v2.evoluciona_pyme_v2.tasks.dispatcher_cron"
	],
	# Cron 2: dispara webhooks de descarga de Libro de Compras y Ventas (una vez al día)
	"hourly": [
		"evoluciona_pyme_v2.evoluciona_pyme_v2.tasks.dispatcher_libros"
	],
	# Cron 3: recordatorio de vencimiento — corre cada día a las 9am
	# Cron 4: acuse de recibo inteligente — corre solo el último día del mes, hora configurable
	"daily": [
		"evoluciona_pyme_v2.evoluciona_pyme_v2.portal_notif.recordatorio_vencimiento",
		"evoluciona_pyme_v2.evoluciona_pyme_v2.tasks.dispatcher_acuse"
	],
}

# Testing
# -------

# before_tests = "evoluciona_pyme_v2.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "evoluciona_pyme_v2.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "evoluciona_pyme_v2.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["evoluciona_pyme_v2.utils.before_request"]
# after_request = ["evoluciona_pyme_v2.utils.after_request"]

# Job Events
# ----------
# before_job = ["evoluciona_pyme_v2.utils.before_job"]
# after_job = ["evoluciona_pyme_v2.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"evoluciona_pyme_v2.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
fixtures = [
	{"dt": "Custom HTML Block", "filters": [["name", "in", ["Dashboard Evoluciona Pyme"]]]},
	{"dt": "Configuracion_Codigo_F29", "filters": [["name", "in", ["62","155","49","151","48","504","532","528","520","562","510","759","111","502","142"]]]},
]
