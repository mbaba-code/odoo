# 📧 Guide Complet - Faire Partir les Emails Réellement

Tu as configuré les templates d'email, mais ils sont juste en **"attente"** (outgoing) dans la queue. Voici comment faire pour qu'ils partent **réellement** vers les destinataires.

---

## 🎯 Le Problème

Actuellement, les emails sont créés mais **restent bloqués** dans la queue Odoo parce que:

1. ❌ **Pas de serveur SMTP configuré** - Odoo ne sait pas comment envoyer les emails
2. ❌ **Pas de cron job actif** - Les emails ne sont pas envoyés automatiquement
3. ❌ **Pas de service de mail externe** - Rien ne pousse les emails dehors

**Résultat**: Les emails restent "outgoing" pour toujours.

---

## ✅ Solution: 3 Options

### 🔥 Option 1: Configuration SMTP Locale (Plus Simple Pour Dev)

**Tu as un serveur email local ou service gratuit?**

#### A. Configure le Serveur SMTP dans Odoo

**Odoo UI → Settings → Email → Outgoing Mail Servers**

Crée un nouveau serveur avec ces infos:

**Pour Gmail** (avec app password):
```
Server Name: Gmail
SMTP Server: smtp.gmail.com
SMTP Port: 587
Username: ton-email@gmail.com
Password: APP_PASSWORD (pas le mot de passe normal!)
Security: TLS
```

**Pour Mailgun** (service gratuit - RECOMMANDÉ):
```
Server Name: Mailgun
SMTP Server: smtp.mailgun.org
SMTP Port: 587
Username: postmaster@votre-domaine.mailgun.org
Password: (de Mailgun)
Security: TLS
```

**Pour Mailtrap** (gratuit pour tester):
```
Server Name: Mailtrap
SMTP Server: live.smtp.mailtrap.io
SMTP Port: 587
Username: (de Mailtrap)
Password: (de Mailtrap)
Security: TLS
```

**Pour localhost** (si tu as un serveur local):
```
Server Name: Localhost
SMTP Server: localhost
SMTP Port: 25
No auth required
```

#### B. Test la Connexion

Dans la même interface:
- Clique **"Test Connection"**
- Attends la confirmation ✓

#### C. Envoie les Emails en Queue

```python
# Dans Odoo Shell
emails = env['mail.mail'].search([('state', '=', 'outgoing')])
for email in emails:
    email.send()
    print(f"✓ Envoyé: {email.subject}")
```

**Ou via l'API Odoo:**

Odoo UI → Settings → Email → Sent Emails
- Sélectionne tous les emails "outgoing"
- Action → Send

---

### 🚀 Option 2: AWS SES (Production - Fiable)

**Pour une vraie production avec bon délivrabilité:**

1. **Crée un compte AWS**
2. **Vérifie ton domaine** dans SES
3. **Crée des credentials SMTP**
4. **Configure dans Odoo:**

```
Server Name: AWS SES
SMTP Server: email-smtp.region.amazonaws.com
SMTP Port: 587
Username: (de AWS SES)
Password: (de AWS SES)
Security: TLS
```

---

### 📦 Option 3: Service Email Commercial (SendGrid, Brevo, etc.)

**Pour la meilleure délivrabilité:**

**Brevo** (anciennement Sendinblue - gratuit pour 300 emails/jour):
```
Server Name: Brevo
SMTP Server: smtp-relay.brevo.com
SMTP Port: 587
Username: ton-email@example.com
Password: (clé API de Brevo)
Security: TLS
```

---

## 🔄 Configuration Automatique des Emails

Maintenant que le serveur SMTP est configuré, il faut que les emails se **envoient automatiquement**.

### Étape 1: Activer le Cron Job Email

**Odoo UI → Settings → Scheduled Actions**

Cherche: **"Mail: Outgoing Emails"**

```
Name: Mail: Outgoing Emails
Model: mail.mail
Interval: 1 minutes (IMPORTANT: change à 1 minute pour tester!)
```

- **Vérifie le checkmark ✓ "Active"**
- Clique **"Execute Now"** pour tester

### Étape 2: Configuration du Système d'Email

**Odoo UI → Settings → Email → Email Configuration**

```
Default Email Address: noreply@example.com
Default Email Name: OneDesk
Bounce Address: bounce@example.com (optionnel)
```

### Étape 3: Ajoute l'Email "From" Correct

Dans chaque template d'email:

**Settings → Email → Email Templates**

Pour chaque template OneDesk:
```
Email From: ${object.company_id.email or 'noreply@onedesk.io'}
```

Ou directement:
```
Email From: noreply@onedesk.io
```

---

## 🧪 Test Complet

### Test 1: Vérifier la Queue

