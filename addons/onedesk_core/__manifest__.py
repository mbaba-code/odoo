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
    'security/ir.model.access.csv',

    # Dashboards FIRST (car le menu y référence des actions)
    'views/onedesk_dashboard.xml',
    'views/onedesk_dashboard_sales_views.xml',
    'views/onedesk_dashboard_reservations_views.xml',
    'views/onedesk_dashboard_properties_views.xml',
    'views/onedesk_dashboard_users_views.xml',

    # Menus ensuite (qui référencent les actions)
    'views/onedesk_menu_hierarchy.xml',

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

    # Multi-tenant views (admin)
    'views/onedesk_plan_views.xml',
    'views/onedesk_client_views.xml',
    'views/onedesk_subscription_views.xml',
    'views/onedesk_audit_log_views.xml',

    # Données après (quand les models sont chargés)
    'data/integration_providers.xml',
    'data/integration_cron.xml',

    # Multi-tenant data (séquences, groupes, plans, règles)
    'data/onedesk_sequences.xml',
    'data/onedesk_groups.xml',
    'data/onedesk_plans.xml',
    'data/onedesk_security.xml',
    'data/onedesk_email_templates.xml',
    ],

    # Assets (CSS, JavaScript)
    'assets': {
        'web.assets_backend': [
            # Chart.js for graphs
            'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js',

            # OneDesk Dashboard CSS & JS
            'onedesk_core/static/src/css/dashboard.css',
            'onedesk_core/static/src/js/dashboard_refresh.js',
            'onedesk_core/static/src/js/dashboard_charts.js',
            'onedesk_core/static/src/js/dashboard_customization.js',
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

