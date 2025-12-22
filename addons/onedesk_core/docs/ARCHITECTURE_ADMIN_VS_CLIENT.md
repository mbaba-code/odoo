# Architecture: Interface Admin vs Client

## 🏗️ Séparation des Interfaces

### 📊 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE SAAS                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  👤 ADMIN (Vous)          │  👥 CLIENTS SaaS               │
│  ├─ SaaS Manager          │  ├─ Portail OneDesk            │
│  │  ├─ Tous les clients   │  │  ├─ Mon compte              │
│  │  ├─ Configuration DB   │  │  ├─ Mon domaine             │
│  │  ├─ Métriques          │  │  ├─ Facturation             │
│  │  └─ Domaines (ADMIN)   │  │  └─ Support                 │
│  │                        │  │                              │
│  └─ Module: onedesk_core  │  └─ Module: onedesk_core       │
│     (Backend/Admin)       │     (Frontend/Portal)           │
│                           │                                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Interface ADMIN (Actuelle)

### Localisation
**Module:** `onedesk_core` → Menu "SaaS Manager"

### Qui a accès?
- ✅ **Vous uniquement** (admin/super-utilisateur)
- ❌ **PAS les clients**

### Ce qui est visible:
```
SaaS Manager/
├── 📊 Dashboards
│   ├── Vue globale de tous les clients
│   ├── Métriques agrégées
│   └── Revenus totaux
│
├── 👥 Clients
│   ├── Liste complète des clients SaaS
│   ├── Détails de chaque client
│   │   ├── Informations contact
│   │   ├── Plan souscrit
│   │   ├── État de la base de données
│   │   ├── Métriques d'utilisation
│   │   └── 🌐 Domaine Personnalisé (ADMIN)  ← ICI
│   └── Actions admin:
│       ├── Provisionner base
│       ├── Suspendre/Activer
│       ├── Configurer domaine
│       └── Reset base
│
├── 📦 Plans SaaS
├── 💾 Bases de Données
├── 🚨 Alertes
└── 📈 Métriques
```

### Section "Domaine Personnalisé" (Admin)

**Localisation exacte:**
`SaaS Manager → Clients → [Client] → Section "🔐 Domaine Personnalisé"`

**Fonctionnalités admin:**
- ✅ Voir tous les domaines de tous les clients
- ✅ Configurer domaine + SSL pour un client
- ✅ Tester localement avant production
- ✅ Supprimer un domaine
- ✅ Voir l'état SSL
- ✅ Accès direct à tous les logs

**Workflow:**
1. Client demande un domaine personnalisé (par email/support)
2. Client configure son DNS
3. **Vous** entrez dans SaaS Manager
4. **Vous** saisissez le domaine
5. **Vous** cliquez "Test Local" (développement) ou "PROD" (production)
6. Système configure Nginx + SSL automatiquement
7. **Vous** validez et informez le client

## 👥 Interface CLIENT (À créer si nécessaire)

### Option 1: Portail OneDesk (Recommandé)

Si vous voulez que les clients gèrent leur domaine eux-mêmes:

```python
# Créer un controller portal
# /onedesk/portal/domain
```

**Interface client verrait:**
```
Mon Compte OneDesk
├── Informations
├── Mon Abonnement
├── 🌐 Mon Domaine  ← Nouvelle section
│   ├── Domaine actuel: exemple.com
│   ├── Instructions DNS
│   ├── Formulaire: Demander changement domaine
│   └── Status: En attente / Actif / Refusé
└── Facturation
```

**Workflow:**
1. Client se connecte à son portail OneDesk
2. Section "Mon Domaine"
3. Formulaire de demande de changement
4. **Vous** recevez notification
5. **Vous** validez et configurez (interface admin)
6. Client reçoit confirmation

### Option 2: Email/Support (Actuel)

**Plus simple**, pas besoin de coder:
1. Client envoie email avec nouveau domaine
2. **Vous** configurez dans SaaS Manager
3. **Vous** répondez au client

## 📍 Où est Quoi?

### Fichiers Interface ADMIN

```
addons/onedesk_core/
├── models/
│   └── saas_client.py                   ← Logique domaine
│       ├── action_setup_custom_domain()
│       ├── action_setup_custom_domain_test()
│       └── action_remove_custom_domain()
│
├── views/
│   └── saas_client_views.xml           ← Interface admin
│       └── Section "Domaine Personnalisé"
│
├── scripts/
│   ├── setup_client_domain.sh          ← Script production
│   └── test_client_domain_local.sh     ← Script test
│
└── security/
    └── ir.model.access.csv             ← Droits d'accès
        └── saas.client → Managers seulement
```

