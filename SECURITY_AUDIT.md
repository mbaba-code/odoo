# 🔒 Rapport d'Audit Sécurité - OneDesk

**Date**: 2025-11-24
**Modules Audités**:
- onedesk_core
- website_onedesk

---

## ⚠️ PROBLÈMES CRITIQUES TROUVÉS

### 🔴 1. SQL Injection Potentielle (CRITIQUE)

**Fichier**: `onedesk_core/models/res_partner_override.py` (ligne 57-62)

**Code Vulnérable**:
```python
query = f"""
    UPDATE res_partner
    SET company_id = {default_company.id}
    WHERE company_id IS NULL OR company_id = 0
"""
self.env.cr.execute(query)
```

**Problème**: Utilisation d'une f-string pour construire une requête SQL
**Risque**: SQL Injection (bien que dans ce cas `default_company.id` soit un entier Odoo, c'est une mauvaise pratique)

**Solution**: Utiliser des paramètres liés:
```python
query = """
    UPDATE res_partner
    SET company_id = %s
    WHERE company_id IS NULL OR company_id = 0
"""
self.env.cr.execute(query, (default_company.id,))
```

---

### 🔴 2. CSRF Vulnerabilities (CRITIQUE)

**Fichiers Affectés**:

#### A. `onedesk_core/controllers/public_reservation.py` (ligne 40)
```python
@http.route('/onedesk/public/reservation/create', type='jsonrpc', auth='public', csrf=False)
def create_reservation(self, **data):
```

#### B. `website_onedesk/controllers/main.py`
```python
# Ligne 81
@http.route('/onedesk/booking', type='http', auth='public', website=True, methods=['POST'], csrf=False)

# Ligne 363
@http.route('/onedesk/subscription/create', type='http', auth='public', website=True, methods=['POST'], csrf=False)
```

**Problème**: Routes POST publiques sans protection CSRF
**Risque**: Un attaquant peut forcer des utilisateurs à créer des réservations/abonnements non autorisés

**Solution**:
1. Pour les routes authentifiées: Enlever `csrf=False` (Odoo activera CSRF par défaut)
2. Pour les routes publiques: Implémenter une validation CSRF alternative ou ajouter un token

```python
# Option 1: Supprimer csrf=False (si l'utilisateur est authentifié)
@http.route('/onedesk/public/reservation/create', type='jsonrpc', auth='user')
def create_reservation(self, **data):

# Option 2: Vérifier un token
@http.route('/onedesk/public/booking', type='http', auth='public', methods=['POST'])
def create_booking(self, **kw):
    token = kw.get('csrf_token')
    if not self._validate_csrf_token(token):
        return {'error': 'Invalid token'}
```

---

### 🟡 3. Webhook SignaturIT Sans Validation (MOYEN)

**Fichier**: `onedesk_core/controllers/signaturit_webhook.py` (ligne 12)

**Code**:
```python
@http.route('/signaturit/webhook', auth='none', type='json', csrf=False, methods=['POST'])
def signaturit_webhook(self, **kwargs):
```

**Problème**: Webhook public sans validation d'authentification
**Risque**: N'importe qui peut envoyer des faux webhooks et modifier le statut des documents

**Solution**: Valider le signature/token de SignaturIT

```python
@http.route('/signaturit/webhook', auth='none', type='json', csrf=False, methods=['POST'])
def signaturit_webhook(self, **kwargs):
    # Valider le webhook signature
    data = request.get_json_data()
    signature = request.httprequest.headers.get('X-Signaturit-Signature')

    if not self._validate_signaturit_signature(data, signature):
        return {'status': 'error', 'message': 'Invalid signature'}, 401

    # ... suite du traitement
```

---

### 🟡 4. Exposition de Données Sensibles dans Logs (MOYEN)

**Fichier**: `website_onedesk/controllers/main.py` (ligne 84-88)

**Code**:
```python
_logger.info('===== START create_booking_request =====')
_logger.info(f'Raw data: {request.httprequest.data}')  # ⚠️ Données sensibles!
```

**Problème**: Les données des réservations (emails, dates, etc.) sont loggées en plain text
**Risque**: Fuite d'informations sensibles dans les logs

**Solution**: Ne logger que les IDs/références:
```python
_logger.info('Booking request received for unit')
# Ne pas logger les données personnelles!
```

---

### 🟡 5. Pas de Rate Limiting (MOYEN)

**Routes Affectées**:
- `/onedesk/public/reservation/create`
- `/onedesk/booking`
- `/onedesk/subscription/create`

**Problème**: Pas de limite sur le nombre de requêtes
**Risque**: Spam, brute force, DoS

**Solution**: Implémenter un rate limiting
```python
# Ajouter un middleware ou vérifier la limite par IP
if self._is_rate_limited(request.remote_addr):
    return {'error': 'Too many requests'}, 429
```

---

### 🟡 6. Input Validation Insuffisante (MOYEN)

**Fichier**: `website_onedesk/controllers/main.py` (ligne 144-145)

**Code**:
```python
start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
```

**Problème**: Pas de validation des dates (dates passées, ordre incorrect)
**Risque**: Réservations avec des dates invalides

**Solution**:
```python
try:
    start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()

    # Valider les dates
    today = datetime.now().date()
    if start_date < today:
        raise ValueError("La date de début ne peut pas être dans le passé")
    if end_date <= start_date:
        raise ValueError("La date de fin doit être après la date de début")
    if (end_date - start_date).days > 365:
        raise ValueError("La réservation ne peut pas dépasser 365 jours")

except ValueError as e:
    return {'error': str(e)}, 400
```

---

### 🟢 7. Access Control (BON ✓)

**Status**: ✅ CORRECT

- Les modèles `onedesk_payment_retry` et `onedesk_availability_cache` ont maintenant des règles d'accès
- Isolation par `company_id` respectée
- Permissions par groupe (PM, Staff, Viewer, Admin, Support)

---

### 🟢 8. OAuth State Validation (BON ✓)

**Fichier**: `onedesk_core/controllers/oauth_callback.py`

**Code**:
```python
integration = request.env['onedesk.integration'].sudo().search([
    ('oauth_state', '=', state),
    ('state', '=', 'connecting'),
], limit=1)
```

**Status**: ✅ Correctement validé

---

## 📋 Résumé des Vulnérabilités

| # | Sévérité | Type | Statut |
|---|----------|------|--------|
| 1 | 🔴 CRITIQUE | SQL Injection | À fixer |
| 2 | 🔴 CRITIQUE | CSRF | À fixer |
| 3 | 🟡 MOYEN | Webhook sans validation | À fixer |
| 4 | 🟡 MOYEN | Exposition données logs | À fixer |
| 5 | 🟡 MOYEN | Pas de rate limiting | À considérer |
| 6 | 🟡 MOYEN | Input validation | À améliorer |
| 7 | 🟢 BON | Access Control | ✅ OK |
| 8 | 🟢 BON | OAuth State | ✅ OK |

---

## 🔧 Plan de Correction

### Priorité 1 (URGENT - Faire d'abord):

1. **Fixer SQL Injection** (5 min)
   ```bash
   # Modifier onedesk_core/models/res_partner_override.py ligne 57-62
   # Utiliser des paramètres liés au lieu de f-string
   ```

2. **Fixer CSRF** (10 min)
   ```bash
   # Pour les routes authentifiées: enlever csrf=False
   # Pour les routes publiques: ajouter validation CSRF/token
   ```

3. **Valider Webhooks** (10 min)
   ```bash
   # Ajouter signature validation pour SignaturIT webhook
   ```

### Priorité 2 (Recommandé):

4. **Nettoyer les logs** (5 min)
   - Supprimer les données sensibles des logs

5. **Ajouter Input Validation** (15 min)
   - Valider les dates
   - Valider les champs email
   - Valider les montants

6. **Rate Limiting** (20 min)
   - Implémenter par IP ou par utilisateur

---

## 🚀 Commandes à Exécuter

```bash
# 1. Fixer SQL Injection
cd /home/user/odoo/addons/onedesk_core
# Modifier res_partner_override.py

# 2. Fixer CSRF
# Modifier controllers/public_reservation.py
# Modifier website_onedesk/controllers/main.py

# 3. Valider Webhooks
# Modifier controllers/signaturit_webhook.py

# Commit tout
git add -A
git commit -m "Fix security vulnerabilities: SQL injection, CSRF, webhook validation"
git push origin claude/analyze-onedesk-core-01Mugm4u4MDrVuH1oD3hgpmG
```

---

## ✅ Recommendations Supplémentaires

1. **Authentification Webhook**: Implémenter HMAC-SHA256 pour valider les webhooks SignaturIT
2. **HTTPS Obligatoire**: Assurer que toutes les routes sensibles utilisent HTTPS
3. **Logging**: Utiliser un logger sécurisé qui ne log pas les données sensibles
4. **Secrets Management**: Stocker les secrets (API keys) dans des variables d'environnement, pas en dur
5. **Audit Trail**: Enregistrer toutes les modifications sensibles
6. **Tests de Sécurité**: Ajouter des tests de sécurité dans la CI/CD
7. **CORS**: Vérifier la configuration CORS pour éviter les accès non autorisés

---

**Besoin d'aide pour fixer ces vulnérabilités?**
Je peux les corriger maintenant! Dis-moi et je les fixe une par une. 🔒
