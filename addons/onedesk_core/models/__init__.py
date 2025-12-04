from . import onedesk_property
from . import onedesk_unit
from . import onedesk_seasonal_price
from . import onedesk_reservation
from . import onedesk_task
from . import onedesk_image

# ← NOUVEAU : Models d'intégration
from . import onedesk_integration
from . import onedesk_integration_provider
from . import onedesk_integration_log

# ← NOUVEAU : Models multi-tenant
from . import onedesk_plan
from . import onedesk_client
from . import res_company
from . import onedesk_audit_log
from . import account_move

# ← NOUVEAU : Overrides pour assurer la cohérence des données
from . import res_partner_override
from . import calendar_event_override

# ← NOUVEAU : Dashboard
from . import onedesk_dashboard
from . import onedesk_dashboard_sales
from . import onedesk_dashboard_reservations
from . import onedesk_dashboard_properties
from . import onedesk_dashboard_users

# ← NOUVEAU : Wizard pour multi-upload
from . import onedesk_image_wizard

# ← NOUVEAU : Documents et Signatures
from . import onedesk_document

# ← NOUVEAU : Payment Retry System (Phase C1)
from . import onedesk_payment_retry

# ← NOUVEAU : Availability Cache (Phase C2)
from . import onedesk_availability_cache

# ← NOUVEAU : Contact Importer
from . import contact_importer
