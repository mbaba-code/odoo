"""
Script de diagnostic pour vérifier TOUS les emails de signature dans Odoo
Exécuter depuis le shell Odoo ou créer un menu action
"""

def diagnostic_emails_signature():
    """Diagnostic complet des emails de signature"""

    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC COMPLET - EMAILS DE SIGNATURE")
    print("="*80 + "\n")

    # 1. Chercher les documents récents avec signatures
    print("1️⃣ Recherche des documents en signature...")
    Document = env['onedesk.document']
    docs = Document.sudo().search([
        ('status', '=', 'pending_signature')
    ], order='create_date desc', limit=5)

    if not docs:
        print("   ⚠️  Aucun document en attente de signature")
        print("   Cherchons tous les documents récents...")
        docs = Document.sudo().search([], order='create_date desc', limit=5)

    for doc in docs:
        print(f"\n📄 Document: {doc.name} (ID: {doc.id}, Status: {doc.status})")

        # 2. Vérifier les signatures pour ce document
        Signature = env['onedesk.document.signature']
        signatures = Signature.sudo().search([('document_id', '=', doc.id)])

        print(f"   Signatures: {len(signatures)}")

        for sig in signatures:
            print(f"\n   ✍️  Signature #{sig.id}:")
            print(f"      - Signataire: {sig.signer_name} ({sig.signer_email})")
            print(f"      - Statut: {sig.status}")
            print(f"      - Créé: {sig.create_date}")

            # 3. Vérifier les mails associés à cette signature
            MailMail = env['mail.mail']
            mails = MailMail.sudo().search([
                ('res_id', '=', sig.id),
                ('model', '=', 'onedesk.document.signature')
            ])

            print(f"      - Emails trouvés: {len(mails)}")

            for mail in mails:
                print(f"\n      📧 Email ID {mail.id}:")
                print(f"         État: {mail.state}")
                print(f"         De: {mail.email_from}")
                print(f"         À: {mail.email_to}")
                print(f"         Sujet: {mail.subject}")
                print(f"         Date: {mail.create_date}")

                if mail.failure_reason:
                    print(f"         ❌ ERREUR: {mail.failure_reason}")

                if mail.state == 'sent':
                    print(f"         ✅ Email envoyé avec succès!")
                elif mail.state == 'exception':
                    print(f"         ❌ Email en erreur!")
                elif mail.state == 'outgoing':
                    print(f"         ⏳ Email en attente d'envoi")
                elif mail.state == 'cancel':
                    print(f"         🚫 Email annulé")

            # 4. Vérifier les messages (chatter)
            Message = env['mail.message']
            messages = Message.sudo().search([
                ('res_id', '=', sig.id),
                ('model', '=', 'onedesk.document.signature')
            ])

            print(f"      - Messages (chatter): {len(messages)}")
            for msg in messages[:3]:  # Limiter à 3 messages
                print(f"         • {msg.date}: {msg.body[:100]}...")

    # 5. Vérifier le template email
    print("\n\n2️⃣ Vérification du template email...")
    try:
        template = env.ref('onedesk_core.email_template_signature_request')
        print(f"   ✅ Template trouvé: {template.name}")
        print(f"      - Modèle: {template.model}")
        print(f"      - Email From: {template.email_from}")
        print(f"      - Email To: {template.email_to}")
        print(f"      - Sujet: {template.subject}")
    except Exception as e:
        print(f"   ❌ ERREUR: Template non trouvé! {e}")

    # 6. Vérifier le serveur SMTP
    print("\n3️⃣ Vérification serveur SMTP...")
    MailServer = env['ir.mail_server']
    servers = MailServer.sudo().search([])

    if not servers:
        print("   ❌ AUCUN serveur SMTP configuré!")
    else:
        for server in servers:
            print(f"   ✅ Serveur: {server.name}")
            print(f"      - Host: {server.smtp_host}:{server.smtp_port}")
            print(f"      - User: {server.smtp_user}")
            print(f"      - From: {server.smtp_from or '(non défini)'}")
            print(f"      - Priorité: {server.sequence}")

    # 7. Vérifier les emails en queue
    print("\n4️⃣ Emails en queue (non envoyés)...")
    queued = MailMail.sudo().search([
        ('state', 'in', ['outgoing', 'exception'])
    ], limit=10)

    print(f"   Total en queue: {len(queued)}")
    for mail in queued:
        print(f"   • ID {mail.id}: {mail.state} - {mail.email_to} - {mail.subject[:50]}")
        if mail.failure_reason:
            print(f"     Erreur: {mail.failure_reason}")

    print("\n" + "="*80)
    print("FIN DU DIAGNOSTIC")
    print("="*80 + "\n")

# Exécuter le diagnostic
diagnostic_emails_signature()
