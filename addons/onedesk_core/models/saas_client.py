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

    @api.depends('subdomain', 'custom_domain')
    def _compute_url(self):
        base_domain = self.env['ir.config_parameter'].sudo().get_param('saas.base_domain', 'onedesk.com')
        for client in self:
            if client.custom_domain:
                client.url = f'https://{client.custom_domain}'
            elif client.subdomain:
                client.url = f'https://{client.subdomain}.{base_domain}'
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

        _logger.info(f"[SAAS] Envoi email bienvenue à {self.email}")

        # TODO: Créer le template email
        # template = self.env.ref('onedesk_core.email_template_client_welcome')
        # template.send_mail(self.id, force_send=True)

        # Pour l'instant, juste un message dans le chatter
        self.message_post(
            body=f"Email de bienvenue à envoyer à {self.email}<br/>"
                 f"URL: {self.url}<br/>"
                 f"Login: {self.admin_login}<br/>"
                 f"Password: {admin_password}",
            subject="Bienvenue sur OneDesk",
        )

    def action_suspend(self):
        """Suspendre l'accès à la base client"""
        for client in self:
            client.write({
                'database_state': 'suspended',
                'subscription_state': 'suspended',
            })
            client.message_post(body="Base de données suspendue")

    def action_activate(self):
        """Réactiver l'accès à la base client"""
        for client in self:
            client.write({
                'database_state': 'active',
                'subscription_state': 'active',
            })
            client.message_post(body="Base de données réactivée")

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
