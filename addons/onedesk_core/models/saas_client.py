# -*- coding: utf-8 -*-
import secrets
import string
import re
import psycopg2
from odoo import models, fields, api, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class SaasClient(models.Model):
    _name = 'saas.client'
    _description = 'Client SaaS Premium'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    # Informations client
    active = fields.Boolean('Actif', default=True, tracking=True,
                           help="Désarchiver pour réactiver le client")
    name = fields.Char('Nom du Contact', required=True, tracking=True)
    email = fields.Char('Email Admin', required=True, tracking=True)
    company_name = fields.Char('Nom de la Société', required=True, tracking=True)
    phone = fields.Char('Téléphone')

    # Plan et abonnement
    plan_id = fields.Many2one('saas.plan', 'Plan Souscrit', required=True, tracking=True)
    subscription_state = fields.Selection([
        ('trial', 'Essai Gratuit'),
        ('active', 'Actif'),
        ('past_due', 'Impayé'),
        ('suspended', 'Suspendu'),
        ('cancelled', 'Résilié'),
    ], string='État Abonnement', default='trial', required=True, tracking=True)

    subscription_billing = fields.Selection([
        ('monthly', 'Mensuel'),
        ('yearly', 'Annuel'),
    ], string='Facturation', default='monthly', required=True)

    # Base de données
    database_name = fields.Char('Nom de la Base', readonly=True, copy=False, tracking=True)
    database_state = fields.Selection([
        ('draft', 'Brouillon'),
        ('provisioning', 'En cours de création'),
        ('active', 'Active'),
        ('suspended', 'Suspendue'),
        ('terminated', 'Terminée'),
        ('error', 'Erreur'),
    ], string='État Base de Données', default='draft', required=True, tracking=True)

    database_error = fields.Text('Erreur Provisioning', readonly=True)

    # Accès
    subdomain = fields.Char('Sous-domaine', required=True, tracking=True)
    custom_domain = fields.Char('Domaine Personnalisé', tracking=True,
                                 help="Ex: app.monclient.com (nécessite plan Pro ou Enterprise)")
    url = fields.Char('URL d\'Accès', compute='_compute_url', store=True)
    domain_ssl_active = fields.Boolean('SSL Actif', default=False, readonly=True,
                                      help="Indique si le certificat SSL est actif pour le domaine personnalisé")

    # Credentials admin client (temporaire)
    admin_login = fields.Char('Login Admin', readonly=True, copy=False)
    admin_password_temp = fields.Char('Mot de passe temporaire', readonly=True, copy=False,
                                       help="Visible uniquement après création, envoyé par email")

    # Dates
    created_date = fields.Datetime('Date de Création', default=fields.Datetime.now, readonly=True)
    trial_start_date = fields.Date('Début Essai', default=fields.Date.today)
    trial_end_date = fields.Date('Fin Essai', compute='_compute_trial_end_date', store=True)
    subscription_start_date = fields.Date('Début Abonnement')
    next_billing_date = fields.Date('Prochaine Facturation')
    cancelled_date = fields.Date('Date Résiliation')

    # Métriques d'utilisation
    nb_users = fields.Integer('Nombre d\'Utilisateurs', default=0, readonly=True)
    nb_active_users = fields.Integer('Utilisateurs Actifs (30j)', default=0, readonly=True)
    storage_used_gb = fields.Float('Stockage Utilisé (GB)', default=0.0, readonly=True, digits=(10, 2))
    api_calls_today = fields.Integer('API Calls Aujourd\'hui', default=0, readonly=True)
    last_login = fields.Datetime('Dernière Connexion', readonly=True)

    # Quotas et limites
    quota_users_exceeded = fields.Boolean('Quota Utilisateurs Dépassé', compute='_compute_quota_exceeded', store=True)
    quota_storage_exceeded = fields.Boolean('Quota Stockage Dépassé', compute='_compute_quota_exceeded', store=True)
    quota_api_exceeded = fields.Boolean('Quota API Dépassé', compute='_compute_quota_exceeded', store=True)

    # Relations
    database_id = fields.Many2one('saas.database', 'Instance Base', readonly=True, ondelete='restrict')
    metric_ids = fields.One2many('saas.metric', 'client_id', 'Métriques')
    alert_ids = fields.One2many('saas.alert', 'client_id', 'Alertes')

    # Facturation
    total_revenue = fields.Float('Revenu Total (€)', compute='_compute_total_revenue', store=True, digits=(10, 2))

    # Computed fields
    is_trial = fields.Boolean('En Période d\'Essai', compute='_compute_is_trial', store=True)
    days_until_trial_end = fields.Integer('Jours Restants Essai', compute='_compute_days_until_trial_end')

    _sql_constraints = [
        ('subdomain_unique', 'UNIQUE(subdomain)', 'Ce sous-domaine est déjà utilisé'),
        ('email_unique', 'UNIQUE(email)', 'Cet email est déjà utilisé'),
        ('database_name_unique', 'UNIQUE(database_name)', 'Ce nom de base de données est déjà utilisé'),
    ]

    @api.depends('database_name', 'admin_login', 'custom_domain')
    def _compute_url(self):
        """Génère l'URL d'accès DIRECT à la base de données client (force la base unique)"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        for client in self:
            # Priorité: domaine personnalisé > URL avec paramètre DB
            if client.custom_domain:
                # URL simple avec domaine personnalisé (Nginx gère le routing)
                client.url = f'https://{client.custom_domain}/web/login'
            elif client.database_name:
                # URL DIRECTE vers la base - Force la sélection de la base unique
                # Utilise le hash redirect pour forcer la base sans permettre le choix
                client.url = f'{base_url}/web?db={client.database_name}#action=&db={client.database_name}'
            else:
                client.url = False

    @api.depends('trial_start_date', 'plan_id.trial_days')
    def _compute_trial_end_date(self):
        for client in self:
            if client.trial_start_date and client.plan_id:
                client.trial_end_date = client.trial_start_date + timedelta(days=client.plan_id.trial_days)
            else:
                client.trial_end_date = False

    @api.depends('subscription_state', 'trial_end_date')
    def _compute_is_trial(self):
        today = fields.Date.today()
        for client in self:
            client.is_trial = (
                client.subscription_state == 'trial' and
                client.trial_end_date and
                client.trial_end_date >= today
            )

    @api.depends('trial_end_date')
    def _compute_days_until_trial_end(self):
        today = fields.Date.today()
        for client in self:
            if client.trial_end_date:
                delta = client.trial_end_date - today
                client.days_until_trial_end = delta.days if delta.days > 0 else 0
            else:
                client.days_until_trial_end = 0

    @api.depends('nb_users', 'storage_used_gb', 'api_calls_today', 'plan_id')
    def _compute_quota_exceeded(self):
        for client in self:
            plan = client.plan_id
            if plan:
                client.quota_users_exceeded = client.nb_users > plan.max_users
                client.quota_storage_exceeded = client.storage_used_gb > plan.max_storage_gb
                client.quota_api_exceeded = client.api_calls_today > plan.max_api_calls_per_day
            else:
                client.quota_users_exceeded = False
                client.quota_storage_exceeded = False
                client.quota_api_exceeded = False

    @api.depends('subscription_start_date', 'next_billing_date', 'plan_id', 'subscription_billing')
    def _compute_total_revenue(self):
        for client in self:
            # Calculer le revenu total basé sur l'historique de facturation
            # Pour l'instant, estimation simple
            if client.subscription_state == 'active' and client.subscription_start_date:
                if client.subscription_billing == 'monthly':
                    months = (fields.Date.today() - client.subscription_start_date).days // 30
                    client.total_revenue = months * client.plan_id.price_monthly
                else:
                    years = (fields.Date.today() - client.subscription_start_date).days // 365
                    client.total_revenue = years * client.plan_id.price_yearly
            else:
                client.total_revenue = 0.0

    @api.constrains('subdomain')
    def _check_subdomain(self):
        for client in self:
            if client.subdomain:
                if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', client.subdomain):
                    raise ValidationError(
                        "Le sous-domaine doit contenir uniquement des lettres minuscules, "
                        "chiffres et tirets, et ne peut pas commencer ou finir par un tiret"
                    )

    @api.model_create_multi
    def create(self, vals_list):
        # Traiter chaque dictionnaire de valeurs
        for vals in vals_list:
            # Générer database_name si manquant
            if not vals.get('database_name'):
                vals['database_name'] = self._generate_database_name(vals.get('company_name', 'client'))

            # Générer subdomain si manquant
            if not vals.get('subdomain'):
                vals['subdomain'] = self._slugify(vals.get('company_name', 'client'))

        # Créer les clients
        clients = super().create(vals_list)

        # Message de bienvenue dans le chatter pour chaque client
        for client in clients:
            client.message_post(
                body=f"Client créé - Plan: {client.plan_id.name} - État: {dict(client._fields['subscription_state'].selection).get(client.subscription_state)}"
            )

        return clients

    def action_provision_database(self):
        """Provisionner la base de données client (appelé manuellement ou automatiquement)"""
        self.ensure_one()

        if self.database_state != 'draft':
            raise UserError("La base de données a déjà été provisionnée")

        try:
            # Changer l'état
            self.write({
                'database_state': 'provisioning',
                'database_error': False,
            })
            self.env.cr.commit()  # Commit pour que l'état soit visible immédiatement

            _logger.info(f"[SAAS] Début provisioning client {self.name} (DB: {self.database_name})")

            # 1. Initialiser Odoo (crée la base PostgreSQL + initialise Odoo)
            #    exp_create_database() gère les deux en une seule étape
            self._initialize_odoo_database()

            # 2. Créer l'admin client
            admin_password = self._create_client_admin()

            # 3. Configurer la company
            self._configure_client_company()

            # 4. Enregistrer l'instance de base
            self._register_database()

            # 5. Envoyer email de bienvenue
            self._send_welcome_email(admin_password)

            # État: active
            self.write({
                'database_state': 'active',
                'subscription_state': 'trial',
            })

            _logger.info(f"[SAAS] Provisioning terminé avec succès pour {self.name}")

            self.message_post(
                body=f"✅ Base de données provisionnée avec succès<br/>"
                     f"URL: <a href='{self.url}'>{self.url}</a><br/>"
                     f"Admin: {self.admin_login}"
            )

        except Exception as e:
            _logger.error(f"[SAAS] Erreur provisioning client {self.name}: {str(e)}", exc_info=True)
            self.write({
                'database_state': 'error',
                'database_error': str(e),
            })
            self.message_post(
                body=f"❌ Erreur lors du provisioning:<br/><code>{str(e)}</code>",
                message_type='comment'
            )
            raise UserError(f"Erreur lors du provisioning: {str(e)}")

    def _generate_database_name(self, client_name):
        """Génère un nom de base unique: onedesk_client_XXX_slug"""
        slug = self._slugify(client_name)
        # Trouver un ID unique
        existing_count = self.search_count([])
        db_name = f'onedesk_client_{existing_count + 1}_{slug}'
        return db_name[:63]  # Limite PostgreSQL

    def _slugify(self, text):
        """Convertit texte en slug (URL-safe)"""
        text = text.lower()
        text = re.sub(r'[àáâãäå]', 'a', text)
        text = re.sub(r'[èéêë]', 'e', text)
        text = re.sub(r'[ìíîï]', 'i', text)
        text = re.sub(r'[òóôõö]', 'o', text)
        text = re.sub(r'[ùúûü]', 'u', text)
        text = re.sub(r'[ýÿ]', 'y', text)
        text = re.sub(r'[ñ]', 'n', text)
        text = re.sub(r'[ç]', 'c', text)
        text = re.sub(r'[^a-z0-9]+', '_', text)
        return text.strip('_')[:50]

    def _is_database_initialized(self):
        """Vérifie si la base de données est déjà initialisée avec Odoo"""
        self.ensure_one()

        db_host = self.env['ir.config_parameter'].sudo().get_param('db_host', 'localhost')
        db_port = int(self.env['ir.config_parameter'].sudo().get_param('db_port', '5432'))
        db_user = self.env['ir.config_parameter'].sudo().get_param('db_user', 'odoo')
        db_password = self.env['ir.config_parameter'].sudo().get_param('db_password', '')

        try:
            # Connexion à la base client
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=self.database_name,
            )
            cursor = conn.cursor()

            try:
                # Vérifier si la table ir_module_module existe (signe d'une base Odoo initialisée)
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'ir_module_module'
                    )
                """)
                exists = cursor.fetchone()[0]
                return exists

            finally:
                cursor.close()
                conn.close()

        except psycopg2.OperationalError:
            # La base n'existe pas ou n'est pas accessible
            return False
        except Exception as e:
            _logger.error(f"[SAAS] Erreur vérification initialisation {self.database_name}: {str(e)}")
            return False

    def _create_postgresql_database(self):
        """Crée la base PostgreSQL (skip si existe déjà)"""
        self.ensure_one()

        _logger.info(f"[SAAS] Création base PostgreSQL: {self.database_name}")

        # Récupérer les paramètres de connexion PostgreSQL
        db_host = self.env['ir.config_parameter'].sudo().get_param('db_host', 'localhost')
        db_port = int(self.env['ir.config_parameter'].sudo().get_param('db_port', '5432'))
        db_user = self.env['ir.config_parameter'].sudo().get_param('db_user', 'odoo')
        db_password = self.env['ir.config_parameter'].sudo().get_param('db_password', '')

        # Connexion à PostgreSQL en tant que superuser
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database='postgres',
        )
        conn.autocommit = True
        cursor = conn.cursor()

        try:
            # Vérifier si la base existe déjà
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database_name,)
            )
            if cursor.fetchone():
                _logger.warning(f"[SAAS] Base PostgreSQL {self.database_name} existe déjà, skip création")
                return  # Skip si existe déjà

            # Créer la base
            cursor.execute(f'CREATE DATABASE "{self.database_name}" ENCODING \'UTF8\'')
            _logger.info(f"[SAAS] Base PostgreSQL {self.database_name} créée")

        finally:
            cursor.close()
            conn.close()

    def _initialize_odoo_database(self):
        """Initialise la base Odoo avec les modules de base (skip si déjà initialisée)"""
        self.ensure_one()

        _logger.info(f"[SAAS] Initialisation Odoo pour {self.database_name}")

        import odoo
        from odoo import sql_db

        # Vérifier si la base est déjà initialisée
        if self._is_database_initialized():
            _logger.warning(f"[SAAS] Base {self.database_name} déjà initialisée, skip initialisation")
            return

        # Modules à installer selon le plan
        modules_to_install = ['base', 'web', 'mail', 'contacts']

        # Ajouter modules selon le plan
        if self.plan_id.name in ['Pro', 'Enterprise']:
            modules_to_install.extend(['account', 'sale', 'crm', 'website'])

        # Ajouter onedesk_core (version client, sans le SaaS manager)
        modules_to_install.append('onedesk_core')

        # Initialiser la base avec odoo.service.db
        try:
            odoo.service.db.exp_create_database(
                db_name=self.database_name,
                demo=False,
                lang='fr_FR',
                user_password='admin',  # Sera changé après
                login='admin',
                country_code='FR',
            )
            _logger.info(f"[SAAS] Base Odoo {self.database_name} initialisée")
        except Exception as e:
            _logger.error(f"[SAAS] Erreur initialisation Odoo: {str(e)}")
            raise

    def _create_client_admin(self):
        """Crée l'utilisateur admin client et retourne le password"""
        self.ensure_one()

        _logger.info(f"[SAAS] Création admin client pour {self.database_name}")

        # Générer un mot de passe sécurisé
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        admin_password = ''.join(secrets.choice(alphabet) for i in range(16))

        # Créer l'utilisateur dans la base client
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(self.database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # Modifier l'utilisateur admin existant
            admin_user = env['res.users'].search([('login', '=', 'admin')], limit=1)

            if admin_user:
                admin_user.write({
                    'name': self.name,
                    'login': self.email,
                    'email': self.email,
                    'password': admin_password,
                })

            cr.commit()

        # Sauvegarder les credentials
        self.write({
            'admin_login': self.email,
            'admin_password_temp': admin_password,
        })

        return admin_password

    def _configure_client_company(self):
        """Configure la company par défaut de la base client"""
        self.ensure_one()

        _logger.info(f"[SAAS] Configuration company pour {self.database_name}")

        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(self.database_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # Récupérer la company principale
            main_company = env['res.company'].search([], limit=1)

            if main_company:
                main_company.write({
                    'name': self.company_name,
                    'email': self.email,
                    'phone': self.phone or '',
                })

            cr.commit()

    def _register_database(self):
        """Enregistre l'instance de base dans saas.database"""
        self.ensure_one()

        database = self.env['saas.database'].create({
            'client_id': self.id,
            'name': self.database_name,
            'state': 'active',
            'plan_id': self.plan_id.id,
        })

        self.write({'database_id': database.id})

    def _send_welcome_email(self, admin_password):
        """Envoie l'email de bienvenue avec les credentials"""
        self.ensure_one()

        if not self.email:
            _logger.warning(f"[SAAS] Impossible d'envoyer email pour {self.name} - email manquant")
            return

        _logger.info(f"[SAAS] Envoi email bienvenue à {self.email}")

        try:
            # Récupérer le template email
            template = self.env.ref('onedesk_core.email_template_client_welcome', raise_if_not_found=False)

            if not template:
                _logger.error("[SAAS] Template email 'email_template_client_welcome' introuvable")
                # Fallback: message dans le chatter
                self.message_post(
                    body=f"⚠️ Email NON envoyé (template manquant)<br/>"
                         f"Destinataire: {self.email}<br/>"
                         f"URL: {self.url}<br/>"
                         f"Login: {self.admin_login}<br/>"
                         f"Password: {admin_password}",
                    subject="Bienvenue sur OneDesk (non envoyé)",
                )
                return

            # Envoyer l'email avec le mot de passe dans le contexte
            template.with_context(admin_password=admin_password).send_mail(
                self.id,
                force_send=True,
                email_values={
                    'email_to': self.email,
                    'email_from': self.env.company.email or 'noreply@basatechno.fr',
                }
            )

            _logger.info(f"[SAAS] Email de bienvenue envoyé à {self.email}")

            # Message dans le chatter pour confirmation
            self.message_post(
                body=f"✅ Email de bienvenue envoyé à {self.email}<br/>"
                     f"URL: <a href='{self.url}'>{self.url}</a><br/>"
                     f"Login: {self.admin_login}<br/>"
                     f"Mot de passe: {admin_password} (envoyé par email)",
                subject="Email de bienvenue envoyé",
            )

        except Exception as e:
            _logger.error(f"[SAAS] Erreur envoi email pour {self.name}: {str(e)}", exc_info=True)
            # Message d'erreur dans le chatter avec les infos
            self.message_post(
                body=f"❌ Erreur envoi email à {self.email}<br/>"
                     f"Erreur: {str(e)}<br/><br/>"
                     f"<strong>Identifiants à communiquer manuellement:</strong><br/>"
                     f"URL: {self.url}<br/>"
                     f"Login: {self.admin_login}<br/>"
                     f"Password: {admin_password}",
                subject="Erreur envoi email de bienvenue",
            )

    def action_suspend(self):
        """Suspendre l'accès à la base client"""
        for client in self:
            client.write({
                'database_state': 'suspended',
                'subscription_state': 'suspended',
            })
            client.message_post(body="⏸️ Base de données suspendue")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Suspendu',
                'message': 'La base de données a été suspendue',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_activate(self):
        """Réactiver l'accès à la base client"""
        for client in self:
            client.write({
                'database_state': 'active',
                'subscription_state': 'active',
            })
            client.message_post(body="✅ Base de données réactivée")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Réactivé',
                'message': 'La base de données a été réactivée',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_terminate(self):
        """Terminer définitivement la base client (attention: irréversible!)"""
        for client in self:
            # TODO: Créer un backup final avant suppression
            client.write({
                'database_state': 'terminated',
                'subscription_state': 'cancelled',
                'cancelled_date': fields.Date.today(),
            })
            client.message_post(body="⚠️ Base de données terminée - Backup final créé")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Terminé',
                'message': 'La base de données a été terminée',
                'type': 'danger',
                'sticky': True,
            }
        }

    def action_reset_and_reprovision(self):
        """Nettoyer complètement et recommencer le provisioning (DANGER!)"""
        self.ensure_one()

        if self.database_state not in ['draft', 'error']:
            raise UserError(
                "Le reprovisioning n'est autorisé que pour les états 'draft' ou 'error'. "
                "Pour une base active, utilisez d'abord action_terminate."
            )

        _logger.warning(f"[SAAS] RESET complet demandé pour {self.name} (DB: {self.database_name})")

        # Connexion PostgreSQL
        db_host = self.env['ir.config_parameter'].sudo().get_param('db_host', 'localhost')
        db_port = int(self.env['ir.config_parameter'].sudo().get_param('db_port', '5432'))
        db_user = self.env['ir.config_parameter'].sudo().get_param('db_user', 'odoo')
        db_password = self.env['ir.config_parameter'].sudo().get_param('db_password', '')

        try:
            # 1. Supprimer le filestore
            import shutil
            import os
            from pathlib import Path
            from odoo.tools import config

            filestore_path = Path(config.filestore(self.database_name))
            if filestore_path.exists():
                shutil.rmtree(filestore_path)
                _logger.info(f"[SAAS] Filestore supprimé: {filestore_path}")

            # 2. Supprimer la base PostgreSQL
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database='postgres',
            )
            conn.autocommit = True
            cursor = conn.cursor()

            try:
                # Terminer toutes les connexions à la base
                cursor.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                      AND pid <> pg_backend_pid()
                """, (self.database_name,))

                # Supprimer la base
                cursor.execute(f'DROP DATABASE IF EXISTS "{self.database_name}"')
                _logger.info(f"[SAAS] Base PostgreSQL supprimée: {self.database_name}")

            finally:
                cursor.close()
                conn.close()

            # 3. Supprimer le saas.database lié si existant
            if self.database_id:
                self.database_id.unlink()

            # 4. Réinitialiser les champs
            self.write({
                'database_state': 'draft',
                'database_error': False,
                'database_id': False,
                'admin_login': False,
                'admin_password_temp': False,
            })

            self.message_post(body="✅ Nettoyage complet effectué - Prêt pour reprovisioning")

            _logger.info(f"[SAAS] Reset terminé pour {self.name}")

        except Exception as e:
            _logger.error(f"[SAAS] Erreur lors du reset de {self.name}: {str(e)}", exc_info=True)
            raise UserError(f"Erreur lors du reset: {str(e)}")

    def cron_collect_metrics(self):
        """Cron: Collecter les métriques de tous les clients actifs"""
        active_clients = self.search([('database_state', '=', 'active')])

        for client in active_clients:
            try:
                client._collect_client_metrics()
            except Exception as e:
                _logger.error(f"[SAAS] Erreur collecte métriques client {client.name}: {str(e)}")

    def _collect_client_metrics(self):
        """Collecte les métriques pour ce client"""
        self.ensure_one()

        import odoo
        from odoo.modules.registry import Registry

        try:
            registry = Registry(self.database_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                # Métrique: Utilisateurs actifs
                active_users = env['res.users'].search_count([('active', '=', True)])

                # Métrique: Stockage utilisé
                cr.execute("SELECT pg_database_size(current_database())")
                db_size_bytes = cr.fetchone()[0]
                db_size_gb = db_size_bytes / (1024**3)

                # Mettre à jour le client
                self.sudo().write({
                    'nb_users': active_users,
                    'storage_used_gb': db_size_gb,
                })

                # Créer les métriques historiques
                self.env['saas.metric'].sudo().create([
                    {
                        'client_id': self.id,
                        'database_id': self.database_id.id,
                        'metric_type': 'users_active',
                        'value': active_users,
                        'unit': 'users',
                    },
                    {
                        'client_id': self.id,
                        'database_id': self.database_id.id,
                        'metric_type': 'storage_used',
                        'value': db_size_gb,
                        'unit': 'GB',
                    }
                ])
        except Exception as e:
            _logger.error(f"[SAAS] Erreur collecte métriques pour {self.name}: {str(e)}")

    # ============================================================
    # FONCTIONNALITÉS SUPER ADMIN
    # ============================================================

    def action_create_backup(self):
        """Créer un backup de la base de données client"""
        self.ensure_one()

        if not self.database_name or self.database_state not in ['active', 'suspended']:
            raise UserError("La base de données doit être active ou suspendue pour créer un backup")

        try:
            import odoo
            import datetime

            _logger.info(f"[SAAS] Création backup pour {self.database_name}")

            # Créer le backup avec Odoo
            backup_format = 'zip'
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{self.database_name}_{timestamp}"

            # Le backup est créé dans le filestore
            odoo.service.db.exp_dump(self.database_name, backup_format)

            self.message_post(
                body=f"💾 Backup créé: {backup_name}.{backup_format}"
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Backup créé',
                    'message': f'Le backup {backup_name} a été créé avec succès',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"[SAAS] Erreur création backup: {str(e)}", exc_info=True)
            raise UserError(f"Erreur lors de la création du backup: {str(e)}")

    def action_download_backup(self):
        """Télécharger un backup complet de la base de données (dump PostgreSQL)"""
        self.ensure_one()

        if not self.database_name or self.database_state == 'draft':
            raise UserError("La base de données doit être provisionnée pour télécharger un backup")

        try:
            import subprocess
            import base64
            import tempfile
            import os
            import datetime

            _logger.info(f"[SAAS] Téléchargement backup pour {self.database_name}")

            # Récupérer les paramètres PostgreSQL
            db_host = self.env['ir.config_parameter'].sudo().get_param('db_host', 'localhost')
            db_port = self.env['ir.config_parameter'].sudo().get_param('db_port', '5432')
            db_user = self.env['ir.config_parameter'].sudo().get_param('db_user', 'odoo')
            db_password = self.env['ir.config_parameter'].sudo().get_param('db_password', '')

            # Créer un fichier temporaire pour le dump
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.database_name}_{timestamp}.sql"

            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sql') as tmp_file:
                tmp_path = tmp_file.name

                # Utiliser pg_dump pour créer un dump complet
                env = os.environ.copy()
                if db_password:
                    env['PGPASSWORD'] = db_password

                cmd = [
                    'pg_dump',
                    '-h', db_host,
                    '-p', db_port,
                    '-U', db_user,
                    '-F', 'c',  # Format custom (compressé)
                    '-b',  # Include blobs
                    '-v',  # Verbose
                    '-f', tmp_path,
                    self.database_name
                ]

                _logger.info(f"[SAAS] Exécution pg_dump: {' '.join(cmd[:-1])} ***")

                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes max
                )

                if result.returncode != 0:
                    raise Exception(f"pg_dump a échoué: {result.stderr}")

                # Lire le fichier
                with open(tmp_path, 'rb') as f:
                    dump_data = f.read()

                # Supprimer le fichier temporaire
                os.unlink(tmp_path)

            # Créer un attachement pour le téléchargement
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': base64.b64encode(dump_data),
                'res_model': 'saas.client',
                'res_id': self.id,
                'type': 'binary',
                'mimetype': 'application/octet-stream',
            })

            self.message_post(
                body=f"📥 Backup complet créé: {filename} ({len(dump_data) / (1024*1024):.2f} MB)",
                attachment_ids=[attachment.id]
            )

            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }

        except subprocess.TimeoutExpired:
            raise UserError("Le backup a pris trop de temps (timeout 10 min)")
        except Exception as e:
            _logger.error(f"[SAAS] Erreur téléchargement backup: {str(e)}", exc_info=True)
            raise UserError(f"Erreur lors du téléchargement du backup: {str(e)}")

    def action_restore_backup(self):
        """Restaurer la base de données depuis un backup (via interface utilisateur)"""
        self.ensure_one()

        # Retourner une action wizard pour uploader et restaurer un backup
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Restauration',
                'message': 'Utilisez le gestionnaire de base de données Odoo pour restaurer un backup',
                'type': 'info',
                'sticky': True,
            }
        }

    def action_connect_as_admin(self):
        """Se connecter directement à la base client en tant qu'admin"""
        self.ensure_one()

        if not self.database_name or self.database_state != 'active':
            raise UserError("La base de données doit être active pour se connecter")

        if not self.admin_login:
            raise UserError("Aucun login admin configuré pour ce client")

        _logger.info(f"[SAAS] Connexion admin à {self.database_name}")

        # Afficher les credentials dans une notification et ouvrir l'URL
        credentials_message = (
            f"<strong>Base:</strong> {self.database_name}<br/>"
            f"<strong>Login:</strong> {self.admin_login}<br/>"
        )

        # Ajouter le mot de passe s'il est disponible
        if self.admin_password_temp:
            credentials_message += f"<strong>Password:</strong> {self.admin_password_temp}<br/>"
        else:
            credentials_message += f"<strong>Password:</strong> (Voir dans le chatter - mot de passe envoyé par email)<br/>"

        credentials_message += f"<br/><strong>URL:</strong> <a href='{self.url}' target='_blank'>{self.url}</a>"

        # Message dans le chatter
        self.message_post(
            body=f"🔐 Connexion admin initiée<br/>{credentials_message}"
        )

        # Construire l'URL avec le login pré-rempli
        login_url = f"{self.url}&login={self.admin_login}" if '?' in self.url else f"{self.url}?login={self.admin_login}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🔐 Connexion Admin',
                'message': credentials_message,
                'type': 'info',
                'sticky': True,
                'next': {
                    'type': 'ir.actions.act_url',
                    'url': login_url,
                    'target': 'new',
                }
            }
        }

    def action_open_database_manager(self):
        """Ouvrir le gestionnaire de base de données Odoo"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')

        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/web/database/manager',
            'target': 'new',
        }

    # ============================================================
    # GESTION DOMAINE PERSONNALISÉ
    # ============================================================

    def action_debug_sudo(self):
        """DEBUG: Tester la configuration sudo depuis Odoo"""
        import os
        import subprocess
        import pwd

        # Récupérer l'utilisateur
        uid = os.getuid()
        try:
            user_info = pwd.getpwuid(uid)
            username = user_info.pw_name
        except:
            username = "unknown"

        # Tester sudo
        try:
            result = subprocess.run(
                ['sudo', '-n', 'whoami'],
                capture_output=True,
                text=True,
                timeout=5
            )
            sudo_works = result.returncode == 0
            sudo_user = result.stdout.strip() if sudo_works else "FAILED"
            sudo_error = result.stderr if not sudo_works else ""
        except Exception as e:
            sudo_works = False
            sudo_user = "EXCEPTION"
            sudo_error = str(e)

        # Message
        msg = (f"🔍 DEBUG SUDO<br/><br/>"
              f"<strong>Utilisateur Odoo:</strong> {username} (UID: {uid})<br/>"
              f"<strong>Sudo fonctionne:</strong> {'✅ OUI' if sudo_works else '❌ NON'}<br/>"
              f"<strong>Sudo user:</strong> {sudo_user}<br/>")

        if not sudo_works:
            msg += f"<strong>Erreur sudo:</strong> {sudo_error}<br/>"

        msg += "<br/><strong>Action requise:</strong><br/>"
        if not sudo_works:
            msg += f"Ajouter dans /etc/sudoers.d/odoo-saas:<br/>"
            msg += f"<code>{username} ALL=(ALL) NOPASSWD: /home/user/odoo/addons/onedesk_core/scripts/*</code>"
        else:
            msg += "✅ Configuration OK!"

        self.message_post(body=msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Debug Sudo',
                'message': f'User: {username} | Sudo: {"OK" if sudo_works else "FAILED"}',
                'type': 'success' if sudo_works else 'danger',
                'sticky': True,
            }
        }

    def action_setup_custom_domain(self, test_mode=False):
        """Configure automatiquement Nginx + SSL pour le domaine personnalisé

        Args:
            test_mode (bool): Si True, utilise le script de test (HTTP only, pas de SSL)
        """
        self.ensure_one()

        if not self.custom_domain:
            raise UserError("Veuillez d'abord saisir un domaine personnalisé")

        if not self.database_name:
            raise UserError("La base de données doit être provisionnée avant de configurer le domaine")

        if self.database_state != 'active':
            raise UserError("La base de données doit être active pour configurer le domaine")

        # Validation du domaine
        if not self._validate_domain_format(self.custom_domain):
            raise ValidationError(
                f"Format de domaine invalide: {self.custom_domain}\n"
                "Format attendu: exemple.com (sans http/https)"
            )

        try:
            mode = "TEST (sans SSL)" if test_mode else "PRODUCTION (avec SSL)"
            _logger.info(f"[SAAS] Configuration domaine {mode}: {self.custom_domain} pour {self.name}")

            # Chemin du script
            import os
            import subprocess
            import shutil

            # Détecter si Nginx est installé
            nginx_available = shutil.which('nginx') is not None

            if nginx_available:
                # Environnement complet avec Nginx
                script_name = 'test_client_domain_local.sh' if test_mode else 'setup_client_domain.sh'
                _logger.info(f"[SAAS] Nginx détecté - Utilisation du script: {script_name}")
            else:
                # Environnement de développement sans Nginx - Mode simulation
                script_name = 'simulate_domain_setup.sh'
                _logger.warning(f"[SAAS] Nginx NON détecté - Mode SIMULATION (pour test intégration seulement)")

            script_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'scripts',
                script_name
            )

            if not os.path.exists(script_path):
                raise UserError(f"Script introuvable: {script_path}")

            # Rendre le script exécutable
            os.chmod(script_path, 0o755)

            # Exécuter le script avec sudo (non-interactif)
            cmd = [
                'sudo',
                '-n',  # Non-interactive: fail if password required
                script_path,
                self.custom_domain,
                self.database_name
            ]

            _logger.info(f"[SAAS] Exécution: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                _logger.error(f"[SAAS] Erreur configuration domaine: {error_msg}")
                raise UserError(
                    f"Erreur lors de la configuration du domaine:\n\n{error_msg}\n\n"
                    "Vérifiez que:\n"
                    "- Le DNS pointe vers ce serveur\n"
                    "- Le port 80/443 est ouvert\n"
                    "- sudo est configuré pour odoo"
                )

            # Succès - logger le résultat
            _logger.info(f"[SAAS] Configuration réussie: {result.stdout}")

            # Mettre à jour SSL status
            self.write({'domain_ssl_active': not test_mode and nginx_available})

            # Mettre à jour l'URL
            self._compute_url()

            # Message de succès
            if not nginx_available:
                msg = (f"🧪 Domaine configuré en MODE SIMULATION!<br/>"
                      f"<strong>Domaine:</strong> {self.custom_domain}<br/>"
                      f"<strong>Mode:</strong> SIMULATION (Nginx non installé)<br/>"
                      f"<strong>⚠️ Attention:</strong> Aucune configuration réelle créée<br/>"
                      f"<strong>Action:</strong> Installez Nginx pour production réelle<br/>"
                      f"<strong>Logs:</strong> /var/log/onedesk/domain_setup.log")
            elif test_mode:
                msg = (f"✅ Domaine configuré en mode TEST!<br/>"
                      f"<strong>Domaine:</strong> {self.custom_domain}<br/>"
                      f"<strong>Mode:</strong> TEST (HTTP seulement, pas de SSL)<br/>"
                      f"<strong>Test:</strong> Ajoutez '127.0.0.1 {self.custom_domain}' dans /etc/hosts<br/>"
                      f"<strong>URL:</strong> <a href='http://{self.custom_domain}'>http://{self.custom_domain}</a>")
            else:
                msg = (f"✅ Domaine personnalisé configuré avec succès!<br/>"
                      f"<strong>Domaine:</strong> {self.custom_domain}<br/>"
                      f"<strong>SSL:</strong> Actif (Let's Encrypt)<br/>"
                      f"<strong>URL:</strong> <a href='https://{self.custom_domain}'>https://{self.custom_domain}</a>")

            self.message_post(body=msg)

            notification_type = 'warning' if not nginx_available else 'success'
            notification_title = 'Simulation' if not nginx_available else ('Succès!' if not test_mode else 'Test configuré!')
            notification_msg = (
                f'Mode SIMULATION - Nginx non installé' if not nginx_available
                else f'Le domaine {self.custom_domain} a été configuré {"en mode TEST" if test_mode else "avec succès"}!'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': notification_title,
                    'message': notification_msg,
                    'type': notification_type,
                    'sticky': not nginx_available,  # Sticky if simulation
                }
            }

        except subprocess.TimeoutExpired:
            raise UserError("La configuration a pris trop de temps (timeout 5 min)")
        except Exception as e:
            _logger.error(f"[SAAS] Erreur configuration domaine: {str(e)}", exc_info=True)
            raise UserError(f"Erreur inattendue: {str(e)}")

    def action_setup_custom_domain_test(self):
        """Configure le domaine en mode TEST (sans SSL)"""
        return self.action_setup_custom_domain(test_mode=True)

    def action_remove_custom_domain(self):
        """Supprime la configuration Nginx + SSL du domaine personnalisé"""
        self.ensure_one()

        if not self.custom_domain:
            raise UserError("Aucun domaine personnalisé à supprimer")

        try:
            _logger.info(f"[SAAS] Suppression domaine {self.custom_domain} pour {self.name}")

            import subprocess
            domain = self.custom_domain

            # Supprimer la configuration Nginx
            subprocess.run([
                'sudo', '-n', 'rm', '-f',
                f'/etc/nginx/sites-enabled/{domain}',
                f'/etc/nginx/sites-available/{domain}'
            ], check=True)

            # Reload Nginx
            subprocess.run(['sudo', '-n', 'systemctl', 'reload', 'nginx'], check=True)

            # Note: On garde les certificats SSL (ils peuvent être réutilisés)
            _logger.info(f"[SAAS] Domaine {domain} supprimé avec succès")

            # Réinitialiser le champ
            self.write({'custom_domain': False})

            self.message_post(body=f"🗑️ Domaine personnalisé {domain} supprimé")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Supprimé',
                    'message': f'Le domaine {domain} a été supprimé',
                    'type': 'info',
                }
            }

        except Exception as e:
            _logger.error(f"[SAAS] Erreur suppression domaine: {str(e)}", exc_info=True)
            raise UserError(f"Erreur lors de la suppression: {str(e)}")

    def _validate_domain_format(self, domain):
        """Valide le format du domaine"""
        if not domain:
            return False

        # Pattern pour valider un nom de domaine
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

        return bool(re.match(pattern, domain))

    @api.constrains('custom_domain')
    def _check_custom_domain(self):
        """Vérifie que le domaine personnalisé n'est pas déjà utilisé"""
        for client in self:
            if client.custom_domain:
                # Validation format
                if not self._validate_domain_format(client.custom_domain):
                    raise ValidationError(
                        f"Format de domaine invalide: {client.custom_domain}\n"
                        "Exemple valide: monentreprise.com"
                    )

                # Vérifier unicité
                duplicate = self.search([
                    ('id', '!=', client.id),
                    ('custom_domain', '=', client.custom_domain)
                ])
                if duplicate:
                    raise ValidationError(
                        f"Le domaine {client.custom_domain} est déjà utilisé par {duplicate.name}"
                    )
