from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json
import logging
import time
import psycopg2

_logger = logging.getLogger(__name__)


class OneDeskWebsite(http.Controller):

    # ==================== TEST ROUTE ====================

    @http.route('/onedesk/test', type='http', auth='public')
    def test_route(self, **kw):
        """Route de test simple"""
        return "✅ OneDesk Website module est actif!"

    @http.route('/onedesk/booking-test', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def test_booking(self, **kw):
        """Route de test pour JSON"""
        _logger.info('Test booking route called!')
        return {
            'status': 'success',
            'message': '✅ Test - La route /onedesk/booking fonctionne!'
        }

    # ==================== PAGES PUBLIQUES ====================

    @http.route('/onedesk/properties', type='http', auth='public', website=True)
    def properties_list(self, **kw):
        """Page de listing de toutes les propriétés"""
        properties = request.env['onedesk.property'].search([])

        # Aussi récupère les unités "orphelines" (sans propriété) qui viennent des intégrations
        orphaned_units = request.env['onedesk.unit'].search([
            ('property_id', '=', False),
            ('external_listing_id', '!=', False)  # Seulement les importées
        ])

        return request.render('website_onedesk.properties_list', {
            'properties': properties,
            'orphaned_units': orphaned_units,
            'page_title': 'Nos propriétés',
        })

    @http.route('/onedesk/property/<model("onedesk.property"):property_id>', type='http', auth='public', website=True)
    def property_detail(self, property_id, **kw):
        """Page de détail d'une propriété"""
        units = property_id.unit_ids

        # Calcul des stats
        total_revenue = sum(units.mapped('revenue_this_month'))
        avg_occupancy = sum(units.mapped('occupancy_percentage')) / len(units) if units else 0

        return request.render('website_onedesk.property_detail', {
            'property': property_id,
            'units': units,
            'total_revenue': total_revenue,
            'avg_occupancy': avg_occupancy,
        })

    @http.route('/onedesk/unit/<model("onedesk.unit"):unit_id>', type='http', auth='public', website=True)
    def unit_detail(self, unit_id, **kw):
        """Page de détail d'une unité (chambre/appartement)"""
        # Récupère les réservations confirmées pour afficher le calendrier
        reservations = request.env['onedesk.reservation'].search([
            ('unit_id', '=', unit_id.id),
            ('status', '!=', 'cancelled'),
        ])

        return request.render('website_onedesk.unit_detail', {
            'unit': unit_id,
            'property': unit_id.property_id,
            'reservations': reservations,
        })

    # ==================== AJAX / FORMULAIRES ====================

    @http.route('/onedesk/booking', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def create_booking_request(self, **kw):
        """Crée une demande de réservation (lead/contact)"""
        _logger.info('===== START create_booking_request =====')
        _logger.info(f'Request method: {request.httprequest.method}')
        _logger.info(f'Has jsonrequest: {hasattr(request, "jsonrequest")}')
        _logger.info(f'jsonrequest value: {request.jsonrequest if hasattr(request, "jsonrequest") else "N/A"}')
        _logger.info(f'Raw data: {request.httprequest.data}')

        try:
            # Extrait les données du JSON body de manière robuste
            data = {}
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                _logger.info('Using request.jsonrequest')
                data = request.jsonrequest
            else:
                # Fallback: parse le JSON manuellement du body
                _logger.info('Using manual JSON parsing')
                if request.httprequest.data:
                    try:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                        _logger.info(f'Manual parse success: {data}')
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        _logger.error(f"Erreur parsing JSON: {e}")
                        data = {}

            _logger.info(f'Data extracted: {data}')

            # Vérifier si l'utilisateur est connecté
            if request.env.user._is_public():
                response = {
                    'status': 'error',
                    'message': '🔒 Vous devez créer un compte ou vous connecter pour effectuer une réservation.',
                    'action': 'login_required',
                    'login_url': '/web/login',
                    'signup_url': '/web/signup',
                }
                _logger.info(f'User is public, returning login required: {response}')
                return http.Response(json.dumps(response), content_type='application/json')

            # Valide les données requises
            required_fields = ['name', 'email', 'unit_id', 'start_date', 'end_date']
            for field in required_fields:
                if not data.get(field):
                    response = {
                        'status': 'error',
                        'message': f'Le champ "{field}" est requis.',
                    }
                    _logger.info(f'Returning response: {response}')
                    return http.Response(json.dumps(response), content_type='application/json')

            # IMPORTANT: Vérifie la disponibilité AVANT de créer la réservation
            unit_id = int(data.get('unit_id'))
            unit = request.env['onedesk.unit'].browse(unit_id)

            if not unit.exists():
                response = {
                    'status': 'error',
                    'message': 'Cette unité n\'existe pas.',
                }
                _logger.info(f'Returning response: {response}')
                return http.Response(json.dumps(response), content_type='application/json')

            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()

            # Convertir en datetime pour la comparaison
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            _logger.info(f'Booking request: unit={unit_id}, start={start_datetime}, end={end_datetime}')

            # Cherche les réservations qui se chevauchent
            conflicting = request.env['onedesk.reservation'].sudo().search([
                ('unit_id', '=', unit_id),
                ('status', '!=', 'cancelled'),
                ('start_date', '<', end_datetime),
                ('end_date', '>', start_datetime),
            ])

            _logger.info(f'Conflicting reservations found: {len(conflicting)}')

            if conflicting:
                # Formate le message d'erreur avec les périodes occupées
                conflict_dates = []
                for res in conflicting:
                    start_str = res.start_date.strftime('%d/%m/%Y')
                    end_str = res.end_date.strftime('%d/%m/%Y')
                    conflict_dates.append(f"{start_str} au {end_str}")

                error_msg = (
                    f"{unit.name}: ❌ Cette unité n'est pas disponible pour la période sélectionnée.\n\n"
                    f"Périodes occupées:\n"
                    + "\n".join(f"  • {date}" for date in conflict_dates)
                    + f"\n\nVeuillez choisir une autre période."
                )
                _logger.warning(f'Période indisponible pour unité {unit.name}')
                response = {
                    'status': 'error',
                    'message': error_msg,
                }
                _logger.info(f'Returning conflict response: {response}')
                return http.Response(json.dumps(response), content_type='application/json')

            # Crée un partner si nécessaire
            partner = request.env['res.partner'].sudo().search([
                ('email', '=', data.get('email'))
            ], limit=1)

            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': data.get('name'),
                    'email': data.get('email'),
                    'phone': data.get('phone', ''),
                })
                _logger.info(f'Created partner: {partner.id}')

            # Crée la réservation en brouillon
            _logger.info(f'Creating reservation with start={start_datetime.isoformat()}, end={end_datetime.isoformat()}')

            reservation = request.env['onedesk.reservation'].sudo().create({
                'unit_id': unit_id,
                'partner_id': partner.id,
                'start_date': start_date.isoformat(),  # Envoyer juste la date, pas la datetime
                'end_date': end_date.isoformat(),      # Envoyer juste la date, pas la datetime
                'guest_notes': data.get('message', ''),
                'status': 'draft',  # En attente de confirmation
            })

            _logger.info(f'Reservation created successfully: {reservation.name}')

            # Envoie l'email de confirmation
            try:
                reservation.send_confirmation_email()
                _logger.info(f'Confirmation email sent for reservation {reservation.name}')
            except Exception as e:
                _logger.error(f'Error sending confirmation email: {str(e)}')

            response = {
                'status': 'success',
                'message': f'✅ Réservation confirmée!\n\nUn email de confirmation a été envoyé à {partner.email}.\n\nNuméro de réservation: {reservation.name}',
                'reservation_id': reservation.id,
            }
            _logger.info(f'Returning success response: {response}')
            return http.Response(json.dumps(response), content_type='application/json')

        except ValueError as e:
            error_str = str(e)
            _logger.error(f'ValueError during booking: {error_str}')
            response = {
                'status': 'error',
                'message': f'Format de date invalide. Veuillez utiliser le format YYYY-MM-DD.',
            }
            return http.Response(json.dumps(response), content_type='application/json')

        except ValidationError as e:
            # Erreur de validation (ex: chevauchement de réservation)
            error_msg = str(e).replace('<class \'odoo.exceptions.ValidationError\'>', '').strip()
            _logger.error(f'ValidationError during booking: {error_msg}')
            response = {
                'status': 'error',
                'message': error_msg or 'Cette réservation n\'est pas possible. Veuillez vérifier les dates.',
            }
            return http.Response(json.dumps(response), content_type='application/json')

        except Exception as e:
            error_msg = str(e) if str(e) else 'Une erreur inconnue s\'est produite'
            _logger.exception(f'Unexpected error during booking: {error_msg}')
            _logger.error(f'Exception type: {type(e).__name__}')
            response = {
                'status': 'error',
                'message': error_msg,
            }
            _logger.error(f'Returning error response: {response}')
            return http.Response(json.dumps(response), content_type='application/json')

    @http.route('/onedesk/unit/<model("onedesk.unit"):unit_id>/availability', type='jsonrpc', auth='public', website=True, methods=['POST'])
    def check_availability(self, unit_id, **kw):
        """Vérifie la disponibilité d'une unité pour une période"""
        try:
            # Extrait les données du JSON body de manière robuste
            data = {}
            if hasattr(request, 'jsonrequest') and request.jsonrequest:
                data = request.jsonrequest
            else:
                # Fallback: parse le JSON manuellement du body
                if request.httprequest.data:
                    try:
                        data = json.loads(request.httprequest.data.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        _logger.warning(f"Erreur parsing JSON: {e}")
                        data = {}

            start_date = data.get('start_date')
            end_date = data.get('end_date')

            if not start_date or not end_date:
                return {
                    'available': False,
                    'message': 'Les dates de début et fin sont requises.',
                }

            # Convertir les dates en datetime objects (avec min/max time pour les comparaisons)
            start_dt = datetime.combine(
                datetime.strptime(start_date, '%Y-%m-%d').date(),
                datetime.min.time()
            )
            end_dt = datetime.combine(
                datetime.strptime(end_date, '%Y-%m-%d').date(),
                datetime.max.time()
            )

            # Cherche les réservations qui se chevauchent
            overlapping = request.env['onedesk.reservation'].search([
                ('unit_id', '=', unit_id.id),
                ('status', '!=', 'cancelled'),
                ('start_date', '<', end_dt),
                ('end_date', '>', start_dt),
            ])

            if overlapping:
                # Formate le message avec les périodes occupées
                conflict_dates = []
                for res in overlapping:
                    start_str = res.start_date.strftime('%d/%m/%Y')
                    end_str = res.end_date.strftime('%d/%m/%Y')
                    conflict_dates.append(f"{start_str} au {end_str}")

                error_msg = (
                    f"{unit_id.name}: ❌ Cette unité n'est pas disponible pour la période sélectionnée.\n\n"
                    f"Périodes occupées:\n"
                    + "\n".join(f"  • {date}" for date in conflict_dates)
                    + f"\n\nVeuillez choisir une autre période."
                )
                return {
                    'available': False,
                    'message': error_msg,
                }

            # Calcule le prix
            nights = (end_dt.date() - start_dt.date()).days
            avg_price = unit_id.get_price_for_dates(start_dt.date(), end_dt.date())
            total_price = avg_price * nights

            return {
                'available': True,
                'nights': nights,
                'price_per_night': avg_price,
                'total_price': total_price,
                'cleaning_fee': unit_id.cleaning_fee,
                'total_with_cleaning': total_price + unit_id.cleaning_fee,
            }

        except Exception as e:
            _logger.exception('Erreur lors de la vérification de disponibilité')
            return {
                'available': False,
                'message': f'Erreur: {str(e)}',
            }

    # ==================== SUBSCRIPTION / PRICING ====================

    @http.route('/onedesk/subscription', type='http', auth='public', website=True)
    def subscription_plans(self, **kw):
        """Page de plans d'abonnement"""
        plans = request.env['onedesk.subscription.plan'].search([
            ('active', '=', True)
        ], order='sequence')

        return request.render('website_onedesk.subscription_plans', {
            'plans': plans,
            'page_title': 'Plans d\'abonnement OneDesk',
        })

    @http.route('/onedesk/subscription/<model("onedesk.subscription.plan"):plan_id>', type='http', auth='public', website=True)
    def subscription_form(self, plan_id, **kw):
        """Formulaire de souscription pour un plan spécifique"""
        return request.render('website_onedesk.subscription_form', {
            'plan': plan_id,
            'page_title': f'S\'abonner au plan {plan_id.name}',
        })

    def _is_plan_free(self, plan):
        """Détermine si un plan est gratuit

        Un plan est gratuit si TOUS les prix sont à 0
        """
        return (
            plan.price_per_unit == 0 and
            plan.commission_percentage == 0 and
            plan.setup_fee == 0
        )

    def _get_payment_mode(self):
        """Récupère le mode de paiement (TEST ou PROD)

        Returns:
            str: 'test' ou 'prod'
        """
        mode = request.env['ir.config_parameter'].sudo().get_param(
            'onedesk.payment_mode',
            'test'  # Mode TEST par défaut pour ne pas casser les tests
        )
        return mode.lower()

    def _calculate_plan_total(self, plan, num_units):
        """
        Calcule le montant mensuel à payer pour un plan

        IMPORTANT: Facturation MENSUELLE uniquement (pas par unité)
        Le montant correspond au prix mensuel du plan configuré

        Args:
            plan: Le plan d'abonnement
            num_units: Nombre d'unités (IGNORÉ - juste pour information)

        Returns:
            float: Prix mensuel du plan
        """
        # CORRECTION: Retourner uniquement le prix mensuel configuré
        # PAS de multiplication par nombre d'unités

        if plan.billing_model == 'per_unit':
            # Prix mensuel par unité (configuration du plan)
            monthly_price = plan.price_per_unit
        elif plan.billing_model == 'commission':
            # Pour commission, pas de paiement initial fixe
            # La commission sera calculée sur les réservations
            monthly_price = 0.0
        else:
            monthly_price = 0.0

        _logger.info(f'💰 Prix mensuel calculé: {monthly_price}€ (num_units={num_units} ignoré)')

        return monthly_price

    @http.route('/onedesk/subscription/create', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def create_subscription(self, **kw):
        """
        Crée une souscription avec gestion du paiement

        NOUVEAU COMPORTEMENT:
        - Plans GRATUITS: activation immédiate + email de bienvenue
        - Plans PAYANTS: génération lien paiement + AUCUNE activation avant paiement
        - Mode TEST: simulation de paiement possible
        - Mode PROD: paiement réel obligatoire
        """
        try:
            # Récupère les données du formulaire
            plan_id = int(kw.get('plan_id'))
            company_name = kw.get('company_name', '').strip()
            contact_name = kw.get('contact_name', '').strip()
            email = kw.get('email', '').strip()
            phone = kw.get('phone', '').strip()
            num_units = int(kw.get('num_units', 0))
            terms_accepted = kw.get('terms_accepted') == 'on'

            # Valide les champs requis
            if not all([company_name, contact_name, email, num_units]):
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'message': 'Tous les champs marqués avec * sont requis.',
                    }),
                    content_type='application/json'
                )

            if not terms_accepted:
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'message': 'Veuillez accepter les conditions d\'utilisation.',
                    }),
                    content_type='application/json'
                )

            # Récupère le plan
            plan = request.env['onedesk.subscription.plan'].browse(plan_id)
            if not plan.exists():
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'message': 'Ce plan n\'existe pas.',
                    }),
                    content_type='application/json'
                )

            # Crée ou récupère la société client
            Company = request.env['res.company']
            company = Company.search([('name', '=', company_name)], limit=1)
            if not company:
                company = Company.sudo().create({
                    'name': company_name,
                    'is_onedesk_client': True,
                })

            # Crée ou récupère le contact
            Partner = request.env['res.partner']
            partner = Partner.search([('email', '=', email)], limit=1)
            if not partner:
                partner = Partner.sudo().create({
                    'name': contact_name,
                    'email': email,
                    'phone': phone if phone else False,
                    'company_id': company.id,
                })

            # ==================== NOUVEAU: Détection plan gratuit/payant ====================

            is_free_plan = self._is_plan_free(plan)
            payment_mode = self._get_payment_mode()

            _logger.info(f'📋 Plan {plan.name}: Gratuit={is_free_plan}, Mode paiement={payment_mode}')

            # Détermine l'état initial de la souscription
            if is_free_plan:
                initial_state = 'active'  # Plan gratuit = activation immédiate
                _logger.info('✅ Plan gratuit détecté - Activation immédiate')
            else:
                initial_state = 'pending_payment'  # Plan payant = en attente de paiement
                _logger.info('💳 Plan payant détecté - Paiement requis')

            # Crée la souscription
            subscription = request.env['onedesk.subscription'].sudo().create({
                'company_id': company.id,
                'plan_id': plan.id,
                'state': initial_state,
                'billing_contact_id': partner.id,
                'requested_units': num_units,
            })

            # Créer aussi le client OneDesk (avec retry pour gérer les erreurs de concurrence)
            client = request.env['onedesk.client'].sudo().search(
                [('company_id', '=', company.id)], limit=1
            )
            if not client:
                # État du client basé sur le type de plan
                client_state = 'active' if is_free_plan else 'pending_payment'

                # Retry jusqu'à 3 fois en cas d'erreur de concurrence PostgreSQL
                for attempt in range(3):
                    try:
                        client = request.env['onedesk.client'].sudo().create({
                            'company_id': company.id,
                            'owner_partner_id': partner.id,
                            'subscription_id': subscription.id,
                            'state': client_state,
                        })
                        _logger.info(f'✅ Created OneDesk client {client.id} (state={client_state})')
                        break  # Succès - sortir de la boucle
                    except psycopg2.errors.SerializationFailure as e:
                        if attempt < 2:  # Pas la dernière tentative
                            _logger.warning(f'⚠️ Erreur de concurrence (tentative {attempt + 1}/3), retry dans 0.1s...')
                            request.env.cr.rollback()  # Rollback de la transaction
                            time.sleep(0.1)  # Attendre un peu avant de réessayer
                        else:  # Dernière tentative échouée
                            _logger.error(f'❌ Échec création client après 3 tentatives: {e}')
                            raise  # Re-lever l'exception
            else:
                # Lier la subscription au client existant
                client.write({'subscription_id': subscription.id})

            _logger.info(f'✅ Subscription created: {subscription.subscription_id}')

            # Créer un audit log
            request.env['onedesk.audit.log'].sudo().create({
                'log_type': 'subscription_created',
                'severity': 'info',
                'company_id': company.id,
                'subscription_id': subscription.id,
                'description': f'Nouvelle souscription créée: {subscription.subscription_id} (Plan: {plan.name}, Type: {"Gratuit" if is_free_plan else "Payant"})',
                'actor_name': contact_name,
                'actor_email': email,
                'result': 'success',
            })

            # ==================== NOUVEAU: Logique différenciée gratuit/payant ====================

            if is_free_plan:
                # ✅ PLAN GRATUIT: Envoyer emails immédiatement
                _logger.info('📧 Envoi des emails pour plan gratuit')

                try:
                    template_client = request.env.ref('website_onedesk.email_subscription_confirmation')
                    template_client.send_mail(subscription.id, force_send=True, email_values={
                        'email_to': email,
                    })
                    _logger.info(f'✅ Confirmation email sent to {email}')
                except Exception as e:
                    _logger.warning(f'⚠️ Error sending client email: {e}')

                # NOUVEAU: Créer utilisateur et envoyer email d'activation pour plan gratuit
                try:
                    # Vérifier si l'utilisateur existe déjà
                    user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)

                    if not user:
                        # Créer l'utilisateur
                        user = request.env['res.users'].sudo().create({
                            'name': contact_name,
                            'login': email,
                            'email': email,
                            'company_id': company.id,
                            'company_ids': [(4, company.id)],
                        })
                        _logger.info(f'✅ Utilisateur créé: {user.login} (ID: {user.id})')

                    # Préparer le signup (génère le token d'activation)
                    user.partner_id.signup_prepare()

                    # Envoyer l'email d'activation
                    template_welcome = request.env.ref('onedesk_core.email_template_welcome')
                    template_welcome.sudo().send_mail(user.id, force_send=True)
                    _logger.info(f'✅ Email d\'activation envoyé à {email}')
                except Exception as e:
                    _logger.warning(f'⚠️ Erreur envoi email activation: {e}', exc_info=True)

                # Envoie l'email à l'admin
                try:
                    admin_email = request.env['ir.config_parameter'].sudo().get_param('onedesk.admin_email')
                    if admin_email:
                        template_admin = request.env.ref('website_onedesk.email_subscription_admin_notification')
                        template_admin.send_mail(subscription.id, force_send=True, email_values={
                            'email_to': admin_email,
                        })
                        _logger.info(f'✅ Admin notification sent to {admin_email}')
                except Exception as e:
                    _logger.warning(f'⚠️ Error sending admin email: {e}')

                response = {
                    'status': 'success',
                    'message': f'✅ Souscription créée avec succès!\n\nUn email de confirmation a été envoyé à {email}.\n\nNuméro de souscription: {subscription.subscription_id}',
                    'subscription_id': subscription.id,
                    'is_free': True,
                }

            else:
                # 💳 PLAN PAYANT: Générer lien de paiement
                total_amount = self._calculate_plan_total(plan, num_units)

                _logger.info(f'💰 Montant mensuel à payer: {total_amount}€')

                # Construire l'URL de paiement
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

                if payment_mode == 'test':
                    # Mode TEST: Redirection vers page de simulation
                    payment_url = f"{base_url}/onedesk/payment/test/{subscription.id}?amount={total_amount}"
                    _logger.info('=' * 80)
                    _logger.info('🧪 MODE TEST ACTIVÉ - SIMULATION DE PAIEMENT')
                    _logger.info(f'🧪 URL de paiement TEST: {payment_url}')
                    _logger.info(f'🧪 Montant: {total_amount}€')
                    _logger.info(f'🧪 Souscription ID: {subscription.id}')
                    _logger.info('🧪 Le paiement sera SIMULÉ (pas de transaction réelle)')
                    _logger.info('=' * 80)
                else:
                    # Mode PROD: Générer un vrai lien de paiement via module payment
                    payment_url = f"{base_url}/onedesk/payment/{subscription.id}?amount={total_amount}"
                    _logger.info('=' * 80)
                    _logger.info('💳 MODE PRODUCTION - PAIEMENT RÉEL')
                    _logger.info(f'💳 URL de paiement PROD: {payment_url}')
                    _logger.info(f'💳 Montant: {total_amount}€')
                    _logger.info(f'💳 Souscription ID: {subscription.id}')
                    _logger.info('💳 Le paiement sera RÉEL (transaction bancaire)')
                    _logger.info('=' * 80)

                # Stocker le montant et l'URL dans la souscription
                subscription.sudo().write({
                    'payment_amount': total_amount,
                    'payment_url': payment_url,
                })

                # Envoyer notification admin SEULEMENT
                try:
                    admin_email = request.env['ir.config_parameter'].sudo().get_param('onedesk.admin_email')
                    if admin_email:
                        template_admin = request.env.ref('website_onedesk.email_subscription_admin_notification')
                        template_admin.send_mail(subscription.id, force_send=True, email_values={
                            'email_to': admin_email,
                        })
                        _logger.info(f'✅ Admin notification sent (payment pending)')
                except Exception as e:
                    _logger.warning(f'⚠️ Error sending admin email: {e}')

                # Message différent selon le mode
                if payment_mode == 'test':
                    message = f'🧪 MODE TEST - Souscription créée\n\nVous allez être redirigé vers la page de SIMULATION de paiement.\n\nMontant mensuel: {total_amount}€\n\n⚠️ Aucune transaction réelle ne sera effectuée.'
                else:
                    message = f'💳 Souscription créée - Paiement requis\n\nVous allez être redirigé vers la page de paiement sécurisé.\n\nMontant mensuel: {total_amount}€'

                response = {
                    'status': 'success',
                    'message': message,
                    'subscription_id': subscription.id,
                    'is_free': False,
                    'requires_payment': True,
                    'payment_url': payment_url,
                    'amount': total_amount,
                    'payment_mode': payment_mode,  # NOUVEAU: Indiquer le mode
                }

            _logger.info(f'Returning response: {response}')
            return http.Response(json.dumps(response), content_type='application/json')

        except ValueError as e:
            _logger.error(f'ValueError: {e}')
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'message': 'Données invalides. Veuillez vérifier votre saisie.',
                }),
                content_type='application/json'
            )

        except Exception as e:
            error_msg = str(e)
            _logger.exception(f'Unexpected error creating subscription: {error_msg}')
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'message': f'Une erreur s\'est produite: {error_msg}',
                }),
                content_type='application/json'
            )

    # ==================== PAYMENT ROUTES ====================

    @http.route('/onedesk/payment/test/<int:subscription_id>', type='http', auth='public', website=True)
    def payment_test_page(self, subscription_id, **kw):
        """
        Page de simulation de paiement en mode TEST

        Permet de tester tout le workflow de paiement sans payer réellement
        """
        subscription = request.env['onedesk.subscription'].sudo().browse(subscription_id)

        if not subscription.exists():
            return request.render('website.404')

        amount = float(kw.get('amount', subscription.payment_amount or 0))

        return request.render('website_onedesk.payment_test_page', {
            'subscription': subscription,
            'plan': subscription.plan_id,
            'amount': amount,
            'page_title': 'Simulation de Paiement (MODE TEST)',
        })

    @http.route('/onedesk/payment/test/simulate', type='http', auth='public', methods=['POST'], csrf=False)
    def payment_test_simulate(self, **kw):
        """
        Simule un paiement validé en mode TEST

        Permet de tester l'activation du compte après paiement
        """
        try:
            subscription_id = int(kw.get('subscription_id'))
            action = kw.get('action')  # 'success' ou 'fail'

            subscription = request.env['onedesk.subscription'].sudo().browse(subscription_id)

            if not subscription.exists():
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'message': 'Souscription non trouvée',
                    }),
                    content_type='application/json'
                )

            if action == 'success':
                # Simule un paiement réussi
                self._activate_subscription_after_payment(subscription)

                return http.Response(
                    json.dumps({
                        'status': 'success',
                        'message': '✅ Paiement simulé avec succès!',
                        'redirect_url': '/onedesk/payment/success',
                    }),
                    content_type='application/json'
                )
            else:
                # Simule un échec de paiement
                return http.Response(
                    json.dumps({
                        'status': 'error',
                        'message': '❌ Paiement simulé échoué',
                        'redirect_url': '/onedesk/payment/error',
                    }),
                    content_type='application/json'
                )

        except Exception as e:
            _logger.exception('Error in payment simulation')
            return http.Response(
                json.dumps({
                    'status': 'error',
                    'message': str(e),
                }),
                content_type='application/json'
            )

    @http.route('/onedesk/payment/<int:subscription_id>', type='http', auth='public', website=True)
    def payment_page(self, subscription_id, **kw):
        """
        Page de paiement réel en mode PRODUCTION

        Intègre avec les payment providers Odoo (Stripe, PayPal, etc.)
        """
        subscription = request.env['onedesk.subscription'].sudo().browse(subscription_id)

        if not subscription.exists():
            return request.render('website.404')

        amount = float(kw.get('amount', subscription.payment_amount or 0))

        # IMPORTANT: Intégration avec Odoo Payment System
        # 1. Chercher les payment providers disponibles (Stripe, PayPal, etc.)
        payment_providers = request.env['payment.provider'].sudo().search([
            ('state', '!=', 'disabled'),
            ('company_id', 'in', [subscription.company_id.id, False]),
        ])

        if not payment_providers:
            _logger.warning('⚠️ No payment providers configured for PROD mode')
            return request.render('website_onedesk.payment_error', {
                'error_message': 'Aucun moyen de paiement configuré. Veuillez contacter le support.',
                'page_title': 'Erreur de paiement',
            })

        # 2. Récupérer les méthodes de paiement disponibles
        payment_methods = request.env['payment.method'].sudo().search([
            ('active', '=', True),
        ])

        # 3. Récupérer la devise
        currency = subscription.company_id.currency_id or request.env.company.currency_id

        # 4. Construire le contexte de paiement pour le template
        partner = subscription.billing_contact_id or request.env.user.partner_id

        _logger.info('=' * 80)
        _logger.info('💳 MODE PRODUCTION - PAIEMENT RÉEL')
        _logger.info(f'💳 Subscription: {subscription.subscription_id}')
        _logger.info(f'💳 Amount: {amount}€')
        _logger.info(f'💳 Payment providers available: {len(payment_providers)}')
        _logger.info(f'💳 Payment methods available: {len(payment_methods)}')
        _logger.info('💳 Le paiement sera RÉEL (transaction bancaire)')
        _logger.info('=' * 80)

        return request.render('website_onedesk.payment_page_prod', {
            'subscription': subscription,
            'plan': subscription.plan_id,
            'amount': amount,
            'currency': currency,
            'partner_id': partner.id,
            'providers_sudo': payment_providers,
            'payment_methods_sudo': payment_methods,
            'tokens_sudo': request.env['payment.token'].sudo().search([
                ('partner_id', '=', partner.id),
            ]),
            'transaction_route': '/payment/transaction',
            'landing_route': f'/onedesk/payment/callback?subscription_id={subscription_id}',
            'reference_prefix': f'ONEDESK-{subscription.subscription_id}',
            'page_title': 'Paiement',
        })

    @http.route('/onedesk/payment/callback', type='http', auth='public', methods=['GET', 'POST'], csrf=False, website=True)
    def payment_callback(self, **kw):
        """
        Callback appelé par Odoo payment system après paiement

        Cette route est appelée après que le payment provider (Stripe, PayPal, etc.)
        ait traité le paiement. Odoo redirige ici après /payment/status.

        Valide le paiement et active la souscription
        """
        try:
            subscription_id = int(kw.get('subscription_id'))
            subscription = request.env['onedesk.subscription'].sudo().browse(subscription_id)

            if not subscription.exists():
                _logger.error(f'Subscription {subscription_id} not found in payment callback')
                return request.redirect('/onedesk/payment/error?error=subscription_not_found')

            _logger.info(f'💳 Payment callback received for subscription {subscription.subscription_id}')

            # Chercher la dernière transaction de paiement pour cette souscription
            # La référence commence par 'ONEDESK-{subscription_id}'
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', 'like', f'ONEDESK-{subscription.subscription_id}%'),
            ], order='id desc', limit=1)

            if not tx:
                _logger.error(f'No payment transaction found for subscription {subscription.subscription_id}')
                return request.redirect('/onedesk/payment/error?error=transaction_not_found')

            _logger.info(f'💳 Transaction found: {tx.reference}, state: {tx.state}')

            # Vérifier l'état de la transaction
            if tx.state == 'done':
                # Paiement réussi - Activer la souscription
                _logger.info(f'✅ Payment successful for {subscription.subscription_id}')
                self._activate_subscription_after_payment(subscription)

                # Rediriger vers la page d'activation du compte (invitation)
                redirect_url = self._get_post_payment_redirect_url(subscription)
                return request.redirect(redirect_url)

            elif tx.state == 'authorized':
                # Paiement autorisé mais pas encore capturé
                _logger.info(f'⏳ Payment authorized for {subscription.subscription_id}')
                # Pour l'instant, on active aussi (peut être modifié selon besoin)
                self._activate_subscription_after_payment(subscription)

                # Rediriger vers la page d'activation du compte (invitation)
                redirect_url = self._get_post_payment_redirect_url(subscription)
                return request.redirect(redirect_url)

            elif tx.state in ['pending', 'draft']:
                # Paiement en attente
                _logger.info(f'⏳ Payment pending for {subscription.subscription_id}')
                return request.redirect('/onedesk/payment/pending')

            elif tx.state in ['cancel', 'error']:
                # Paiement échoué
                _logger.warning(f'❌ Payment failed for {subscription.subscription_id}: {tx.state_message}')

                # Log l'échec
                request.env['onedesk.audit.log'].sudo().create({
                    'log_type': 'payment_failed',
                    'severity': 'warning',
                    'company_id': subscription.company_id.id,
                    'subscription_id': subscription.id,
                    'description': f'Échec de paiement pour {subscription.subscription_id}: {tx.state_message}',
                    'result': 'failed',
                })

                return request.redirect(f'/onedesk/payment/error?error={tx.state_message or "payment_failed"}')

            else:
                # État inconnu
                _logger.warning(f'⚠️ Unknown payment state for {subscription.subscription_id}: {tx.state}')
                return request.redirect('/onedesk/payment/pending')

        except Exception as e:
            _logger.exception('Error in payment callback')
            return request.redirect(f'/onedesk/payment/error?error={str(e)}')

    def _activate_subscription_after_payment(self, subscription):
        """
        Active une souscription après validation du paiement

        Cette méthode:
        1. Change l'état de la souscription à 'active'
        2. Active le client OneDesk
        3. Envoie l'email de bienvenue au client
        4. Crée un audit log
        """
        _logger.info(f'✅ Activating subscription {subscription.subscription_id} after payment')

        # 1. Activer la souscription
        subscription.write({
            'state': 'active',
            'start_date': fields.Date.today(),
        })

        # 2. Activer le client OneDesk (ou le créer s'il n'existe pas)
        client = request.env['onedesk.client'].sudo().search([
            ('company_id', '=', subscription.company_id.id)
        ], limit=1)

        if not client:
            # Créer le client s'il n'existe pas encore
            client = request.env['onedesk.client'].sudo().create({
                'company_id': subscription.company_id.id,
                'state': 'active',
            })
            _logger.info(f'✅ Client {client.id} créé pour la company {subscription.company_id.id}')
        else:
            client.write({'state': 'active'})
            _logger.info(f'✅ Client {client.id} activated')

        # 3. Envoyer l'email de confirmation de souscription
        try:
            template = request.env.ref('website_onedesk.email_subscription_confirmation')
            template.send_mail(subscription.id, force_send=True, email_values={
                'email_to': subscription.billing_contact_id.email,
            })
            _logger.info(f'✅ Confirmation email sent to {subscription.billing_contact_id.email}')
        except Exception as e:
            _logger.warning(f'⚠️ Error sending confirmation email: {e}')

        # 3.5. NOUVEAU: Créer invitation après paiement (les emails seront envoyés après acceptation)
        _logger.info(f'📧 Vérification de la création d\'invitation pour {subscription.billing_contact_id.email}')
        try:
            contact_email = subscription.billing_contact_id.email

            # Vérifier si l'utilisateur existe déjà
            existing_user = request.env['res.users'].sudo().search([('login', '=', contact_email)], limit=1)

            if existing_user:
                _logger.info(f'ℹ️ Utilisateur existe déjà: {contact_email}, pas d\'invitation créée')
            else:
                _logger.info(f'🆕 Création d\'invitation pour {contact_email} avec client_id={client.id}')
                # Créer une invitation pour que l'utilisateur définisse son mot de passe
                invitation = request.env['onedesk.client.invitation'].sudo().create({
                    'client_id': client.id,
                    'email': contact_email,
                    'role': 'owner',  # Propriétaire = property_manager group
                    'state': 'pending',
                    'expires_date': fields.Datetime.now() + timedelta(days=7),
                })
                _logger.info(f'✅ Invitation créée avec succès: ID={invitation.id}, token={invitation.invitation_token}')

                # Note: L'invitation sera récupérée via l'email dans payment_callback
        except Exception as e:
            _logger.error(f'❌ Erreur création invitation après paiement: {e}', exc_info=True)

        # 4. Créer un audit log
        request.env['onedesk.audit.log'].sudo().create({
            'log_type': 'payment_validated',
            'severity': 'info',
            'company_id': subscription.company_id.id,
            'subscription_id': subscription.id,
            'description': f'Paiement validé et souscription activée: {subscription.subscription_id}',
            'result': 'success',
        })

        _logger.info(f'✅ Subscription {subscription.subscription_id} fully activated')

    def _get_post_payment_redirect_url(self, subscription):
        """
        Obtenir l'URL de redirection après paiement réussi

        - Si une invitation existe pour cet email → Redirige vers la page d'acceptation
        - Sinon (utilisateur existe déjà) → Redirige vers la page de succès
        """
        contact_email = subscription.billing_contact_id.email
        _logger.info(f'🔍 Recherche d\'invitation pour {contact_email}')

        # Chercher une invitation en attente pour cet email
        invitation = request.env['onedesk.client.invitation'].sudo().search([
            ('email', '=', contact_email),
            ('state', '=', 'pending'),
        ], limit=1, order='id desc')

        if invitation:
            redirect_url = f'/onedesk/invite/accept/{invitation.invitation_token}'
            _logger.info(f'✅ Invitation trouvée (ID: {invitation.id}), redirection vers: {redirect_url}')
            return redirect_url
        else:
            _logger.warning(f'⚠️ Aucune invitation trouvée pour {contact_email}, redirection vers page de succès')
            return '/onedesk/payment/success'

    @http.route('/onedesk/payment/success', type='http', auth='public', website=True)
    def payment_success(self, **kw):
        """Page de confirmation de paiement réussi"""
        return request.render('website_onedesk.payment_success', {
            'page_title': 'Paiement Réussi',
        })

    @http.route('/onedesk/payment/error', type='http', auth='public', website=True)
    def payment_error(self, **kw):
        """Page d'erreur de paiement"""
        return request.render('website_onedesk.payment_error', {
            'page_title': 'Erreur de Paiement',
        })

    @http.route('/onedesk/payment/pending', type='http', auth='public', website=True)
    def payment_pending(self, **kw):
        """Page de paiement en attente"""
        return request.render('website_onedesk.payment_pending', {
            'page_title': 'Paiement en Attente',
        })