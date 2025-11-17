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
    ],
    'data': [
    'security/ir.model.access.csv',

    # Menus FIRST (avant toutes les autres vues qui les référencent)
    'views/onedesk_menu_views.xml',

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

    # Données après (quand les models sont chargés)
    'data/integration_providers.xml',
    'data/integration_cron.xml',
    ],
    
    # ← NOUVEAU : Dépendances Python
    'external_dependencies': {
        'python': ['cryptography', 'requests', 'python-dateutil'],
    },
    
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}

