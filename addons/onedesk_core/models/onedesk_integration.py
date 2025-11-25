import logging
import requests
import hashlib
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config

_logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    import base64
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    _logger.critical(
        "❌ CRITICAL SECURITY ERROR: Le module 'cryptography' n'est pas installé!\n"
        "Les tokens OAuth seront stockés en CLAIR dans la base de données.\n"
        "Installation requise: pip install cryptography"
    )


class OnedeskIntegration(models.Model):
    _name = 'onedesk.integration'
    _description = 'Intégration Plateforme de Réservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Infos de base
    name = fields.Char(string='Nom', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Entreprise', 
                                 default=lambda self: self.env.company, required=True)
    provider_id = fields.Many2one('onedesk.integration.provider', 
                                  string='Plateforme', required=True, tracking=True)
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('connecting', 'Connexion...'),
        ('connected', '✅ Connecté'),
        ('error', '❌ Erreur'),
        ('expired', '⏰ Expiré'),
        ('disconnected', 'Déconnecté'),
    ], default='draft', required=True, tracking=True, string='État')
    
    # Méthode de connexion
    connection_method = fields.Selection([
        ('oauth', 'OAuth 2.0 (Recommandé)'),
        ('ical', 'iCal URL'),
        ('csv', 'Import CSV Manuel'),
    ], string='Méthode', required=True, default='oauth')
    
    # OAuth (chiffré)
    access_token_encrypted = fields.Char(string='Access Token')
    refresh_token_encrypted = fields.Char(string='Refresh Token')
    token_expiry = fields.Datetime(string='Expiration')
    oauth_state = fields.Char(string='OAuth State')
    
    # iCal
    ical_url = fields.Char(string='URL iCal')
    
    # Synchronisation
    last_sync_date = fields.Datetime(string='Dernière sync')
    next_sync_date = fields.Datetime(string='Prochaine sync', compute='_compute_next_sync', store=True)
    sync_frequency = fields.Integer(string='Fréquence (minutes)', default=60)
    auto_sync = fields.Boolean(string='Sync automatique', default=True)
    
    # Statistiques
    total_synced = fields.Integer(string='Total synchronisé', default=0)
    last_sync_count = fields.Integer(string='Dernier count', default=0)
    error_count = fields.Integer(string='Erreurs', default=0)
    last_error = fields.Text(string='Dernière erreur')
    last_error_date = fields.Datetime(string='Date erreur')
    
    # Logs
    log_ids = fields.One2many('onedesk.integration.log', 'integration_id', string='Logs')
    
    # Options de mapping
    auto_create_units = fields.Boolean(string='Créer unités automatiquement', default=True,
                                       help="Si activé, crée automatiquement les unités manquantes")
    auto_create_contacts = fields.Boolean(string='Créer contacts automatiquement', default=True)
    default_unit_id = fields.Many2one('onedesk.unit', string='Unité par défaut',
                                      help="Unité utilisée si le mapping échoue")
    default_property_id = fields.Many2one('onedesk.property', string='Propriété par défaut')
    
    active = fields.Boolean(default=True)

    @api.depends('last_sync_date', 'sync_frequency')
    def _compute_next_sync(self):
        for record in self:
            if record.last_sync_date and record.sync_frequency:
                record.next_sync_date = record.last_sync_date + timedelta(minutes=record.sync_frequency)
            else:
                record.next_sync_date = False

    # ========================================================================
    # CHIFFREMENT
    # ========================================================================
    
    def _get_encryption_key(self):
        """Récupère la clé depuis odoo.conf"""
        key = config.get('onedesk_encryption_key')
        if not key and CRYPTO_AVAILABLE:
            _logger.warning("⚠️ Pas de clé de chiffrement dans odoo.conf")
        return key.encode() if key else None

    def _encrypt_token(self, token):
        """
        Chiffre un token OAuth avec validation stricte

        SECURITY: Le chiffrement est OBLIGATOIRE pour protéger les tokens OAuth.
        Si cryptography n'est pas installé, on refuse de stocker le token.
        """
        if not token:
            return False

        # SECURITY: Refuser de stocker des tokens en clair
        if not CRYPTO_AVAILABLE:
            _logger.error(
                "❌ REFUS: Impossible de chiffrer le token - module cryptography manquant!\n"
                "Installation: pip install cryptography"
            )
            raise UserError(
                "Module de chiffrement 'cryptography' manquant!\n\n"
                "Pour des raisons de sécurité, les tokens OAuth ne peuvent pas être stockés sans chiffrement.\n\n"
                "Installation requise:\n"
                "pip install cryptography"
            )

        try:
            key = self._get_encryption_key()
            if not key:
                raise UserError(
                    "Clé de chiffrement non configurée!\n\n"
                    "Ajoutez dans votre fichier odoo.conf:\n"
                    "onedesk_encryption_key = <générez une clé avec: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'>"
                )

            f = Fernet(key)
            encrypted = f.encrypt(token.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            _logger.error(f"❌ Erreur chiffrement: {e}")
            raise UserError(f"Erreur lors du chiffrement du token: {str(e)}")

    def _decrypt_token(self, encrypted_token):
        """Déchiffre un token"""
        if not encrypted_token:
            return False
        
        if not CRYPTO_AVAILABLE:
            return encrypted_token
        
        try:
            key = self._get_encryption_key()
            if not key:
                return encrypted_token
            
            f = Fernet(key)
            encrypted_bytes = base64.b64decode(encrypted_token.encode())
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            _logger.error(f"Erreur déchiffrement: {e}")
            return False

    # ========================================================================
    # OAUTH
    # ========================================================================
    
    def action_start_oauth_connection(self):
        """Lance le flux OAuth"""
        self.ensure_one()
        
        if not self.provider_id.supports_oauth:
            raise UserError("Cette plateforme ne supporte pas OAuth.\nUtilisez iCal à la place.")
        
        if not self.provider_id.client_id or not self.provider_id.client_secret:
            raise UserError(
                "Configuration OAuth manquante !\n\n"
                "Allez dans : Intégrations → Configuration plateformes → " + self.provider_id.name + "\n"
                "Et configurez le Client ID et Client Secret."
            )
        
        # Génère un state unique
        state = hashlib.sha256(f"{self.id}-{datetime.now()}".encode()).hexdigest()
        
        self.write({
            'oauth_state': state,
            'state': 'connecting',
        })
        
        # URL de redirection
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f"{base_url}/onedesk/integration/oauth/callback"
        
        # Construit l'URL d'autorisation
        auth_url = (
            f"{self.provider_id.oauth_authorize_url}?"
            f"client_id={self.provider_id.client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"state={state}&"
            f"scope={self.provider_id.oauth_scope or ''}"
        )
        
        _logger.info(f"🔗 OAuth redirect vers {self.provider_id.name}")
        
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'new',
        }
    
    def handle_oauth_callback(self, code, state):
        """Traite le callback OAuth"""
        self.ensure_one()
        
        if state != self.oauth_state:
            raise ValidationError("État OAuth invalide - possible attaque CSRF")
        
        try:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            
            _logger.info(f"📡 Échange du code OAuth pour {self.provider_id.name}")
            
            response = requests.post(
                self.provider_id.oauth_token_url,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': f"{base_url}/onedesk/integration/oauth/callback",
                    'client_id': self.provider_id.client_id,
                    'client_secret': self.provider_id.client_secret,
                },
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            self.write({
                'access_token_encrypted': self._encrypt_token(token_data.get('access_token')),
                'refresh_token_encrypted': self._encrypt_token(token_data.get('refresh_token')),
                'token_expiry': datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
                'state': 'connected',
                'oauth_state': False,
                'error_count': 0,
            })
            
            self._log('success', f"✅ Connexion OAuth réussie")

            # Lance première sync
            self.action_sync_now()
            
        except Exception as e:
            error_msg = f"Erreur OAuth: {str(e)}"
            _logger.error(error_msg, exc_info=True)
            self.write({
                'state': 'error',
                'last_error': error_msg,
                'last_error_date': fields.Datetime.now(),
                'error_count': self.error_count + 1,
            })
            raise UserError(error_msg)
    
    def _get_valid_token(self):
        """Retourne un token valide"""
        self.ensure_one()
        
        if self.token_expiry and self.token_expiry <= datetime.now():
            self._refresh_token()
        
        return self._decrypt_token(self.access_token_encrypted)
    
    def _refresh_token(self):
        """Rafraîchit le token"""
        self.ensure_one()
        
        if not self.refresh_token_encrypted:
            self.write({'state': 'expired'})
            return False
        
        try:
            refresh_token = self._decrypt_token(self.refresh_token_encrypted)
            
            response = requests.post(
                self.provider_id.oauth_token_url,
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': refresh_token,
                    'client_id': self.provider_id.client_id,
                    'client_secret': self.provider_id.client_secret,
                },
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            
            self.write({
                'access_token_encrypted': self._encrypt_token(token_data.get('access_token')),
                'refresh_token_encrypted': self._encrypt_token(token_data.get('refresh_token', refresh_token)),
                'token_expiry': datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600)),
                'state': 'connected',
            })
            
            return True
            
        except Exception as e:
            _logger.error(f"Erreur refresh token: {e}")
            self.write({'state': 'expired'})
            return False

    # ========================================================================
    # SYNCHRONISATION
    # ========================================================================
    
    def action_sync_now(self):
        """Synchronise maintenant"""
        for record in self:
            try:
                _logger.info(f"🔄 Début sync {record.provider_id.name} (méthode: {record.connection_method})")
                
                if record.connection_method == 'oauth':
                    # Vérifie que c'est connecté
                    if record.state != 'connected':
                        raise UserError("Vous devez d'abord vous connecter via OAuth")
                    count = record._sync_oauth()
                    
                elif record.connection_method == 'ical':
                    # iCal ne nécessite pas de connexion
                    if not record.ical_url:
                        raise UserError("Veuillez d'abord renseigner l'URL iCal dans l'onglet Configuration")
                    count = record._sync_ical()
                    
                else:
                    raise UserError("Méthode non supportée")
                
                record.sudo().write({
                    'last_sync_date': fields.Datetime.now(),
                    'last_sync_count': count,
                    'total_synced': record.total_synced + count,
                    'state': 'connected',
                    'error_count': 0,
                })
                
                record._log('success', f"✅ {count} réservations synchronisées")
                
            except Exception as e:
                error_msg = f"Erreur synchronisation: {str(e)}"
                _logger.error(error_msg, exc_info=True)
                record.sudo().write({
                    'state': 'error',
                    'last_error': error_msg,
                    'last_error_date': fields.Datetime.now(),
                    'error_count': record.error_count + 1,
                })
                record._log('error', error_msg)
        
        return True
    
    def _sync_oauth(self):
        """Sync via OAuth API"""
        self.ensure_one()
        
        token = self._get_valid_token()
        if not token:
            raise UserError("Token invalide - merci de reconnecter")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        
        # Endpoint API (à adapter selon plateforme)
        api_url = f"{self.provider_id.api_base_url}/reservations"
        params = {
            'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        reservations_data = self._parse_provider_response(data)
        
        count = 0
        for res_data in reservations_data:
            if self._process_reservation(res_data):
                count += 1
        
        return count
    
    def _sync_ical(self):
        """Sync via iCal"""
        self.ensure_one()
        
        if not self.ical_url:
            raise UserError("URL iCal manquante")
        
        try:
            from icalendar import Calendar
        except ImportError:
            raise UserError(
                "Module icalendar manquant !\n\n"
                "Installez-le avec : pip install icalendar"
            )
        
        _logger.info(f"📥 Import iCal depuis {self.ical_url}")
        
        response = requests.get(self.ical_url, timeout=30)
        response.raise_for_status()
        
        cal = Calendar.from_ical(response.content)
        
        count = 0
        for component in cal.walk():
            if component.name == "VEVENT":
                description = str(component.get('description', ''))
                
                # Parse la description pour extraire les infos
                guest_info = self._parse_ical_description(description)
                
                res_data = {
                    'id': str(component.get('uid')),
                    'name': str(component.get('summary', 'Réservation')),
                    'unit_name': str(component.get('summary', '')),  # FIX BUG #1: Map SUMMARY to unit_name
                    'start_date': component.get('dtstart').dt if component.get('dtstart') else False,
                    'end_date': component.get('dtend').dt if component.get('dtend') else False,
                    'description': description,
                    'location': str(component.get('location', '')),
                    'guest_name': guest_info.get('guest_name'),
                    'guest_email': guest_info.get('guest_email'),
                    'guest_phone': guest_info.get('guest_phone'),
                    'price': guest_info.get('price'),
                    'adults': guest_info.get('adults'),
                    'children': guest_info.get('children'),
                }
                if self._process_reservation(res_data):
                    count += 1
        
        return count
    
    def _parse_ical_description(self, description):
        """Parse la description iCal pour extraire les infos client"""
        import re
        
        info = {}
        
        # Nettoie les caractères d'échappement
        description = description.replace('\\n', '\n').replace('\\,', ',')
        
        # Cherche le nom du voyageur
        match = re.search(r'Voyageur:\s*([^\n]+)', description, re.IGNORECASE)
        if match:
            info['guest_name'] = match.group(1).strip()
        
        # Cherche l'email (si présent)
        match = re.search(r'Email:\s*([^\n]+)', description, re.IGNORECASE)
        if match:
            info['guest_email'] = match.group(1).strip()
        
        # Cherche le téléphone (si présent)
        match = re.search(r'(Phone|Téléphone|Tel):\s*([^\n]+)', description, re.IGNORECASE)
        if match:
            info['guest_phone'] = match.group(2).strip()
        
        # Cherche le prix
        match = re.search(r'Prix:\s*([0-9.,]+)', description, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '.')
            try:
                info['price'] = float(price_str)
            except:
                pass
        
        # Cherche le nombre d'adultes
        match = re.search(r'Adultes:\s*([0-9]+)', description, re.IGNORECASE)
        if match:
            info['adults'] = int(match.group(1))
        
        # Cherche le nombre d'enfants
        match = re.search(r'Enfants:\s*([0-9]+)', description, re.IGNORECASE)
        if match:
            info['children'] = int(match.group(1))
        
        return info
    
    def _parse_provider_response(self, data):
        """Parse la réponse selon le provider"""
        provider_code = self.provider_id.code
        
        if provider_code == 'airbnb':
            return data.get('reservations', [])
        elif provider_code == 'booking':
            return data.get('reservations', [])
        elif provider_code == 'vrbo':
            return data.get('bookings', [])
        else:
            return data.get('data', data.get('reservations', []))
    
    def _process_reservation(self, data):
        """Traite une réservation et l'importe dans OneDesk"""
        self.ensure_one()

        # Validation des données minimales requises
        if not data.get('id'):
            _logger.warning("⚠️ Réservation ignorée: ID manquant")
            return False

        if not data.get('start_date') and not data.get('checkin'):
            _logger.warning(f"⚠️ Réservation {data.get('id')} ignorée: date de début manquante")
            return False

        if not data.get('end_date') and not data.get('checkout'):
            _logger.warning(f"⚠️ Réservation {data.get('id')} ignorée: date de fin manquante")
            return False

        external_id = f"{self.provider_id.code}:{data.get('id')}"

        # Cherche si existe déjà
        Reservation = self.env['onedesk.reservation']
        existing = Reservation.search([
            ('external_id', '=', external_id),
        ], limit=1)
        
        # Trouve l'unité
        unit = self._find_or_create_unit(data)
        if not unit:
            _logger.warning(f"⚠️ Impossible de mapper l'unité pour {data.get('name')}")
            if not self.default_unit_id:
                return False
            unit = self.default_unit_id
        
        # Trouve le contact
        partner = self._find_or_create_contact(data)
        if not partner:
            # Si impossible de créer le contact, on crée un contact générique
            try:
                partner = self.env['res.partner'].sudo().create({
                    'name': 'Client externe',
                    'comment': f"Réservation importée depuis {self.provider_id.name}",
                    'company_id': self.company_id.id,  # Assigner la compagnie
                })
                _logger.info(f"👤 Contact générique créé")
            except Exception as e:
                _logger.error(f"❌ Impossible de créer le contact: {e}")
                return False
        
        # Prépare les valeurs (ADAPTÉ À TA STRUCTURE)
        vals = {
            'name': data.get('name', 'Réservation'),
            'unit_id': unit.id,
            'partner_id': partner.id,
            'start_date': data.get('start_date') or data.get('checkin'),
            'end_date': data.get('end_date') or data.get('checkout'),
            'external_id': external_id,
            'integration_id': self.id,
        }
        
        if existing:
            existing.write(vals)
            _logger.info(f"📝 Mise à jour réservation {existing.name}")
            reservation = existing
        else:
            reservation = Reservation.create(vals)
            _logger.info(f"✅ Nouvelle réservation créée: {vals['name']}")

        # Force la création de l'événement calendrier si pas déjà créé
        if reservation and not reservation.calendar_event_id:
            try:
                # Crée l'événement visible pour tout le monde
                # Accès aux données du partenaire avec sudo() pour contourner les ir.rules
                partner_name = reservation.sudo().partner_id.name if reservation.partner_id else 'N/A'
                event = self.env['calendar.event'].sudo().create({
                    'name': f"{reservation.name} - {reservation.unit_id.name}",
                    'start': reservation.start_date,
                    'stop': reservation.end_date,
                    'description': f"Réservation importée depuis {self.provider_id.name}\n"
                                   f"Client: {partner_name}\n"
                                   f"Unité: {reservation.unit_id.name}",
                    'location': reservation.unit_id.name,
                    'allday': False,
                    'privacy': 'public',
                    'show_as': 'busy',
                })
                # Assignement du calendar_event_id avec sudo() pour contourner les ir.rules
                reservation.sudo().write({'calendar_event_id': event.id})
                _logger.info(f"📅 Événement calendrier créé pour {reservation.name}")
            except Exception as e:
                _logger.warning(f"⚠️ Impossible de créer l'événement calendrier: {e}")

        return True

    def _extract_property_name_from_location(self, location):
        """Extract a meaningful property name from location address

        Examples:
        "42 Rue des Francs-Bourgeois, 75004 Paris, France" → "Paris" or "75004 Paris"
        "123 Rue de la Paix, 69000 Lyon, France" → "Lyon" or "69000 Lyon"
        """
        if not location:
            return 'Propriété importée'

        # Clean up escaped characters
        location = location.replace('\\,', ',')

        # Split by comma to get parts
        parts = [p.strip() for p in location.split(',')]

        if len(parts) >= 2:
            # Try to extract postal code + city pattern (e.g., "75004 Paris")
            # Usually the second-to-last part is postal code + city
            postal_city = parts[-2] if len(parts) >= 2 else parts[-1]
            # Pattern: "12345 CityName"
            import re
            match = re.match(r'(\d{5})\s+(.+)', postal_city.strip())
            if match:
                return f"{match.group(2)}"  # Return just the city name
            else:
                # If no postal code, return the second-to-last part as is
                return postal_city.strip()

        # Fallback: return the whole location
        return location[:50] if len(location) > 50 else location

    def _find_or_create_property(self, data):
        """Trouve ou crée la propriété pour une unité importée"""
        # FIX BUG #2: Extract meaningful property name from location
        property_name = (
            data.get('property_name') or
            data.get('listing_name') or
            self._extract_property_name_from_location(data.get('location')) or
            'Propriété importée'
        )

        Property = self.env['onedesk.property']

        # Cherche une propriété correspondante
        prop = Property.search([
            ('name', 'ilike', property_name),
        ], limit=1)

        # Crée une propriété si elle n'existe pas
        if not prop:
            prop = Property.sudo().create({
                'name': property_name,
                'address': data.get('location', ''),
                'property_type': 'apartment',  # Par défaut
                'description': f"Propriété importée depuis {self.provider_id.name}",
                'company_id': self.company_id.id,
            })
            _logger.info(f"🏘️ Nouvelle propriété créée: {property_name}")

        return prop

    def _find_or_create_unit(self, data):
        """Trouve ou crée l'unité"""
        # FIX BUG #3: unit_name should come from iCal SUMMARY (now properly mapped in _sync_ical)
        unit_name = data.get('unit_name') or data.get('listing_name')

        # Extract property name using the same logic as _find_or_create_property
        property_name = (
            data.get('property_name') or
            data.get('listing_name') or
            self._extract_property_name_from_location(data.get('location')) or
            'Propriété importée'
        )

        Unit = self.env['onedesk.unit']
        external_listing_id = data.get('external_listing_id') or data.get('listing_id')

        # Cherche par ID externe en priorité (déduplication)
        unit = False
        if external_listing_id:
            unit = Unit.search([
                ('external_listing_id', '=', external_listing_id),
                ('integration_id', '=', self.id),
            ], limit=1)

        # Sinon cherche par nom + propriété
        if not unit and unit_name:
            unit = Unit.search([
                ('name', 'ilike', unit_name),
                ('property_id.name', 'ilike', property_name),
            ], limit=1)

        # Crée l'unité si elle n'existe pas et auto_create_units est actif
        if not unit and self.auto_create_units:
            # Auto-crée la propriété associée
            property_id = self._find_or_create_property(data)

            # Génère un nom d'unité unique si pas fourni
            if not unit_name:
                # Compte le nombre d'unités existantes dans la propriété
                unit_count = Unit.search_count([
                    ('property_id', '=', property_id.id),
                ]) + 1
                unit_name = f"{property_name} - Unité {unit_count}"

            # Extrait les infos disponibles pour enrichir l'unité
            capacity = data.get('capacity') or data.get('guests') or 2
            bedrooms = data.get('bedrooms') or 1
            bathrooms = data.get('bathrooms') or 1
            price = data.get('price') or data.get('price_per_night') or 100.0

            unit = Unit.sudo().create({
                'name': unit_name,
                'property_id': property_id.id if property_id else (self.default_property_id.id if self.default_property_id else False),
                'external_listing_id': external_listing_id,
                'integration_id': self.id,
                'available': True,
                'capacity': capacity,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'price_per_night': price,
                'company_id': self.company_id.id,
            })
            _logger.info(f"🏠 Nouvelle unité créée: {unit_name} (Propriété: {property_id.name if property_id else 'N/A'}, Cap: {capacity}, Lit: {bedrooms}, SdB: {bathrooms}, Prix: {price}€)")

        return unit
    
    def _find_or_create_contact(self, data):
        """Trouve ou crée le contact avec plus d'infos"""
        guest_email = data.get('guest_email')
        guest_name = data.get('guest_name')
        guest_phone = data.get('guest_phone')

        # Si pas de nom ET pas d'email, on ne peut pas créer de contact
        if not guest_email and not guest_name:
            return False

        Partner = self.env['res.partner']

        # Cherche d'abord par email (sudo() pour contourner les ir.rules)
        if guest_email:
            partner = Partner.sudo().search([('email', '=', guest_email)], limit=1)
            if partner:
                # S'assurer que le partenaire trouvé a une company_id assignée
                if not partner.company_id:
                    partner.sudo().write({'company_id': self.company_id.id})
                    # Invalider le cache et recharger le partenaire
                    self.env.invalidate_all()
                    partner = Partner.sudo().browse(partner.id)
                return partner

        # Puis par nom (sudo() pour contourner les ir.rules)
        if guest_name:
            partner = Partner.sudo().search([('name', '=', guest_name)], limit=1)
            if partner:
                # S'assurer que le partenaire trouvé a une company_id assignée
                if not partner.company_id:
                    partner.sudo().write({'company_id': self.company_id.id})
                    # Invalider le cache et recharger le partenaire
                    self.env.invalidate_all()
                    partner = Partner.sudo().browse(partner.id)
                return partner

        # Crée le contact avec toutes les infos disponibles
        if self.auto_create_contacts:
            # IMPORTANT : Assure qu'il y a toujours un nom
            contact_name = guest_name or guest_email or 'Client externe'

            partner = Partner.sudo().create({
                'name': contact_name,
                'email': guest_email if guest_email else False,
                'phone': guest_phone if guest_phone else False,
                'comment': f"Importé depuis {self.provider_id.name}",
                'company_id': self.company_id.id,  # Assigner la compagnie
            })
            _logger.info(f"👤 Contact créé: {partner.name}")
            return partner

        return False
    
    def _log(self, log_type, message):
        """Crée un log"""
        self.env['onedesk.integration.log'].sudo().create({
            'integration_id': self.id,
            'log_type': log_type,
            'message': message,
        })

    # ========================================================================
    # ACTIONS
    # ========================================================================
    
    def action_reconnect(self):
        """Reconnecte"""
        for record in self:
            if record.connection_method == 'oauth':
                return record.action_start_oauth_connection()
            else:
                record.write({'state': 'draft'})
    
    def action_disconnect(self):
        """Déconnecte"""
        self.write({
            'state': 'disconnected',
            'access_token_encrypted': False,
            'refresh_token_encrypted': False,
            'token_expiry': False,
            'active': False,
        })
    
    def action_view_logs(self):
        """Affiche les logs"""
        self.ensure_one()
        return {
            'name': 'Logs de synchronisation',
            'type': 'ir.actions.act_window',
            'res_model': 'onedesk.integration.log',
            'view_mode': 'list,form',
            'domain': [('integration_id', '=', self.id)],
        }

    # ========================================================================
    # CRON
    # ========================================================================
    
    @api.model
    def cron_sync_integrations(self):
        """Cron job automatique"""
        integrations = self.search([
            ('auto_sync', '=', True),
            ('state', '=', 'connected'),
            ('active', '=', True),
        ])
        
        _logger.info(f"🤖 Cron: {len(integrations)} intégrations à synchroniser")
        
        for integration in integrations:
            try:
                if integration.next_sync_date and integration.next_sync_date <= datetime.now():
                    integration.action_sync_now()
            except Exception as e:
                _logger.error(f"❌ Erreur cron {integration.id}: {e}")
                continue
        
        return True