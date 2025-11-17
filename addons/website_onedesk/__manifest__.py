{
    'name': 'OneDesk Website',
    'version': '1.0.0',
    'summary': 'Public website for OneDesk property listings and booking requests',
    'author': 'Merveilles',
    'license': 'LGPL-3',
    'category': 'Website',
    'depends': [
        'website',
        'onedesk_core',
    ],
    'data': [
        'templates/pages.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_onedesk/static/css/website_onedesk.css',
        ],
    },
    'installable': True,
    'application': False,
}