### Fichiers Interface CLIENT (si besoin)

```
addons/onedesk_core/
├── controllers/
│   └── portal.py                       ← Nouveau: Portal client
│       └── /onedesk/portal/domain
│
├── views/
│   └── portal_templates.xml            ← Nouveau: Templates portal
│       └── Page domaine client
│
└── models/
    └── domain_request.py               ← Nouveau: Demandes domaine
        └── État: En attente/Approuvé/Refusé
```

## 🚀 Recommandation

### Pour l'instant (SIMPLE)

**✅ Interface ADMIN seulement** (déjà créée)
- Clients contactent par email
- Vous configurez dans SaaS Manager
- Rapide, sécurisé, contrôle total

### Plus tard (AVANCÉ)

**🔄 Ajouter interface client portal**
- Client peut demander changement domaine
- Workflow de validation
- Plus automatisé mais plus complexe

## 🔒 Sécurité et Accès

### Droits d'Accès Actuels

```xml
<!-- ir.model.access.csv -->
model_id,group_id,access
saas.client,saas_manager,CRUD   ← Vous seulement
saas.client,portal_user,Read    ← Client: lecture basique seulement
```

### Qui Voit Quoi?

| Élément                      | Admin | Client |
|------------------------------|-------|--------|
| Menu "SaaS Manager"          | ✅    | ❌     |
| Liste tous clients           | ✅    | ❌     |
| Détails client (propre)      | ✅    | ✅ *   |
| Configuration domaine        | ✅    | ❌     |
| Scripts Nginx/SSL            | ✅    | ❌     |
| Métriques tous clients       | ✅    | ❌     |
| Portail OneDesk              | ✅    | ✅     |

`*` = Via portail uniquement, pas SaaS Manager

## 📝 Pour Créer Interface Client (Optionnel)

Si vous voulez que les clients gèrent leur domaine:

### 1. Créer modèle de demande

```python
# models/domain_request.py
class DomainRequest(models.Model):
    _name = 'saas.domain.request'

    client_id = fields.Many2one('saas.client')
    requested_domain = fields.Char('Domaine Demandé')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En Attente Validation'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé'),
    ])
    rejection_reason = fields.Text()
```

### 2. Créer controller portal

```python
# controllers/portal.py
@route(['/onedesk/portal/domain'], auth='user', website=True)
def portal_domain(self, **kw):
    client = request.env.user.partner_id.saas_client_id
    return request.render('onedesk_core.portal_domain', {
        'client': client,
        'domain': client.custom_domain,
    })
```

### 3. Créer template

```xml
<!-- views/portal_templates.xml -->
<template id="portal_domain">
    <t t-call="portal.portal_layout">
        <h1>Mon Domaine Personnalisé</h1>
        <p>Domaine actuel: <t t-esc="domain or 'Aucun'"/></p>

        <form action="/onedesk/portal/domain/request" method="post">
            <input type="text" name="domain" placeholder="exemple.com"/>
            <button type="submit">Demander Changement</button>
        </form>
    </t>
</template>
```

Mais **ce n'est PAS nécessaire pour l'instant!**

## ✅ État Actuel (Correct)

**Ce qui est implémenté:**
- ✅ Interface admin complète dans SaaS Manager
- ✅ Boutons Test Local et Production
- ✅ Scripts automatisés (Nginx + SSL)
- ✅ Logs et monitoring
- ✅ Droits d'accès restreints (admin only)

**Ce qui fonctionne:**
1. Vous ouvrez SaaS Manager (admin)
2. Vous sélectionnez un client
3. Vous configurez son domaine
4. Le client peut utiliser son domaine
5. Le client NE voit PAS l'interface admin

**C'est parfait pour commencer!** L'interface client peut être ajoutée plus tard si besoin.

## 🎯 Conclusion

**L'interface actuelle est dans SaaS Manager = ADMIN SEULEMENT**

C'est **volontaire et correct** car:
- ✅ Vous gardez le contrôle total
- ✅ Évite erreurs de configuration client
- ✅ Sécurité renforcée (scripts sudo)
- ✅ Validation manuelle avant activation
- ✅ Support direct si problème

Les clients verront juste leur domaine fonctionner, point. Ils n'ont pas besoin de voir les détails techniques.

Si plus tard vous voulez une interface client, on pourra l'ajouter facilement dans le portail OneDesk. Mais ce n'est pas nécessaire pour démarrer!