```python
# Dans Odoo Shell
pending = env['mail.mail'].search([('state', '=', 'outgoing')])
print(f"Emails en attente: {len(pending)}")
for email in pending[:3]:
    print(f"  - {email.subject} → {email.email_to}")
```

### Test 2: Envoyer Manuellement

```python
# Dans Odoo Shell
mail = env['mail.mail'].search([('state', '=', 'outgoing')], limit=1)
if mail:
    mail.send()
    print(f"Envoyé: {mail.subject}")
    print(f"État: {mail.state}")
```

### Test 3: Créer un Email de Test

```python
# Dans Odoo Shell
test_mail = env['mail.mail'].create({
    'subject': '🧪 TEST EMAIL - OneDesk',
    'email_to': 'ton-email@example.com',  # ← Mets ton email!
    'email_from': 'noreply@onedesk.io',
    'body_html': '<p>Ceci est un email de test</p>',
})

test_mail.send()
print(f"✓ Email de test envoyé!")
print(f"  État: {test_mail.state}")
```

**Regarde ta boîte email - tu devrais recevoir l'email!**

---

## 📊 Vérifier que tout Marche

### Après avoir configuré SMTP:

```bash
# Dans Odoo Shell

# 1. Vérifie la config SMTP
config = env['ir.config_parameter'].sudo()
print("=== EMAIL CONFIG ===")
print(f"SMTP Server: {config.get_param('mail.smtp.server')}")
print(f"SMTP Port: {config.get_param('mail.smtp.port')}")
print(f"SMTP User: {config.get_param('mail.smtp.user')}")

# 2. Vérifie les outgoing servers
servers = env['ir.mail_server'].search([])
print(f"\n=== MAIL SERVERS ({len(servers)}) ===")
for server in servers:
    print(f"✓ {server.name}: {server.smtp_host}:{server.smtp_port}")

# 3. Vérifie les emails en attente
pending = env['mail.mail'].search_count([('state', '=', 'outgoing')])
sent = env['mail.mail'].search_count([('state', '=', 'sent')])
failed = env['mail.mail'].search_count([('state', '=', 'failed')])

print(f"\n=== EMAIL QUEUE ===")
print(f"⏳ Outgoing: {pending}")
print(f"✓ Sent: {sent}")
print(f"✗ Failed: {failed}")

# 4. Essaie d'envoyer les mails en queue
if pending > 0:
    emails = env['mail.mail'].search([('state', '=', 'outgoing')], limit=5)
    for email in emails:
        try:
            email.send()
            print(f"✓ Sent: {email.subject}")
        except Exception as e:
            print(f"✗ Failed: {email.subject} - {str(e)}")
```

---

## 🆘 Troubleshooting

### Problème: "No SMTP Server Defined"

**Solution:**
```
Settings → Email → Outgoing Mail Servers
→ Crée un nouveau serveur
→ Teste la connexion
```

### Problème: "Connection Refused"

**Check:**
1. SMTP Server address correct?
2. SMTP Port correct? (587 pour TLS, 25 pour non-sécurisé)
3. Firewall bloque le port?

### Problème: "Authentication Failed"

**Check:**
1. Username correct?
2. Password/API Key correct?
3. App password pour Gmail? (pas le mot de passe normal)

### Problème: "Relay Access Denied"

**Solution:**
- Utilise un service comme Mailgun, Brevo, ou AWS SES
- Pas localhost qui refuse les connexions externes

---

## 📋 Checklist - Emails Réels

- [ ] SMTP Server configuré dans Odoo
- [ ] Connexion SMTP testée ✓
- [ ] Cron job "Mail: Outgoing Emails" actif
- [ ] Email templates ont "Email From" configuré
- [ ] Test: Email de test créé et envoyé
- [ ] Check: Email reçu dans ta boîte?

---

## 🎯 Résumé Rapide

**Pour que les mails partent réellement:**

1. **Configure SMTP** → Settings → Email → Outgoing Mail Servers
2. **Test la connexion** → Clique "Test Connection" ✓
3. **Active le Cron** → Settings → Scheduled Actions → "Mail: Outgoing Emails"
4. **Envoie manuellement** → Shell: `mail.send()` ou UI action

**Résultat:**
- État change: `outgoing` → `sent` ✓
- Email arrive dans la boîte du destinataire ✓
- Logs montrent succès ✓

---

## 🚀 Production Checklist

Avant de déployer en production:

- [ ] SMTP Server robuste (AWS SES, Mailgun, Brevo)
- [ ] SPF/DKIM/DMARC configurés (meilleure délivrabilité)
- [ ] Cron job configuré pour envoyer toutes les minutes
- [ ] Bounce address configuré
- [ ] Test avec vraies adresses emails
- [ ] Monitor la queue d'emails
- [ ] Logs email vérifiés

---

**Besoin d'aide? Dis-moi quel serveur SMTP tu veux utiliser et je te aide à le configurer!** 🚀
