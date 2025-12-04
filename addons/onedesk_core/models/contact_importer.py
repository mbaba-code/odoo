# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)


class ContactImporter(models.TransientModel):
    """
    Wizard pour importer des contacts de conciergeries depuis l'API Sirene (INSEE).

    AVERTISSEMENT LEGAL:
    - Utilise l'API publique Sirene de l'INSEE (données légales)
    - Les données importées sont publiques (SIREN, raison sociale, adresse)
    - Pour le marketing par email, vous DEVEZ respecter le RGPD
    - Obtenez le consentement avant tout envoi marketing
    """
    _name = 'onedesk.contact.importer'
    _description = 'Importateur de Contacts Conciergeries'

    search_keyword = fields.Char(
        string='Mot-clé de recherche',
        default='conciergerie',
        required=True,
        help='Mot-clé pour filtrer les entreprises (ex: conciergerie, gestion locative, etc.)'
    )

    department = fields.Char(
        string='Département',
        help='Code département (ex: 75 pour Paris, 13 pour Marseille). Laissez vide pour toute la France.'
    )

    max_results = fields.Integer(
        string='Nombre maximum de résultats',
        default=100,
        required=True,
        help='Limite le nombre de contacts à importer'
    )

    active_only = fields.Boolean(
        string='Entreprises actives uniquement',
        default=True,
        help='Importer uniquement les entreprises en activité'
    )

    import_count = fields.Integer(
        string='Contacts importés',
        readonly=True,
        default=0
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('importing', 'Import en cours...'),
        ('done', 'Terminé'),
        ('error', 'Erreur')
    ], default='draft', string='État')

    error_message = fields.Text(string='Message d\'erreur', readonly=True)

    def action_import_contacts(self):
        """
        Importe les contacts depuis l'API Sirene de l'INSEE.
        """
        self.ensure_one()
        self.state = 'importing'
        self.import_count = 0

        try:
            # API Sirene de l'INSEE (gratuite et publique)
            base_url = "https://api.insee.fr/entreprises/sirene/V3/siret"

            # Construction de la requête
            params = {
                'q': f'denominationUniteLegale:{self.search_keyword}*',
                'nombre': self.max_results,
            }

            # Filtre par département si spécifié
            if self.department:
                params['q'] += f' AND codeCommuneEtablissement:{self.department}*'

            # Filtre entreprises actives
            if self.active_only:
                params['q'] += ' AND etatAdministratifEtablissement:A'

            _logger.info(f"Import de contacts - Recherche: {params['q']}")

            # Note: L'API Sirene nécessite une clé API gratuite
            # À obtenir sur: https://api.insee.fr/catalogue/
            headers = {
                'Accept': 'application/json',
                'Authorization': '699b7729-261f-4f02-9b77-29261faf02a2'  # À configurer
            }

            # Appel API (version sans authentification pour demo)
            # En production, utilisez l'authentification
            response = self._call_api_sirene(params)

            if not response:
                raise Exception("Impossible de contacter l'API Sirene. Configurez votre clé API.")

            # Traitement des résultats
            contacts_imported = self._process_sirene_results(response)

            self.import_count = contacts_imported
            self.state = 'done'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import réussi !',
                    'message': f'{contacts_imported} contacts importés avec succès.',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"Erreur lors de l'import de contacts: {str(e)}")
            self.state = 'error'
            self.error_message = str(e)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Erreur d\'import',
                    'message': f'Erreur: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def _call_api_sirene(self, params):
        """
        Appelle l'API Sirene avec la clé API stockée dans les paramètres système.
        Si aucune clé n'est configurée, retourne des données de démonstration.
        """
        # Récupérer la clé API depuis les paramètres système Odoo (SÉCURISÉ)
        api_key = self.env['ir.config_parameter'].sudo().get_param('onedesk.sirene_api_key', default='')

        if api_key:
            # MODE PRODUCTION: Appel API réel
            try:
                _logger.info("Appel API Sirene avec clé authentifiée...")
                response = requests.get(
                    "https://api.insee.fr/entreprises/sirene/V3/siret",
                    params=params,
                    headers={
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    _logger.info(f"API Sirene: {response.json().get('header', {}).get('total', 0)} résultats trouvés")
                    return response.json()
                elif response.status_code == 401:
                    _logger.error("API Sirene: Clé API invalide (401 Unauthorized)")
                    raise Exception("Clé API Sirene invalide. Vérifiez votre clé dans Paramètres > Technique > Paramètres système")
                elif response.status_code == 429:
                    _logger.error("API Sirene: Limite de requêtes atteinte (429 Too Many Requests)")
                    raise Exception("Limite de requêtes API atteinte. Réessayez plus tard.")
                else:
                    _logger.error(f"API Sirene: Erreur HTTP {response.status_code}")
                    raise Exception(f"Erreur API Sirene: HTTP {response.status_code}")

            except requests.exceptions.RequestException as e:
                _logger.error(f"Erreur réseau API Sirene: {str(e)}")
                raise Exception(f"Erreur de connexion à l'API Sirene: {str(e)}")
        else:
            # MODE DÉMO: Aucune clé API configurée
            _logger.info("Mode DÉMO activé - Aucune clé API Sirene configurée")
            _logger.info("Pour activer l'API réelle: Paramètres > Technique > Paramètres système > Créer 'onedesk.sirene_api_key'")
            return self._get_demo_data()

    def _get_demo_data(self):
        """
        Retourne des données de démonstration.
        À REMPLACER par l'API Sirene réelle en production.
        """
        return {
            'header': {'total': 3},
            'etablissements': [
                {
                    'siret': '12345678901234',
                    'siren': '123456789',
                    'uniteLegale': {
                        'denominationUniteLegale': 'Conciergerie Premium Paris',
                        'categorieJuridiqueUniteLegale': '5710'
                    },
                    'adresseEtablissement': {
                        'numeroVoieEtablissement': '10',
                        'typeVoieEtablissement': 'RUE',
                        'libelleVoieEtablissement': 'DE LA PAIX',
                        'codePostalEtablissement': '75001',
                        'libelleCommuneEtablissement': 'PARIS'
                    },
                    'periodesEtablissement': [
                        {
                            'etatAdministratifEtablissement': 'A',
                            'activitePrincipaleEtablissement': '96.09Z'
                        }
                    ]
                },
                {
                    'siret': '98765432109876',
                    'siren': '987654321',
                    'uniteLegale': {
                        'denominationUniteLegale': 'Conciergerie Luxe Marseille',
                        'categorieJuridiqueUniteLegale': '5710'
                    },
                    'adresseEtablissement': {
                        'numeroVoieEtablissement': '25',
                        'typeVoieEtablissement': 'AVENUE',
                        'libelleVoieEtablissement': 'DU PRADO',
                        'codePostalEtablissement': '13008',
                        'libelleCommuneEtablissement': 'MARSEILLE'
                    },
                    'periodesEtablissement': [
                        {
                            'etatAdministratifEtablissement': 'A',
                            'activitePrincipaleEtablissement': '96.09Z'
                        }
                    ]
                },
                {
                    'siret': '11122233344455',
                    'siren': '111222333',
                    'uniteLegale': {
                        'denominationUniteLegale': 'Conciergerie Services Lyon',
                        'categorieJuridiqueUniteLegale': '5710'
                    },
                    'adresseEtablissement': {
                        'numeroVoieEtablissement': '5',
                        'typeVoieEtablissement': 'PLACE',
                        'libelleVoieEtablissement': 'BELLECOUR',
                        'codePostalEtablissement': '69002',
                        'libelleCommuneEtablissement': 'LYON'
                    },
                    'periodesEtablissement': [
                        {
                            'etatAdministratifEtablissement': 'A',
                            'activitePrincipaleEtablissement': '96.09Z'
                        }
                    ]
                }
            ]
        }

    """

    def _process_sirene_results(self, response):
        """
        Traite les résultats de l'API Sirene et crée les contacts dans Odoo.
        """
        Partner = self.env['res.partner']
        count = 0

        etablissements = response.get('etablissements', [])

        for etab in etablissements:
            try:
                # Extraction des données
                siret = etab.get('siret', '')
                siren = etab.get('siren', '')

                unite_legale = etab.get('uniteLegale', {})
                nom = unite_legale.get('denominationUniteLegale', 'Entreprise inconnue')

                adresse = etab.get('adresseEtablissement', {})
                rue = self._format_address(adresse)
                code_postal = adresse.get('codePostalEtablissement', '')
                ville = adresse.get('libelleCommuneEtablissement', '')

                periode = etab.get('periodesEtablissement', [{}])[0]
                activite = periode.get('activitePrincipaleEtablissement', '')

                # Vérifier si le contact existe déjà (par SIRET)
                existing = Partner.search([('ref', '=', siret)], limit=1)

                if existing:
                    _logger.info(f"Contact existant ignoré: {nom} (SIRET: {siret})")
                    continue

                # Création du contact
                partner_vals = {
                    'name': nom,
                    'ref': siret,  # SIRET comme référence
                    'company_registry': siren,  # SIREN
                    'street': rue,
                    'zip': code_postal,
                    'city': ville,
                    'country_id': self.env.ref('base.fr').id,  # France
                    'company_id': self.env.company.id,  # Entreprise courante (multi-tenant)
                    'is_company': True,
                    'comment': f'Importé depuis API Sirene\nActivité: {activite}\n\n'
                               f'⚠️ RGPD: Vérifiez le consentement avant envoi marketing',
                }

                # Création
                Partner.create(partner_vals)
                count += 1
                _logger.info(f"Contact créé: {nom} (SIRET: {siret})")

            except Exception as e:
                _logger.error(f"Erreur création contact: {str(e)}")
                continue

        return count

    def _format_address(self, adresse):
        """Formate l'adresse à partir des données Sirene."""
        parts = []

        if adresse.get('numeroVoieEtablissement'):
            parts.append(adresse['numeroVoieEtablissement'])
        if adresse.get('typeVoieEtablissement'):
            parts.append(adresse['typeVoieEtablissement'].lower())
        if adresse.get('libelleVoieEtablissement'):
            parts.append(adresse['libelleVoieEtablissement'].title())

        return ' '.join(parts) if parts else ''

    def action_view_imported_contacts(self):
        """Affiche les contacts importés."""
        self.ensure_one()

        return {
            'name': 'Contacts Importés',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'kanban,list,form',
            'domain': [('is_company', '=', True)],
            'context': {'search_default_customer': 1},
        }
