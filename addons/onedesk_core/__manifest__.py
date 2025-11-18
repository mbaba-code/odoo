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

    # Menus FIRST (avant toutes les autres vues qui les référencent)
    'views/onedesk_menu_hierarchy.xml',

    # Vues ensuite (ça charge les models)
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
    
    # ← NOUVEAU : Dépendances Python
    'external_dependencies': {
        'python': ['cryptography', 'requests', 'python-dateutil'],
    },
    
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}

