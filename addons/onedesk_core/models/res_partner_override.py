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
                    _logger.info(f"⚠️ Partner without company_id - assigned to {default_company.name}")
        
        return super().create(vals_list)

    def write(self, vals):
        """Assurer que les partenaires ne perdent pas leur company_id"""
        # S'assurer qu'aucun partenaire n'a company_id = False
        if 'company_id' in vals and vals['company_id'] is False:
            default_company = self.env['res.company'].search([], limit=1)
            if default_company:
                vals['company_id'] = default_company.id
                _logger.warning(f"⚠️ Attempted to set company_id=False - reassigned to {default_company.name}")
        
        # Pour les partenaires existants sans company_id
        if not vals.get('company_id'):
            partners_without_company = self.filtered(lambda p: not p.company_id)
            if partners_without_company:
                default_company = self.env['res.company'].search([], limit=1)
                if default_company:
                    vals['company_id'] = default_company.id
                    _logger.info(f"⚠️ {len(partners_without_company)} partners without company_id - assigned to {default_company.name}")
        
        return super().write(vals)

    @api.model
    def fix_all_partners_without_company(self):
        """Fix all partners in DB that don't have company_id (call manually if needed)"""
        try:
            # Direct SQL update for all partners without company_id
            default_company = self.env['res.company'].search([], limit=1)
            if not default_company:
                _logger.error("❌ No default company found to assign partners")
                return
            
            # Use raw SQL to update ALL partners without company_id
            query = f"""
                UPDATE res_partner 
                SET company_id = {default_company.id}
                WHERE company_id IS NULL OR company_id = 0
            """
            self.env.cr.execute(query)
            self.env.cr.commit()
            
            count = self.search_count([('company_id', '=', False)])
            _logger.info(f"✅ Fixed partners: {count} remaining partners without company_id")
            
        except Exception as e:
            _logger.error(f"❌ Error fixing partners: {e}")
