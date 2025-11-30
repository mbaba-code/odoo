#!/usr/bin/env python3
"""
Script de test complet pour diagnostiquer et tester les emails de signature
À exécuter via: python3 odoo-bin shell -c odoo.conf -d onedesk --shell-interface ipython
Puis: exec(open('test_email_complet.py').read())
"""

def test_email_complet():
    """Test complet des emails de signature"""

    print("\n" + "="*80)
    print("🔍 TEST COMPLET - DIAGNOSTIC + TEST EMAIL SIGNATURE")
    print("="*80 + "\n")

    # ========== PARTIE 1: DIAGNOSTIC SMTP ==========
    print("📋 PARTIE 1: VÉRIFICATION CONFIGURATION SMTP")
    print("-" * 80)

    MailServer = env['ir.mail_server']
    servers = MailServer.sudo().search([])

    if not servers:
        print("❌ PROBLÈME CRITIQUE: Aucun serveur SMTP configuré!")
        print("   → Allez dans Paramètres > Technique > Email > Serveurs emails sortants")
        return

    for server in servers:
        print(f"\n✅ Serveur SMTP trouvé: {server.name}")
        print(f"   - Host: {server.smtp_host}:{server.smtp_port}")
        print(f"   - User: {server.smtp_user}")
        print(f"   - SSL/TLS: {server.smtp_encryption}")
        print(f"   - Priorité: {server.sequence}")

        # Test connexion SMTP
        try:
            print(f"\n   🔄 Test de connexion SMTP...")
            server.test_smtp_connection()
            print(f"   ✅ Connexion SMTP réussie!")
        except Exception as e:
            print(f"   ❌ ERREUR connexion SMTP: {e}")
            print(f"   → Vérifiez le login/password et la configuration Brevo")

    # ========== PARTIE 2: VÉRIFICATION TEMPLATE ==========
    print("\n\n📋 PARTIE 2: VÉRIFICATION TEMPLATE EMAIL")
    print("-" * 80)

    try:
        template = env.ref('onedesk_core.email_template_signature_request')
        print(f"✅ Template trouvé: {template.name} (ID: {template.id})")
        print(f"   - Modèle: {template.model}")
        print(f"   - Email From: {template.email_from}")
        print(f"   - Email To: {template.email_to}")
        print(f"   - Sujet: {template.subject}")
        print(f"   - Body HTML: {len(template.body_html)} caractères")
    except Exception as e:
        print(f"❌ ERREUR: Template non trouvé! {e}")
        return

    # ========== PARTIE 3: VÉRIFICATION SIGNATURES EXISTANTES ==========
    print("\n\n📋 PARTIE 3: VÉRIFICATION SIGNATURES EXISTANTES")
    print("-" * 80)

    Signature = env['onedesk.document.signature']
    recent_sigs = Signature.sudo().search([], order='create_date desc', limit=3)

    if not recent_sigs:
        print("⚠️  Aucune signature trouvée dans la base")
    else:
        print(f"✅ {len(recent_sigs)} signature(s) récente(s) trouvée(s):\n")

        for sig in recent_sigs:
            print(f"   Signature #{sig.id}:")
            print(f"   - Signataire: {sig.signer_name} ({sig.signer_email})")
            print(f"   - Document: {sig.document_id.name if sig.document_id else 'N/A'}")
            print(f"   - Statut: {sig.status}")
            print(f"   - Créé: {sig.create_date}")

            # Chercher les emails associés
            MailMail = env['mail.mail']
            mails = MailMail.sudo().search([
                ('res_id', '=', sig.id),
                ('model', '=', 'onedesk.document.signature')
            ], limit=1)

            if mails:
                mail = mails[0]
                print(f"   📧 Email #{mail.id}:")
                print(f"      État: {mail.state}")
                print(f"      De: {mail.email_from}")
                print(f"      À: {mail.email_to}")
                if mail.failure_reason:
                    print(f"      ❌ Erreur: {mail.failure_reason}")
            else:
                print(f"   ⚠️  Aucun email trouvé pour cette signature!")
            print()

    # ========== PARTIE 4: TEST TEMPLATE SIMPLE ==========
    print("\n📋 PARTIE 4: TEST AVEC TEMPLATE ULTRA SIMPLE")
    print("-" * 80)

    # Créer un template de test minimal
    print("\n1️⃣ Création d'un template de test minimal...")
    MailTemplate = env['mail.template']

    test_template = MailTemplate.sudo().create({
        'name': 'TEST Signature Minimal',
        'model_id': env.ref('onedesk_core.model_onedesk_document_signature').id,
        'email_from': 'kokouignace.baba@prefecto-etranger-aide.com',
        'email_to': '{{ object.signer_email }}',
        'subject': 'TEST OneDesk - {{ object.signer_name }}',
        'body_html': '''<html><body>
            <h2>Test Email OneDesk</h2>
            <p>Bonjour {{ object.signer_name }},</p>
            <p>Ceci est un email de test pour vérifier la configuration SMTP.</p>
            <p>Document: {{ object.document_id.name }}</p>
        </body></html>''',
    })
    print(f"   ✅ Template de test créé (ID: {test_template.id})")

    # Récupérer ou créer une signature de test
    test_sig = recent_sigs[0] if recent_sigs else None

    if not test_sig:
        print("\n   ⚠️  Aucune signature existante. Création d'une signature de test...")

        # Créer un document de test
        Document = env['onedesk.document']
        test_doc = Document.sudo().create({
            'name': 'TEST Document Email',
            'document_type': 'contract',
        })

        # Créer une signature de test (sans déclencher l'email auto)
        test_sig = Signature.sudo().with_context(mail_create_nosubscribe=True).create({
            'document_id': test_doc.id,
            'signer_email': 'merveillesbaba@gmail.com',
            'signer_name': 'Test Merveilles',
            'status': 'pending',
        })
        print(f"   ✅ Signature de test créée (ID: {test_sig.id})")

    print(f"\n2️⃣ Test d'envoi avec la signature #{test_sig.id}...")
    print(f"   - À: {test_sig.signer_email}")
    print(f"   - Nom: {test_sig.signer_name}")

    try:
        # Test du rendering
        print(f"\n   🔄 Test rendering du template...")
        body = test_template._render_field('body_html', [test_sig.id])[test_sig.id]
        subject = test_template._render_field('subject', [test_sig.id])[test_sig.id]
        print(f"   ✅ Rendering OK")
        print(f"      Sujet: {subject}")
        print(f"      Body: {len(body)} caractères")

        # Envoi
        print(f"\n   📧 Envoi de l'email de test...")
        mail_id = test_template.send_mail(test_sig.id, force_send=True)

        if mail_id:
            mail = env['mail.mail'].sudo().browse(mail_id)
            print(f"   ✅ Email créé (ID: {mail_id})")
            print(f"      État: {mail.state}")

            if mail.state == 'sent':
                print(f"\n   🎉 EMAIL ENVOYÉ AVEC SUCCÈS!")
                print(f"\n   ✅ CONCLUSION: SMTP fonctionne, le template simple fonctionne")
                print(f"      → Si les vrais emails ne partent pas, le problème est dans le template complexe")
            elif mail.state == 'exception':
                print(f"\n   ❌ EMAIL EN ERREUR!")
                if mail.failure_reason:
                    print(f"      Raison: {mail.failure_reason}")
            else:
                print(f"\n   ⏳ Email en attente (état: {mail.state})")
        else:
            print(f"   ⚠️  send_mail a retourné None")

    except Exception as e:
        print(f"\n   ❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

    # Nettoyage
    print(f"\n3️⃣ Nettoyage...")
    test_template.unlink()
    print(f"   ✅ Template de test supprimé")

    # ========== PARTIE 5: RECOMMANDATIONS ==========
    print("\n\n📋 PARTIE 5: RECOMMANDATIONS")
    print("-" * 80)

    print("""
✅ POINTS À VÉRIFIER:

1. SMTP Brevo:
   - Login: 9c50c1001@smtp-brevo.com
   - Host: smtp-relay.brevo.com:587
   - Email FROM vérifié: kokouignace.baba@prefecto-etranger-aide.com

2. Si le test simple RÉUSSIT mais pas les vrais emails:
   → Le problème est dans le template complexe (body_html avec QWeb)
   → Vérifier les expressions QWeb dans le template
   → Vérifier env['ir.config_parameter'].sudo().get_param('web.base.url')

3. Si le test simple ÉCHOUE aussi:
   → Problème SMTP (credentials, sender non vérifié, quota, etc.)
   → Vérifier dans Brevo Dashboard → Logs
   → Vérifier que l'email FROM est bien vérifié chez Brevo

4. Vérifier les emails en queue:
   → Paramètres > Technique > Email > Emails
   → Chercher les emails en état "exception" ou "outgoing"
""")

    print("\n" + "="*80)
    print("FIN DU TEST COMPLET")
    print("="*80 + "\n")

# Exécuter le test
test_email_complet()
