# -*- coding: utf-8 -*-
"""
Script de test pour vérifier la redirection après paiement

Exécutez ce script dans le shell Odoo:
$ odoo-bin shell -c odoo.conf -d votre_base

Puis dans le shell Python:
>>> exec(open('/home/user/odoo/addons/website_onedesk/tests/test_invitation_redirect.py').read())
"""

# Email de test - CHANGEZ CETTE VALEUR
TEST_EMAIL = 'test-nouveau-user@example.com'

print("=" * 80)
print("🔍 TEST DE REDIRECTION APRÈS PAIEMENT")
print("=" * 80)

# 1. Vérifier si l'utilisateur existe déjà
print(f"\n1️⃣ Vérification de l'utilisateur: {TEST_EMAIL}")
existing_user = env['res.users'].sudo().search([('login', '=', TEST_EMAIL)], limit=1)
if existing_user:
    print(f"   ❌ PROBLÈME: L'utilisateur existe déjà (ID: {existing_user.id})")
    print(f"   → Le système NE créera PAS d'invitation")
    print(f"   → Vous serez redirigé vers /onedesk/payment/success")
    print(f"\n   💡 SOLUTION: Utilisez un nouvel email OU supprimez cet utilisateur:")
    print(f"      >>> env['res.users'].sudo().browse({existing_user.id}).unlink()")
else:
    print(f"   ✅ OK: Aucun utilisateur trouvé avec cet email")

# 2. Chercher une company de test
print(f"\n2️⃣ Recherche d'une company de test...")
company = env['res.company'].sudo().search([('name', 'ilike', 'test')], limit=1)
if not company:
    company = env['res.company'].sudo().search([], limit=1)
print(f"   ✅ Company trouvée: {company.name} (ID: {company.id})")

# 3. Chercher ou créer une souscription de test
print(f"\n3️⃣ Recherche d'une souscription de test...")
subscription = env['onedesk.subscription'].sudo().search([
    ('company_id', '=', company.id),
], limit=1)

if not subscription:
    print(f"   ℹ️ Aucune souscription trouvée. Création d'une souscription de test...")
    # Créer un contact de test
    contact = env['res.partner'].sudo().create({
        'name': 'Test User',
        'email': TEST_EMAIL,
    })
    subscription = env['onedesk.subscription'].sudo().create({
        'company_id': company.id,
        'billing_contact_id': contact.id,
        'state': 'draft',
        'subscription_id': 'TEST-001',
    })
    print(f"   ✅ Souscription créée: {subscription.subscription_id} (ID: {subscription.id})")
else:
    print(f"   ✅ Souscription trouvée: {subscription.subscription_id} (ID: {subscription.id})")
    # Mettre à jour l'email du contact
    subscription.billing_contact_id.email = TEST_EMAIL

# 4. Vérifier si un client existe
print(f"\n4️⃣ Vérification du client OneDesk...")
client = env['onedesk.client'].sudo().search([
    ('company_id', '=', company.id)
], limit=1)
if client:
    print(f"   ✅ Client trouvé: ID={client.id}")
else:
    print(f"   ⚠️ Aucun client trouvé (il sera créé automatiquement)")

# 5. Simuler l'activation après paiement
print(f"\n5️⃣ Simulation de l'activation après paiement...")
print(f"   📧 Email du contact: {subscription.billing_contact_id.email}")

# Créer le client s'il n'existe pas
if not client:
    client = env['onedesk.client'].sudo().create({
        'company_id': company.id,
        'state': 'active',
    })
    print(f"   ✅ Client créé: ID={client.id}")

# Vérifier si l'utilisateur existe
existing_user = env['res.users'].sudo().search([('login', '=', TEST_EMAIL)], limit=1)
if existing_user:
    print(f"   ❌ Utilisateur existe déjà → PAS d'invitation")
else:
    # Créer l'invitation
    invitation = env['onedesk.client.invitation'].sudo().create({
        'client_id': client.id,
        'email': TEST_EMAIL,
        'role': 'owner',
        'state': 'pending',
        'expires_date': fields.Datetime.now() + timedelta(days=7),
    })
    print(f"   ✅ Invitation créée: ID={invitation.id}, token={invitation.invitation_token}")

# 6. Tester la recherche de l'invitation
print(f"\n6️⃣ Test de la recherche d'invitation...")
invitation = env['onedesk.client.invitation'].sudo().search([
    ('email', '=', TEST_EMAIL),
    ('state', '=', 'pending'),
], limit=1, order='id desc')

if invitation:
    print(f"   ✅ Invitation trouvée!")
    print(f"   → ID: {invitation.id}")
    print(f"   → Token: {invitation.invitation_token}")
    print(f"   → URL: /onedesk/invite/accept/{invitation.invitation_token}")
    print(f"\n   🎉 REDIRECTION ATTENDUE: /onedesk/invite/accept/{invitation.invitation_token}")
else:
    print(f"   ❌ AUCUNE invitation trouvée")
    print(f"   → REDIRECTION ATTENDUE: /onedesk/payment/success")
    print(f"\n   💡 Raison possible:")
    print(f"      - L'utilisateur existe déjà avec cet email")
    print(f"      - L'invitation n'a pas pu être créée (voir les logs)")

print("\n" + "=" * 80)
print("🏁 TEST TERMINÉ")
print("=" * 80)
