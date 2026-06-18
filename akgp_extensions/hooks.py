app_name = "akgp_extensions"
app_title = "AKGP Extensions"
app_publisher = "WildanYR"
app_description = "Ekstensi ERPNext untuk menerapkan workflow dari Akgp"
app_email = "wildanyahya99@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "akgp_extensions",
# 		"logo": "/assets/akgp_extensions/logo.png",
# 		"title": "AKGP Extensions",
# 		"route": "/akgp_extensions",
# 		"has_permission": "akgp_extensions.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/akgp_extensions/css/akgp_extensions.css"
# app_include_js = "/assets/akgp_extensions/js/akgp_extensions.js"

# include js, css files in header of web template
# web_include_css = "/assets/akgp_extensions/css/akgp_extensions.css"
# web_include_js = "/assets/akgp_extensions/js/akgp_extensions.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "akgp_extensions/public/scss/website"

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
# app_include_icons = "akgp_extensions/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "akgp_extensions.utils.jinja_methods",
# 	"filters": "akgp_extensions.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "akgp_extensions.install.before_install"
# after_install = "akgp_extensions.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "akgp_extensions.uninstall.before_uninstall"
# after_uninstall = "akgp_extensions.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "akgp_extensions.utils.before_app_install"
# after_app_install = "akgp_extensions.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "akgp_extensions.utils.before_app_uninstall"
# after_app_uninstall = "akgp_extensions.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "akgp_extensions.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "akgp_extensions.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_invoice_update",
		"on_cancel": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_invoice_update",
		"on_update": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_invoice_update"
	},
	"Payment Entry": {
		"on_submit": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_payment_update",
		"on_cancel": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_payment_update"
	},
	"Delivery Note": {
		"on_submit": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_delivery_note_submit",
		"on_cancel": "akgp_extensions.akgp_extensions.doctype.catering_order.catering_order.on_delivery_note_cancel"
	}
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"akgp_extensions.tasks.all"
# 	],
# 	"daily": [
# 		"akgp_extensions.tasks.daily"
# 	],
# 	"hourly": [
# 		"akgp_extensions.tasks.hourly"
# 	],
# 	"weekly": [
# 		"akgp_extensions.tasks.weekly"
# 	],
# 	"monthly": [
# 		"akgp_extensions.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "akgp_extensions.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "akgp_extensions.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "akgp_extensions.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "akgp_extensions.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["akgp_extensions.utils.before_request"]
# after_request = ["akgp_extensions.utils.after_request"]

# Job Events
# ----------
# before_job = ["akgp_extensions.utils.before_job"]
# after_job = ["akgp_extensions.utils.after_job"]

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
# 	"akgp_extensions.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			["fieldname", "in", ["custom_catering_order_ref"]]
		]
	}
]


