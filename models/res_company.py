from odoo import fields, models, api, _, Command
from datetime import timedelta, datetime, date

import logging

_logger = logging.getLogger(__name__)
class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_user_fiscal_lock_date(self):
        """Get the fiscal lock date for this company depending on the user"""
        lock_date = max(self.period_lock_date or date.min, self.fiscalyear_lock_date or date.min)
        #if self.user_has_groups('account.group_account_manager'):
            #lock_date = self.fiscalyear_lock_date or date.min
        #if self.parent_id:
            # We need to use sudo, since we might not have access to a parent company.
            #lock_date = max(lock_date, self.sudo().parent_id._get_user_fiscal_lock_date())
        return lock_date

    def _get_violated_lock_dates(self, accounting_date, has_tax, tax_date=None):
        """Get all the lock dates affecting the current accounting_date.
        :param accounting_date: The accounting date
        :param has_tax: If any taxes are involved in the lines of the invoice
        :param tax_date: The tax date to be checked against the tax lock date
        :return: a list of tuples containing the lock dates ordered chronologically.
        
        """
        self.ensure_one()
        locks = []
    
        user_lock_date = self._get_user_fiscal_lock_date()
        if accounting_date and user_lock_date and accounting_date <= user_lock_date:
            locks.append((user_lock_date, _('user')))
    
        tax_lock_date = self.max_tax_lock_date
        if tax_lock_date and has_tax:
            # Si hay un tax_date, lo comparamos en lugar del accounting_date
            date_to_check = tax_date if tax_date else accounting_date
            if date_to_check and date_to_check <= tax_lock_date:
                locks.append((tax_lock_date, _('tax')))
    
        locks.sort()
        return locks