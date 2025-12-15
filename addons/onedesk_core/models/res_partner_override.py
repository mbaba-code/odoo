import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# Liste des partners qui DOIVENT rester globaux (company_id = False)
SYSTEM_PARTNERS = [
    'Administrator',
    'OdooBot',
    'Public user',
    'Portal',
]


class ResPartnerOverride(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals_list):
        """Assurer que les nouveaux partenaires ont un company_id (sauf partners système)"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            partner_name = vals.get('name', '')

            # Si c'est un partner système, NE PAS assigner de company_id
            if partner_name in SYSTEM_PARTNERS:
                vals['company_id'] = False
                _logger.info(f"✅ System partner '{partner_name}' created with company_id=False (global)")
                continue

            # Pour les partners normaux, assigner une company si pas défini
            if not vals.get('company_id'):
                # Essayer d'utiliser la company de l'utilisateur créateur
                current_user = self.env.user
                if current_user and current_user.company_id:
                    vals['company_id'] = current_user.company_id.id
                    _logger.info(f"✅ Partner '{partner_name}' assigned to creator's company: {current_user.company_id.name}")
                else:
                    # Fallback: company par défaut
                    default_company = self.env['res.company'].search([], limit=1)
                    if default_company:
                        vals['company_id'] = default_company.id
                        _logger.info(f"⚠️ Partner '{partner_name}' assigned to default company: {default_company.name}")

        return super().create(vals_list)

    def write(self, vals):
        """Permettre company_id=False pour les partners système, sinon garantir une company"""
        # Si on essaie de mettre company_id = False
        if 'company_id' in vals and vals['company_id'] is False:
            # Vérifier si c'est un partner système
            system_partners = self.filtered(lambda p: p.name in SYSTEM_PARTNERS)

            if system_partners:
                # OK pour les partners système
                _logger.info(f"✅ System partners set to company_id=False: {system_partners.mapped('name')}")
                # Ne rien changer, laisser False
            else:
                # Pour les partners normaux, assigner une company
                non_system = self - system_partners
                if non_system:
                    # Utiliser la company de l'utilisateur
                    current_user = self.env.user
                    if current_user and current_user.company_id:
                        vals['company_id'] = current_user.company_id.id
                        _logger.warning(f"⚠️ Prevented company_id=False for {len(non_system)} partners - assigned to {current_user.company_id.name}")
                    else:
                        # Fallback: company par défaut
                        default_company = self.env['res.company'].search([], limit=1)
                        if default_company:
                            vals['company_id'] = default_company.id
                            _logger.warning(f"⚠️ Prevented company_id=False for {len(non_system)} partners - assigned to {default_company.name}")

        return super().write(vals)

    @api.model
    def fix_system_partners_global(self):
        """
        Mettre tous les partners système en global (company_id = False)
        À appeler manuellement si besoin
        """
        _logger.info("🔧 Fixing system partners to be global...")

        for partner_name in SYSTEM_PARTNERS:
            partner = self.search([('name', '=', partner_name)], limit=1)
            if partner and partner.company_id:
                old_company = partner.company_id.name
                partner.sudo().write({'company_id': False})
                _logger.info(f"  ✅ {partner_name}: {old_company} → False (global)")

        _logger.info("✅ System partners are now global")
