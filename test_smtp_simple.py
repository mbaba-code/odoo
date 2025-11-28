"""
Test simple pour vérifier le serveur SMTP
Exécuter depuis Python shell Odoo ou créer un menu action
"""

def test_smtp_simple():
    """Test d'envoi d'email simple pour vérifier SMTP"""

    # Récupérer le serveur SMTP
    IrMailServer = env['ir.mail_server']
    mail_server = IrMailServer.sudo().search([], limit=1)

    if not mail_server:
        print("❌ Aucun serveur SMTP configuré!")
        return False

    print(f"📧 Serveur SMTP: {mail_server.smtp_host}:{mail_server.smtp_port}")
    print(f"   User: {mail_server.smtp_user}")
    print(f"   From: {mail_server.smtp_from or 'Non défini'}")

    # Créer un email de test simple
    MailMail = env['mail.mail']

    test_email = MailMail.sudo().create({
        'subject': 'Test OneDesk - Signature',
        'body_html': '<p>Ceci est un test d\'envoi d\'email de signature.</p>',
        'email_to': 'merveillesbaba@gmail.com',
        'email_from': mail_server.smtp_user,  # Utiliser l'email du serveur SMTP
        'state': 'outgoing',
    })

    print(f"\n✉️ Email de test créé (ID: {test_email.id})")
    print(f"   De: {test_email.email_from}")
    print(f"   À: {test_email.email_to}")

    # Envoyer
    try:
        test_email.send()
        print("\n✅ Email envoyé avec succès!")
        print(f"   État: {test_email.state}")
        if test_email.failure_reason:
            print(f"   ⚠️ Raison échec: {test_email.failure_reason}")
        return True
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

# Exécuter
test_smtp_simple()
