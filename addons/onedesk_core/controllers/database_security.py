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
from odoo.http import request, Response
from odoo.addons.web.controllers.database import Database

_logger = logging.getLogger(__name__)


def _blocked_response(reason="Accès non autorisé", message="Vous n'avez pas les permissions nécessaires pour accéder à cette page."):
    """
    Retourne une réponse HTTP avec page de blocage HTML pure

    Ne nécessite pas de base de données ou de contexte
    """
    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8"/>
            <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
            <meta name="viewport" content="width=device-width, initial-scale=1"/>
            <title>Accès Refusé - Database Manager</title>
            <style>
                body {{
                    background-color: #f8f9fa;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    padding-top: 50px;
                    margin: 0;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 0 15px;
                }}
                .card {{
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .card-header {{
                    background-color: #dc3545;
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                }}
                .card-header h3 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .card-body {{
                    padding: 30px;
                }}
                .alert {{
                    padding: 20px;
                    border-radius: 5px;
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                }}
                .alert h4 {{
                    margin-top: 0;
                    font-size: 20px;
                }}
                .btn-primary {{
                    background-color: #007bff;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin-top: 10px;
                }}
                .btn-primary:hover {{
                    background-color: #0056b3;
                    text-decoration: none;
                }}
                .card-footer {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    text-align: center;
                    border-radius: 0 0 8px 8px;
                    color: #6c757d;
                    font-size: 14px;
                }}
                .text-muted {{
                    color: #6c757d;
                }}
                ul {{
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="card-header">
                        <h3>🚫 Accès Refusé</h3>
                    </div>
                    <div class="card-body">
                        <div class="alert">
                            <h4>⚠️ {reason}</h4>
                            <hr style="border-top: 1px solid #f5c6cb; margin: 15px 0;"/>
                            <p style="margin: 0;">{message}</p>
                        </div>

                        <div style="margin-top: 30px;">
                            <h5>🔒 Sécurité SaaS</h5>
                            <p class="text-muted">
                                Pour des raisons de sécurité, le gestionnaire de bases de données
                                est réservé aux super administrateurs.
                            </p>
                            <ul class="text-muted">
                                <li>Les bases de données sont provisionnées automatiquement</li>
                                <li>Chaque client dispose d'une base isolée et sécurisée</li>
                                <li>Les opérations sensibles sont auditées</li>
                            </ul>
                        </div>

                        <div style="margin-top: 30px; text-align: center;">
                            <a href="/web" class="btn-primary">
                                🏠 Retour à l'accueil
                            </a>
                        </div>
                    </div>
                    <div class="card-footer">
                        <small>
                            🛡️ Cet accès a été enregistré dans les logs de sécurité
                        </small>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    return Response(html, status=403, content_type='text/html; charset=utf-8')


class DatabaseSecurity(Database):
    """
    Hérite du contrôleur Database pour bloquer les accès non autorisés
    """

    @http.route('/web/database/manager', type='http', auth="none")
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
            return _blocked_response(
                reason='Authentification requise',
                message='Vous devez être connecté en tant que super administrateur pour accéder à cette page.'
            )

        # Vérifier si l'utilisateur est super admin
        user = request.env['res.users'].browse(request.env.uid)

        # Seuls les utilisateurs avec group_system peuvent accéder
        if not user.has_group('base.group_system'):
            _logger.warning(
                f"[SECURITY] Tentative d'accès non autorisé à /web/database/manager "
                f"par {user.name} (ID: {user.id})"
            )
            return _blocked_response(
                reason='Accès refusé',
                message='Seuls les super administrateurs peuvent accéder au gestionnaire de bases de données.'
            )

        # Super admin autorisé - appeler la méthode parent
        _logger.info(f"[SECURITY] Accès autorisé à /web/database/manager pour {user.name} (Super Admin)")
        return super().manager(**kw)

    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        """
        Bloque l'accès au sélecteur de bases de données

        En mode SaaS, les utilisateurs ne doivent PAS voir la liste des bases
        """
        # Si pas d'utilisateur connecté, bloquer
        if not request.env.uid:
            _logger.warning("[SECURITY] Tentative d'accès non authentifié à /web/database/selector")
            return _blocked_response(
                reason='Authentification requise',
                message='Le sélecteur de bases de données n\'est pas accessible.'
            )

        user = request.env['res.users'].browse(request.env.uid)

        # Seuls les super admins peuvent voir le sélecteur
        if not user.has_group('base.group_system'):
            _logger.warning(
                f"[SECURITY] Tentative d'accès non autorisé à /web/database/selector "
                f"par {user.name} (ID: {user.id})"
            )
            return _blocked_response(
                reason='Accès refusé',
                message='Vous n\'avez pas les droits nécessaires pour accéder au sélecteur de bases de données.'
            )

        # Super admin autorisé
        _logger.info(f"[SECURITY] Accès autorisé à /web/database/selector pour {user.name} (Super Admin)")
        return super().selector(**kw)

    @http.route('/web/database/create', type='http', auth="none", methods=['POST'], csrf=False)
    def create(self, *args, **kw):
        """
        Bloque complètement la création de bases via HTTP

        SÉCURITÉ CRITIQUE:
        - En mode SaaS, les bases sont créées via saas_client.action_provision_database()
        - La création directe via /web/database/create doit être TOTALEMENT bloquée
        """
        _logger.error("[SECURITY] Tentative de création de base via /web/database/create - BLOQUÉ")
        return _blocked_response(
            reason='Opération non autorisée',
            message='La création de bases de données via cette interface est désactivée. Utilisez le système de provisioning SaaS.'
        )

    @http.route('/web/database/duplicate', type='http', auth="none", methods=['POST'], csrf=False)
    def duplicate(self, *args, **kw):
        """
        Bloque la duplication de bases via HTTP
        """
        _logger.error("[SECURITY] Tentative de duplication de base via /web/database/duplicate - BLOQUÉ")
        return _blocked_response(
            reason='Opération non autorisée',
            message='La duplication de bases de données via cette interface est désactivée.'
        )

    @http.route('/web/database/drop', type='http', auth="none", methods=['POST'], csrf=False)
    def drop(self, *args, **kw):
        """
        Bloque la suppression de bases via HTTP

        SÉCURITÉ CRITIQUE:
        - La suppression doit UNIQUEMENT passer par saas_client.action_terminate()
        - Logging et audit trail requis
        """
        _logger.error("[SECURITY] Tentative de suppression de base via /web/database/drop - BLOQUÉ")
        return _blocked_response(
            reason='Opération non autorisée',
            message='La suppression de bases de données via cette interface est désactivée. Utilisez le système de gestion SaaS.'
        )

    @http.route('/web/database/backup', type='http', auth="none", methods=['POST'], csrf=False)
    def backup(self, *args, **kw):
        """
        Limite le backup aux super admins uniquement
        """
        if not request.env.uid:
            _logger.warning("[SECURITY] Tentative de backup non authentifié")
            return _blocked_response(
                reason='Accès refusé',
                message='Seuls les super administrateurs peuvent effectuer des backups.'
            )

        user = request.env['res.users'].browse(request.env.uid)
        if not user.has_group('base.group_system'):
            _logger.warning("[SECURITY] Tentative de backup non autorisé")
            return _blocked_response(
                reason='Accès refusé',
                message='Seuls les super administrateurs peuvent effectuer des backups.'
            )

        _logger.info(f"[SECURITY] Backup autorisé pour {user.name}")
        return super().backup(*args, **kw)

    @http.route('/web/database/restore', type='http', auth="none", methods=['POST'], csrf=False)
    def restore(self, *args, **kw):
        """
        Bloque complètement la restauration via HTTP
        """
        _logger.error("[SECURITY] Tentative de restauration de base via /web/database/restore - BLOQUÉ")
        return _blocked_response(
            reason='Opération non autorisée',
            message='La restauration de bases de données via cette interface est désactivée.'
        )

    @http.route('/web/database/change_password', type='http', auth="none", methods=['POST'], csrf=False)
    def change_password(self, *args, **kw):
        """
        Bloque le changement de master password via HTTP

        SÉCURITÉ CRITIQUE:
        - Le master password est configuré via odoo.conf
        - Ne doit JAMAIS être changeable via l'interface web
        """
        _logger.error("[SECURITY] Tentative de changement master password via HTTP - BLOQUÉ")
        return _blocked_response(
            reason='Opération non autorisée',
            message='Le changement du mot de passe master via l\'interface web est désactivé pour des raisons de sécurité.'
        )
