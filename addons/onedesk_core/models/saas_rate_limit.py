# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging


_logger = logging.getLogger(__name__)

class SaasRateLimit(models.Model):
    """
    Suivi des requêtes de provisioning pour protection DoS

    SÉCURITÉ: Ce modèle empêche les attaques par création massive de clients
    en limitant le nombre de tentatives de provisioning par IP/heure
    """
    _name = 'saas.rate_limit'
    _description = 'Rate Limiting pour Provisioning SaaS'
    _order = 'window_start desc'
    _rec_name = 'ip_address'

    # Identification
    ip_address = fields.Char('Adresse IP', required=True, index=True,
                              help="IP source de la requête de provisioning")
    user_id = fields.Many2one('res.users', 'Utilisateur', index=True,
                               help="Utilisateur ayant effectué la requête (si authentifié)")

    # Compteurs
    request_count = fields.Integer('Nombre de Requêtes', default=1, required=True,
                                     help="Nombre de tentatives dans la fenêtre actuelle")
    window_start = fields.Datetime('Début Fenêtre', default=fields.Datetime.now, required=True, index=True,
                                     help="Début de la fenêtre de temps (1 heure)")

    # Blocage
    is_blocked = fields.Boolean('Bloqué', default=False, index=True,
                                  help="Indique si l'IP est temporairement bloquée")
    blocked_until = fields.Datetime('Bloqué Jusqu\'à', index=True,
                                      help="Date de fin du blocage (si applicable)")
    blocked_reason = fields.Text('Raison du Blocage',
                                   help="Détails sur la raison du blocage")
    
    


    # Audit
    last_attempt = fields.Datetime('Dernière Tentative', default=fields.Datetime.now,
                                     help="Timestamp de la dernière tentative")
    attempts_blocked = fields.Integer('Tentatives Bloquées', default=0,
                                        help="Nombre de tentatives bloquées après limite atteinte")

    _sql_constraints = [
        ('ip_window_unique', 'unique(ip_address, window_start)',
         'Un seul enregistrement par IP et fenêtre de temps autorisé'),
    ]
    
    
    
    
    # 1. On définit les champs comme non-stockés (store=False)
    # 2. On ajoute l'attribut 'search' pour dire à Odoo comment filtrer
    is_last_hour = fields.Boolean(
        string="Dernière heure", 
        compute='_compute_dummy', 
        search='_search_last_hour',
        store=False
    )
    
    is_last_24h = fields.Boolean(
        string="Dernières 24h", 
        compute='_compute_dummy', 
        search='_search_last_24h',
        store=False
    )
    
    is_last_7d = fields.Boolean(
        string="Derniers 7 jours", 
        compute='_compute_dummy', 
        search='_search_last_7d',
        store=False
    )

    # Fonction compute "bidon" obligatoire pour les champs non stockés
    # Elle sert juste à éviter une erreur si on essaie de LIRE ces champs
    def _compute_dummy(self):
        for rec in self:
            rec.is_last_hour = False
            rec.is_last_24h = False
            rec.is_last_7d = False

    # --- FONCTIONS DE RECHERCHE (C'est ici que la magie opère) ---
    
    def _search_last_hour(self, operator, value):
        # Si on cherche "est vrai" (True)
        if operator == '=' and value:
            limit = fields.Datetime.now() - timedelta(hours=1)
            return [('window_start', '>=', limit)]
        return []

    def _search_last_24h(self, operator, value):
        if operator == '=' and value:
            limit = fields.Datetime.now() - timedelta(hours=24)
            return [('window_start', '>=', limit)]
        return []

    def _search_last_7d(self, operator, value):
        if operator == '=' and value:
            limit = fields.Datetime.now() - timedelta(days=7)
            return [('window_start', '>=', limit)]
        return []
    
    
    

    @api.model
    def check_rate_limit(self, ip_address, user_id=None):
        """
        Vérifie et enregistre une tentative de provisioning

        Limites:
        - 5 provisionings par heure par IP
        - Blocage de 1 heure après dépassement
        - Blocage de 24h après 3 dépassements dans la journée

        EXCEPTION: Les administrateurs système (group_system) sont exemptés

        Args:
            ip_address: IP source de la requête
            user_id: ID de l'utilisateur (optionnel)

        Returns:
            dict: {'allowed': bool, 'message': str, 'remaining': int}

        Raises:
            UserError: Si la limite est dépassée
        """
        if not ip_address:
            # Si pas d'IP (requête locale?), autoriser
            return {'allowed': True, 'message': 'OK', 'remaining': 999}

        # EXCEPTION: Les administrateurs système sont exemptés du rate limiting
        # Cela permet aux admins de créer plusieurs clients pour tests/démos
        if user_id:
            user = self.env['res.users'].browse(user_id)
            if user.has_group('base.group_system'):
                _logger.info(f"[SAAS SECURITY] Rate limit bypassed - System Admin: {user.name}")
                return {'allowed': True, 'message': 'Admin exempted', 'remaining': 999}

        # Configuration des limites
        MAX_REQUESTS_PER_HOUR = 5
        BLOCK_DURATION_HOURS = 1
        MAX_BLOCKS_PER_DAY = 3
        PERMANENT_BLOCK_HOURS = 24

        now = fields.Datetime.now()
        window_start = now.replace(minute=0, second=0, microsecond=0)

        # 1. Vérifier si IP actuellement bloquée
        blocked_record = self.search([
            ('ip_address', '=', ip_address),
            ('is_blocked', '=', True),
            ('blocked_until', '>', now),
        ], limit=1)

        if blocked_record:
            time_remaining = blocked_record.blocked_until - now
            minutes_remaining = int(time_remaining.total_seconds() / 60)

            # Incrémenter le compteur de tentatives bloquées
            blocked_record.write({
                'attempts_blocked': blocked_record.attempts_blocked + 1,
                'last_attempt': now,
            })

            _logger.warning(f"[SAAS SECURITY] Rate limit - IP bloquée: {ip_address} "
                          f"(encore {minutes_remaining} minutes)")

            raise UserError(
                f"Trop de tentatives de création de clients. "
                f"Votre adresse IP est temporairement bloquée.\n\n"
                f"Temps restant: {minutes_remaining} minutes\n\n"
                f"Si vous pensez qu'il s'agit d'une erreur, contactez le support."
            )

        # 2. Trouver ou créer l'enregistrement pour cette fenêtre
        rate_record = self.search([
            ('ip_address', '=', ip_address),
            ('window_start', '=', window_start),
        ], limit=1)

        if not rate_record:
            # Nouvelle fenêtre - créer un enregistrement
            rate_record = self.create({
                'ip_address': ip_address,
                'user_id': user_id,
                'request_count': 1,
                'window_start': window_start,
                'last_attempt': now,
            })

            remaining = MAX_REQUESTS_PER_HOUR - 1
            _logger.info(f"[SAAS SECURITY] Rate limit - Nouvelle fenêtre pour {ip_address}: "
                        f"1/{MAX_REQUESTS_PER_HOUR}")

            return {
                'allowed': True,
                'message': 'OK',
                'remaining': remaining,
            }

        # 3. Vérifier si limite atteinte
        if rate_record.request_count >= MAX_REQUESTS_PER_HOUR:
            # Limite dépassée - bloquer l'IP

            # Vérifier combien de fois bloqué dans les dernières 24h
            day_ago = now - timedelta(hours=24)
            blocks_today = self.search_count([
                ('ip_address', '=', ip_address),
                ('is_blocked', '=', True),
                ('window_start', '>=', day_ago),
            ])

            # Si déjà bloqué plusieurs fois aujourd'hui, bloquer plus longtemps
            if blocks_today >= MAX_BLOCKS_PER_DAY:
                block_duration = timedelta(hours=PERMANENT_BLOCK_HOURS)
                reason = f"Blocage de 24h: {blocks_today} dépassements de limite détectés dans les dernières 24h"
                _logger.error(f"[SAAS SECURITY] Rate limit - Blocage 24h pour {ip_address} "
                            f"({blocks_today} violations)")
            else:
                block_duration = timedelta(hours=BLOCK_DURATION_HOURS)
                reason = f"Limite de {MAX_REQUESTS_PER_HOUR} requêtes/heure dépassée"
                _logger.warning(f"[SAAS SECURITY] Rate limit - Blocage 1h pour {ip_address}")

            blocked_until = now + block_duration

            rate_record.write({
                'is_blocked': True,
                'blocked_until': blocked_until,
                'blocked_reason': reason,
                'attempts_blocked': 1,
                'last_attempt': now,
            })

            minutes_blocked = int(block_duration.total_seconds() / 60)

            raise UserError(
                f"Limite de création de clients dépassée.\n\n"
                f"Vous avez effectué {rate_record.request_count} tentatives dans la dernière heure.\n"
                f"Limite autorisée: {MAX_REQUESTS_PER_HOUR} tentatives/heure\n\n"
                f"Votre IP est bloquée pour {minutes_blocked} minutes.\n\n"
                f"Si vous avez besoin d'assistance, contactez le support."
            )

        # 4. Limite non atteinte - incrémenter le compteur
        new_count = rate_record.request_count + 1
        rate_record.write({
            'request_count': new_count,
            'last_attempt': now,
        })

        remaining = MAX_REQUESTS_PER_HOUR - new_count

        _logger.info(f"[SAAS SECURITY] Rate limit - IP {ip_address}: "
                    f"{new_count}/{MAX_REQUESTS_PER_HOUR} requêtes")

        # Avertir si proche de la limite
        if remaining <= 1:
            _logger.warning(f"[SAAS SECURITY] Rate limit - IP {ip_address} proche de la limite: "
                          f"{new_count}/{MAX_REQUESTS_PER_HOUR}")

        return {
            'allowed': True,
            'message': f'{remaining} tentative(s) restante(s) cette heure',
            'remaining': remaining,
        }

    @api.model
    def cleanup_old_records(self):
        """
        Nettoie les anciens enregistrements de rate limiting
        Appelé par un cron job quotidien

        Conservation:
        - Records non bloqués: 7 jours
        - Records bloqués: 30 jours (audit/sécurité)
        """
        now = fields.Datetime.now()

        # Supprimer les enregistrements non bloqués de plus de 7 jours
        seven_days_ago = now - timedelta(days=7)
        old_records = self.search([
            ('is_blocked', '=', False),
            ('window_start', '<', seven_days_ago),
        ])

        count_normal = len(old_records)
        if count_normal > 0:
            old_records.unlink()
            _logger.info(f"[SAAS SECURITY] Rate limit cleanup: {count_normal} anciens records supprimés")

        # Supprimer les enregistrements bloqués de plus de 30 jours
        thirty_days_ago = now - timedelta(days=30)
        old_blocked = self.search([
            ('is_blocked', '=', True),
            ('window_start', '<', thirty_days_ago),
        ])

        count_blocked = len(old_blocked)
        if count_blocked > 0:
            old_blocked.unlink()
            _logger.info(f"[SAAS SECURITY] Rate limit cleanup: {count_blocked} records bloqués expirés supprimés")

        # Débloquer les IPs dont le blocage est expiré
        expired_blocks = self.search([
            ('is_blocked', '=', True),
            ('blocked_until', '<', now),
        ])

        count_unblocked = len(expired_blocks)
        if count_unblocked > 0:
            expired_blocks.write({'is_blocked': False})
            _logger.info(f"[SAAS SECURITY] Rate limit cleanup: {count_unblocked} IPs débloquées")

        return {
            'deleted_normal': count_normal,
            'deleted_blocked': count_blocked,
            'unblocked': count_unblocked,
        }

    @api.model
    def get_statistics(self):
        """
        Retourne des statistiques sur le rate limiting
        Utile pour monitoring et dashboard admin
        """
        now = fields.Datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        return {
            'currently_blocked': self.search_count([('is_blocked', '=', True), ('blocked_until', '>', now)]),
            'requests_last_hour': self.search_count([('window_start', '>=', hour_ago)]),
            'blocks_last_24h': self.search_count([('is_blocked', '=', True), ('window_start', '>=', day_ago)]),
            'total_records': self.search_count([]),
        }
        
    
    
