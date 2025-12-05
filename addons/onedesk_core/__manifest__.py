{
    'name': 'OneDesk Core',
    'version': '1.0.0',
    'summary': 'Core of OneDesk (central hub for property management, tasks, documents, etc.)',
    'author': 'Merveilles',
    'license': 'LGPL-3',
    'category': 'Services',
    'depends': [
        'base', 'contacts', 'mail', 'account', 'calendar',
        'payment',              # NEW - Payment Engine
        'account_payment',      # NEW - Invoice Payment Integration
        'website',              # NEW - Website module for portal/frontend
    ],
    'data': [
    # Multi-tenant data FIRST - Groupes et séquences doivent exister AVANT ir.model.access.csv
    'data/onedesk_sequences.xml',
    'data/onedesk_groups.xml',

    'security/ir.model.access.csv',

    # Dashboards FIRST (car le menu y référence des actions)
    'views/onedesk_dashboard.xml',
    'views/onedesk_dashboard_sales_views.xml',
    'views/onedesk_dashboard_reservations_views.xml',
    'views/onedesk_dashboard_properties_views.xml',
    'views/onedesk_dashboard_users_views.xml',

    # Menu root and initial menus (must load BEFORE views that reference them)
    'views/onedesk_menu_views.xml',

    # Actions and wizards (must load BEFORE views that reference them)
    'views/onedesk_image_wizard_views.xml',
    'views/contact_importer_views.xml',

    # Autres vues
    # ⚠️ ORDRE IMPORTANT: seasonal_price AVANT unit car unit en dépend
    'views/onedesk_property_views.xml',
    'views/onedesk_seasonal_price_views.xml',
    'views/onedesk_unit_views.xml',
    'views/onedesk_image_views.xml',
    'views/onedesk_reservation_views.xml',
    'views/onedesk_task_views.xml',
    'views/onedesk_integration_provider_views.xml',
    'views/onedesk_integration_views.xml',
    'views/onedesk_integration_menu.xml',
    'views/oauth_templates.xml',
    'views/public_reservation_templates.xml',

    # Document & Signature views
    'views/onedesk_document_views.xml',
    'views/onedesk_document_signature_views.xml',
    'views/public_signature_templates.xml',  # NEW - Public signature pages
    'views/invitation_templates.xml',  # NEW - Invitation acceptance pages
    'views/onedesk_document_recipient_views.xml',
    'views/onedesk_signaturit_config.xml',

    # Payment Retry & Availability Cache views (Phase C1 + C2)
    'views/onedesk_payment_retry_views.xml',
    'views/onedesk_availability_cache_views.xml',

    # Contact Importer (Marketing)
    'views/contact_importer_views.xml',

    # Multi-tenant views (admin)
    'views/onedesk_plan_views.xml',
    'views/onedesk_client_views.xml',
    'views/onedesk_subscription_views.xml',
    'views/onedesk_audit_log_views.xml',

    # Données après (quand les models sont chargés)
    'data/integration_providers.xml',
    'data/integration_cron.xml',
    'data/onedesk_signaturit_config.xml',

    # Payment & Cache (Phase C1 + C2)
    'data/onedesk_payment_retry_cron.xml',

    # Menus APRÈS les vues qui créent les actions (CRITICAL: must be after all view files)
    'views/onedesk_menu_hierarchy.xml',
    'data/onedesk_menus.xml',

    # Multi-tenant data (plans, règles)
    'data/onedesk_plans.xml',
    'data/onedesk_security.xml',
    'data/onedesk_email_templates.xml',
    ],

    # Assets (CSS, JavaScript)
    'assets': {
        'web.assets_backend': [
            # ApexCharts for graphs (replacing Chart.js)
            'https://cdn.jsdelivr.net/npm/apexcharts@3.45.1/dist/apexcharts.min.js',

            # OneDesk Dashboard CSS & JS
            'onedesk_core/static/src/css/dashboard.css',
            'onedesk_core/static/src/css/document_form.css',
            'onedesk_core/static/src/xml/dashboard_templates.xml',  # NEW: OWL Templates
            'onedesk_core/static/src/js/dashboard_refresh.js',
            'onedesk_core/static/src/js/dashboard_apexcharts.js',  # NEW: ApexCharts dashboard
            'onedesk_core/static/src/js/dashboard_admin_master.js',  # NEW: Admin Master dashboard
            'onedesk_core/static/src/js/dashboard_customization.js',
            'onedesk_core/static/src/js/document_form_layout.js',
        ]
    },
    
    # ← NOUVEAU : Dépendances Python
    'external_dependencies': {
        'python': ['cryptography', 'requests', 'python-dateutil'],
    },
    
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}

