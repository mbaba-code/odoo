import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResPartnerOverride(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals_list):
        """Assurer que tous les nouveaux partenaires ont un company_id"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        for vals in vals_list:
            # Si pas de company_id, assigner la compagnie par défaut
            if not vals.get('company_id'):
                default_company = self.env['res.company'].search([], limit=1)
                if default_company:
                    vals['company_id'] = default_company.id
                    _logger.info(f"⚠️ Partenaire sans company_id - assignation à {default_company.name}")
        
        return super().create(vals_list)

    def write(self, vals):
        """Assurer que les partenaires ne perdent pas leur company_id"""
        # S'assurer qu'aucun partenaire n'a company_id = False
        if 'company_id' in vals and vals['company_id'] is False:
            default_company = self.env['res.company'].search([], limit=1)
            if default_company:
                vals['company_id'] = default_company.id
                _logger.warning(f"⚠️ Tentative d'assigner company_id=False - changement à {default_company.name}")
        
        # Pour les partenaires existants sans company_id
        if not vals.get('company_id'):
            for partner in self:
                if not partner.company_id:
                    default_company = self.env['res.company'].search([], limit=1)
                    if default_company and 'company_id' not in vals:
                        vals['company_id'] = default_company.id
                        _logger.info(f"⚠️ Partenaire {partner.name} sans company_id - assignation à {default_company.name}")
        
        return super().write(vals)
