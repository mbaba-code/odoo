# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)


class ContactImporter(models.TransientModel):
    """
    Wizard pour importer des contacts de conciergeries depuis l'API Sirene (INSEE).
    """
    _name = 'onedesk.contact.importer'
    _description = 'Importateur de Contacts Conciergeries'

    search_keyword = fields.Char(
        string='Mot-clé de recherche',
        default='conciergerie',
        help='Mot-clé pour filtrer les entreprises (ex: conciergerie, gestion locative, etc.). Optionnel si code NAF spécifié.'
    )

    department = fields.Char(
        string='Département',
        help='Code département (ex: 75 pour Paris, 13 pour Marseille). Laissez vide pour toute la France.'
    )

    naf_code = fields.Char(
        string='Code NAF',
        help='Code NAF pour filtrer par activité (ex: 81.21Z pour nettoyage, 96.09Z pour services). Laissez vide si non utilisé.'
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
            # Construction du paramètre q
            q_parts = []

            # Mot-clé (optionnel si NAF spécifié)
            keyword = self.search_keyword.strip().replace('"', '') if self.search_keyword else ''
            if keyword:
                q_parts.append(f'denominationUniteLegale:{keyword}')

            # Au moins un critère requis (keyword OU NAF)
            if not keyword and not self.naf_code:
                raise Exception("Veuillez spécifier au moins un mot-clé OU un code NAF.")

            if self.department:
                # On suppose que l'utilisateur met un code département ou code commune
                q_parts.append(f"codeCommuneEtablissement:{self.department}")

            if self.naf_code:
                # Code NAF pour filtrer par activité principale
                naf_clean = self.naf_code.strip().replace('.', '')  # Enlever le point si présent
                q_parts.append(f"activitePrincipaleUniteLegale:{naf_clean}")

            #if self.active_only:
               # q_parts.append('etatAdministratifEtablissement:A')

            q_string = " AND ".join(q_parts)
            _logger.info(f"Import de contacts - Recherche: {q_string}")

            params = {
                'q': q_string,
                'nombre': self.max_results,
            }

            # Appel API
            response = self._call_api_sirene(params)

            if not response:
                raise Exception("Impossible de contacter l'API Sirene. Vérifiez votre clé API.")

            # Filtrage partiel côté Python (uniquement si keyword spécifié)
            etablissements = response.get('etablissements', [])
            if keyword:
                etablissements = [
                    e for e in etablissements
                    if keyword.lower() in e.get('uniteLegale', {}).get('denominationUniteLegale', '').lower()
                ]

            contacts_imported = self._process_sirene_results(etablissements)

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
        """
        api_key = self.env['ir.config_parameter'].sudo().get_param('onedesk.sirene_api_key', default='')

        if not api_key:
            _logger.info("Mode DÉMO activé - Aucune clé API Sirene configurée")
            return self._get_demo_data()

        try:
            _logger.info("Appel API Sirene avec clé authentifiée...")
            response = requests.get(
                "https://api.insee.fr/api-sirene/3.11/siret",
                params=params,
                headers={
                    'Accept': 'application/json',
                    'X-INSEE-Api-Key-Integration': api_key
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                raise Exception("Erreur API Sirene: Syntaxe invalide dans le paramètre q")
            elif response.status_code == 401:
                raise Exception("Clé API Sirene invalide (401 Unauthorized)")
            elif response.status_code == 429:
                raise Exception("Limite de requêtes API atteinte (429 Too Many Requests)")
            else:
                raise Exception(f"Erreur API Sirene: HTTP {response.status_code}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erreur de connexion à l'API Sirene: {str(e)}")

    def _get_demo_data(self):
        """
        Données de démonstration si aucune clé API n'est configurée.
        """
        return {
            'header': {'total': 3},
            'etablissements': [
                {
                    'siret': '12345678901234',
                    'siren': '123456789',
                    'uniteLegale': {'denominationUniteLegale': 'Conciergerie Premium Paris', 'categorieJuridiqueUniteLegale': '5710'},
                    'adresseEtablissement': {'numeroVoieEtablissement': '10', 'typeVoieEtablissement': 'RUE', 'libelleVoieEtablissement': 'DE LA PAIX', 'codePostalEtablissement': '75001', 'libelleCommuneEtablissement': 'PARIS'},
                    'periodesEtablissement': [{'etatAdministratifEtablissement': 'A', 'activitePrincipaleEtablissement': '96.09Z'}]
                },
                {
                    'siret': '98765432109876',
                    'siren': '987654321',
                    'uniteLegale': {'denominationUniteLegale': 'Conciergerie Luxe Marseille', 'categorieJuridiqueUniteLegale': '5710'},
                    'adresseEtablissement': {'numeroVoieEtablissement': '25', 'typeVoieEtablissement': 'AVENUE', 'libelleVoieEtablissement': 'DU PRADO', 'codePostalEtablissement': '13008', 'libelleCommuneEtablissement': 'MARSEILLE'},
                    'periodesEtablissement': [{'etatAdministratifEtablissement': 'A', 'activitePrincipaleEtablissement': '96.09Z'}]
                },
                {
                    'siret': '11122233344455',
                    'siren': '111222333',
                    'uniteLegale': {'denominationUniteLegale': 'Conciergerie Services Lyon', 'categorieJuridiqueUniteLegale': '5710'},
                    'adresseEtablissement': {'numeroVoieEtablissement': '5', 'typeVoieEtablissement': 'PLACE', 'libelleVoieEtablissement': 'BELLECOUR', 'codePostalEtablissement': '69002', 'libelleCommuneEtablissement': 'LYON'},
                    'periodesEtablissement': [{'etatAdministratifEtablissement': 'A', 'activitePrincipaleEtablissement': '96.09Z'}]
                }
            ]
        }

    def _process_sirene_results(self, etablissements):
        """
        Crée les contacts Odoo à partir des établissements récupérés.
        """
        Partner = self.env['res.partner']
        count = 0

        for etab in etablissements:
            try:
                siret = etab.get('siret', '')
                siren = etab.get('siren', '')
                unite_legale = etab.get('uniteLegale', {})
                nom = unite_legale.get('denominationUniteLegale', 'Entreprise inconnue')

                adresse = etab.get('adresseEtablissement', {})
                rue = self._format_address(adresse)
                code_postal = adresse.get('codePostalEtablissement', '')
                ville = adresse.get('libelleCommuneEtablissement', '')

                periodes = etab.get('periodesEtablissement', [])
                periode = periodes[0] if periodes else {}
                activite = periode.get('activitePrincipaleEtablissement', '')

                existing = Partner.search([('ref', '=', siret)], limit=1)
                if existing:
                    _logger.info(f"Contact existant ignoré: {nom} (SIRET: {siret})")
                    continue

                partner_vals = {
                    'name': nom,
                    'ref': siret,
                    'company_registry': siren,
                    'street': rue,
                    'zip': code_postal,
                    'city': ville,
                    'country_id': self.env.ref('base.fr').id,
                    'company_id': self.env.company.id,
                    'is_company': True,
                    'comment': f'Importé depuis API Sirene\nActivité: {activite}\n⚠️ RGPD: Vérifiez le consentement avant envoi marketing',
                }

                Partner.create(partner_vals)
                count += 1
                _logger.info(f"Contact créé: {nom} (SIRET: {siret})")

            except Exception as e:
                _logger.error(f"Erreur création contact: {str(e)}")
                continue

        return count

    def _format_address(self, adresse):
        """
        Formate correctement l'adresse complète depuis l'API Sirene.
        """
        parts = []
        numero = adresse.get('numeroVoieEtablissement', '')
        type_voie = adresse.get('typeVoieEtablissement', '')
        libelle = adresse.get('libelleVoieEtablissement', '')

        if numero:
            parts.append(numero)
        if type_voie:
            parts.append(type_voie.lower())
        if libelle:
            parts.append(libelle.title())

        return ' '.join(parts).strip() if parts else ''

    def action_view_imported_contacts(self):
        """
        Ouvre la vue Odoo pour voir les contacts importés.
        """
        self.ensure_one()
        return {
            'name': 'Contacts Importés',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'kanban,list,form',
            'domain': [('is_company', '=', True)],
            'context': {'search_default_customer': 1},
        }
