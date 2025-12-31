# -*- coding: utf-8 -*-
"""
Contrôleur de sécurité pour bloquer l'accès au gestionnaire de bases de données

SÉCURITÉ CRITIQUE:
- Bloque /web/database/manager et autres routes sensibles
- Seuls les super admins peuvent y accéder
- Protection contre l'exposition publique en production
"""
import logging
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.database import Database

_logger = logging.getLogger(__name__)


class DatabaseSecurity(Database):
    """
    Hérite du contrôleur Database pour bloquer les accès non autorisés
    """

    @http.route('/web/database/manager', type='http', auth="none", website=True)
    def manager(self, **kw):
        """
        Bloque l'accès au gestionnaire de bases de données pour tous sauf super admin

        SÉCURITÉ CRITIQUE:
        - En production SaaS, le database manager NE DOIT JAMAIS être accessible
        - Seuls les super admins de la base principale peuvent y accéder
        - Les clients et utilisateurs normaux sont bloqués
        """
        # Si pas d'utilisateur connecté, bloquer
        if not request.env.uid:
            _logger.warning("[SECURITY] Tentative d'accès non authentifié à /web/database/manager")
            return request.render('onedesk_core.database_manager_blocked', {
                'reason': 'Authentification requise',
                'message': 'Vous devez être connecté en tant que super administrateur pour accéder à cette page.'
            })

        # Vérifier si l'utilisateur est super admin
        user = request.env.user

        # Seuls les utilisateurs avec group_system peuvent accéder
        if not user.has_group('base.group_system'):
            _logger.warning(
                f"[SECURITY] Tentative d'accès non autorisé à /web/database/manager "
                f"par {user.name} (ID: {user.id})"
            )
            return request.render('onedesk_core.database_manager_blocked', {
                'reason': 'Accès refusé',
                'message': 'Seuls les super administrateurs peuvent accéder au gestionnaire de bases de données.'
            })

        # Super admin autorisé - appeler la méthode parent
        _logger.info(f"[SECURITY] Accès autorisé à /web/database/manager pour {user.name} (Super Admin)")
        return super().manager(**kw)

    @http.route('/web/database/selector', type='http', auth="none", website=True)
    def selector(self, **kw):
        """
        Bloque l'accès au sélecteur de bases de données

        En mode SaaS, les utilisateurs ne doivent PAS voir la liste des bases
        """
        # Si pas d'utilisateur connecté, bloquer
        if not request.env.uid:
            _logger.warning("[SECURITY] Tentative d'accès non authentifié à /web/database/selector")
            return request.render('onedesk_core.database_manager_blocked', {
                'reason': 'Authentification requise',
                'message': 'Le sélecteur de bases de données n\'est pas accessible.'
            })

        user = request.env.user

        # Seuls les super admins peuvent voir le sélecteur
        if not user.has_group('base.group_system'):
            _logger.warning(
                f"[SECURITY] Tentative d'accès non autorisé à /web/database/selector "
                f"par {user.name} (ID: {user.id})"
            )
            return request.render('onedesk_core.database_manager_blocked', {
                'reason': 'Accès refusé',
                'message': 'Vous n\'avez pas les droits nécessaires pour accéder au sélecteur de bases de données.'
            })

        # Super admin autorisé
        _logger.info(f"[SECURITY] Accès autorisé à /web/database/selector pour {user.name} (Super Admin)")
        return super().selector(**kw)

    @http.route('/web/database/create', type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def create(self, *args, **kw):
        """
        Bloque complètement la création de bases via HTTP

        SÉCURITÉ CRITIQUE:
        - En mode SaaS, les bases sont créées via saas_client.action_provision_database()
        - La création directe via /web/database/create doit être TOTALEMENT bloquée
        """
        _logger.error("[SECURITY] Tentative de création de base via /web/database/create - BLOQUÉ")
        return request.render('onedesk_core.database_manager_blocked', {
            'reason': 'Opération non autorisée',
            'message': 'La création de bases de données via cette interface est désactivée. '
                      'Utilisez le système de provisioning SaaS.'
        })

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def duplicate(self, *args, **kw):
        """
        Bloque la duplication de bases via HTTP
        """
        _logger.error("[SECURITY] Tentative de duplication de base via /web/database/duplicate - BLOQUÉ")
        return request.render('onedesk_core.database_manager_blocked', {
            'reason': 'Opération non autorisée',
            'message': 'La duplication de bases de données via cette interface est désactivée.'
        })

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def drop(self, *args, **kw):
        """
        Bloque la suppression de bases via HTTP

        SÉCURITÉ CRITIQUE:
        - La suppression doit UNIQUEMENT passer par saas_client.action_terminate()
        - Logging et audit trail requis
        """
        _logger.error("[SECURITY] Tentative de suppression de base via /web/database/drop - BLOQUÉ")
        return request.render('onedesk_core.database_manager_blocked', {
            'reason': 'Opération non autorisée',
            'message': 'La suppression de bases de données via cette interface est désactivée. '
                      'Utilisez le système de gestion SaaS.'
        })

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def backup(self, *args, **kw):
        """
        Limite le backup aux super admins uniquement
        """
        if not request.env.uid or not request.env.user.has_group('base.group_system'):
            _logger.warning("[SECURITY] Tentative de backup non autorisé")
            return request.render('onedesk_core.database_manager_blocked', {
                'reason': 'Accès refusé',
                'message': 'Seuls les super administrateurs peuvent effectuer des backups.'
            })

        _logger.info(f"[SECURITY] Backup autorisé pour {request.env.user.name}")
        return super().backup(*args, **kw)

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def restore(self, *args, **kw):
        """
        Bloque complètement la restauration via HTTP
        """
        _logger.error("[SECURITY] Tentative de restauration de base via /web/database/restore - BLOQUÉ")
        return request.render('onedesk_core.database_manager_blocked', {
            'reason': 'Opération non autorisée',
            'message': 'La restauration de bases de données via cette interface est désactivée.'
        })

    @http.route('/web/database/change_password', type='http', auth="none", methods=['POST'], csrf=False, website=True)
    def change_password(self, *args, **kw):
        """
        Bloque le changement de master password via HTTP

        SÉCURITÉ CRITIQUE:
        - Le master password est configuré via odoo.conf
        - Ne doit JAMAIS être changeable via l'interface web
        """
        _logger.error("[SECURITY] Tentative de changement master password via HTTP - BLOQUÉ")
        return request.render('onedesk_core.database_manager_blocked', {
            'reason': 'Opération non autorisée',
            'message': 'Le changement du mot de passe master via l\'interface web est désactivé pour des raisons de sécurité.'
        })
