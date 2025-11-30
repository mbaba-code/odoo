#!/usr/bin/env python3
"""
Script pour vérifier et corriger la configuration email + template
À exécuter via: python3 odoo-bin shell -c odoo.conf -d onedesk
Puis: exec(open('fix_template_et_config.py').read())
"""

def fix_template_et_config():
    """Vérifie et corrige la configuration email et le template"""

    print("\n" + "="*80)
    print("🔧 FIX - CONFIGURATION EMAIL + TEMPLATE")
    print("="*80 + "\n")

    # ========== 1. VÉRIFIER/FIXER web.base.url ==========
    print("1️⃣ Vérification du paramètre web.base.url...")

    IrConfigParameter = env['ir.config_parameter'].sudo()
    base_url = IrConfigParameter.get_param('web.base.url')

    if not base_url:
        print("   ⚠️  web.base.url n'est PAS configuré!")
        print("   🔧 Configuration par défaut...")

        # Essayer de détecter l'URL depuis la requête ou utiliser localhost
        default_url = 'http://localhost:8069'
        IrConfigParameter.set_param('web.base.url', default_url)
        print(f"   ✅ web.base.url configuré: {default_url}")
        print(f"   ⚠️  IMPORTANT: Changez ceci en production vers votre vraie URL!")
    else:
        print(f"   ✅ web.base.url est configuré: {base_url}")

    # ========== 2. VÉRIFIER LE TEMPLATE ==========
    print("\n2️⃣ Vérification du template signature...")

    try:
        template = env.ref('onedesk_core.email_template_signature_request')
        print(f"   ✅ Template trouvé: {template.name}")

        # Vérifier les champs critiques
        issues = []

        if not template.email_from:
            issues.append("email_from est vide")
        elif 'kokouignace.baba@prefecto-etranger-aide.com' not in template.email_from:
            issues.append(f"email_from devrait être l'email vérifié Brevo: {template.email_from}")

        if not template.email_to:
            issues.append("email_to est vide")

        if not template.body_html:
            issues.append("body_html est vide")

        if issues:
            print(f"   ⚠️  Problèmes détectés:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"   ✅ Template semble correct")

        # Afficher la config actuelle
        print(f"\n   📋 Configuration actuelle:")
        print(f"      - email_from: {template.email_from}")
        print(f"      - email_to: {template.email_to}")
        print(f"      - subject: {template.subject}")
        print(f"      - body_html: {len(template.body_html)} caractères")

    except Exception as e:
        print(f"   ❌ ERREUR: Template non trouvé! {e}")
        return

    # ========== 3. TEST DE RENDERING DU TEMPLATE ==========
    print("\n3️⃣ Test de rendering du template...")

    Signature = env['onedesk.document.signature']
    test_sig = Signature.sudo().search([], order='create_date desc', limit=1)

    if not test_sig:
        print("   ⚠️  Aucune signature existante pour tester le rendering")
        print("   ⏭️  On passe cette étape")
    else:
        print(f"   🔄 Test avec signature #{test_sig.id}...")

        try:
            # Test rendering de chaque champ
            subject_rendered = template._render_field('subject', [test_sig.id])[test_sig.id]
            print(f"   ✅ Subject rendered: {subject_rendered}")

            email_to_rendered = template._render_field('email_to', [test_sig.id])[test_sig.id]
            print(f"   ✅ Email_to rendered: {email_to_rendered}")

            body_rendered = template._render_field('body_html', [test_sig.id])[test_sig.id]
            print(f"   ✅ Body_html rendered: {len(body_rendered)} caractères")

            # Vérifier que le body contient des éléments essentiels
            if not body_rendered or len(body_rendered) < 100:
                print(f"   ⚠️  WARNING: Body semble trop court!")

            if 'http' in body_rendered:
                print(f"   ✅ Body contient des liens HTTP (URLs générées)")
            else:
                print(f"   ⚠️  WARNING: Aucun lien HTTP trouvé dans le body")

        except Exception as e:
            print(f"   ❌ ERREUR lors du rendering: {e}")
            print(f"\n   🔍 Détails de l'erreur:")
            import traceback
            traceback.print_exc()
            print(f"\n   💡 Cela indique que le template a un problème de syntaxe ou de données")

    # ========== 4. VÉRIFIER SERVEUR SMTP ==========
    print("\n4️⃣ Vérification serveur SMTP...")

    MailServer = env['ir.mail_server']
    servers = MailServer.sudo().search([])

    if not servers:
        print("   ❌ AUCUN serveur SMTP configuré!")
        print("\n   🔧 Configuration automatique de Brevo...")

        # Créer la configuration Brevo
        # NOTE: Le mot de passe doit être configuré manuellement pour des raisons de sécurité
        brevo_server = MailServer.sudo().create({
            'name': 'Brevo SMTP',
            'smtp_host': 'smtp-relay.brevo.com',
            'smtp_port': 587,
            'smtp_encryption': 'starttls',
            'smtp_user': '9c50c1001@smtp-brevo.com',
            'smtp_pass': '',  # À REMPLIR MANUELLEMENT!
            'sequence': 10,
        })

        print(f"   ✅ Serveur SMTP Brevo créé (ID: {brevo_server.id})")
        print(f"   ⚠️  IMPORTANT: Vous devez configurer le mot de passe SMTP manuellement!")
        print(f"   → Paramètres > Technique > Email > Serveurs emails sortants")
        print(f"   → Modifier 'Brevo SMTP' et ajouter le mot de passe")
    else:
        for server in servers:
            print(f"   ✅ Serveur: {server.name}")
            print(f"      - Host: {server.smtp_host}:{server.smtp_port}")
            print(f"      - User: {server.smtp_user}")
            print(f"      - Password configuré: {'Oui' if server.smtp_pass else 'NON ⚠️'}")

            if not server.smtp_pass:
                print(f"      ❌ PROBLÈME: Mot de passe SMTP non configuré!")

    # ========== 5. VÉRIFIER LES EMAILS EN ERREUR ==========
    print("\n5️⃣ Vérification des emails en erreur...")

    MailMail = env['mail.mail']
    failed_mails = MailMail.sudo().search([
        ('state', '=', 'exception')
    ], limit=5, order='create_date desc')

    if failed_mails:
        print(f"   ⚠️  {len(failed_mails)} email(s) en erreur trouvé(s):\n")
        for mail in failed_mails:
            print(f"      Email #{mail.id}:")
            print(f"      - À: {mail.email_to}")
            print(f"      - Sujet: {mail.subject[:50]}")
            print(f"      - Erreur: {mail.failure_reason}")
            print()

        # Proposer de réessayer
        print(f"   💡 Vous pouvez réessayer ces emails après avoir corrigé la config:")
        print(f"      → Dans Odoo: Paramètres > Technique > Email > Emails")
        print(f"      → Sélectionner les emails en erreur")
        print(f"      → Action > Réessayer l'envoi")
    else:
        print(f"   ✅ Aucun email en erreur récent")

    # ========== RÉSUMÉ ==========
    print("\n" + "="*80)
    print("📋 RÉSUMÉ DES ACTIONS")
    print("="*80)

    print("""
✅ Vérifications effectuées:
   1. Paramètre web.base.url
   2. Template email de signature
   3. Test de rendering du template
   4. Configuration serveur SMTP
   5. Emails en erreur

🔧 PROCHAINES ÉTAPES:

   A. Si le serveur SMTP n'a pas de mot de passe:
      → Allez dans Paramètres > Technique > Email > Serveurs emails sortants
      → Éditez 'Brevo SMTP'
      → Ajoutez le mot de passe SMTP Brevo

   B. Testez l'envoi d'email:
      → Créez un nouveau document
      → Ajoutez un signataire
      → Envoyez pour signature (méthode: Email Odoo)
      → Vérifiez les logs Brevo + boîte mail

   C. Si problème persiste:
      → Exécutez: exec(open('test_email_complet.py').read())
      → Analysez les logs détaillés
""")

    print("\n" + "="*80)
    print("FIN DU FIX")
    print("="*80 + "\n")

# Exécuter
fix_template_et_config()
