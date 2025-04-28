from odoo import fields, models, api, _, Command
from datetime import timedelta, datetime, date

import logging

_logger = logging.getLogger(__name__)
class ResCompany(models.Model):
    _inherit = "res.company"

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
        if tax_lock_date and user_lock_date and has_tax and tax_lock_date <= user_lock_date:
            # Si hay un tax_date, lo comparamos en lugar del accounting_date
            date_to_check = tax_date if tax_date else accounting_date
            if date_to_check and date_to_check <= tax_lock_date:
                locks.append((tax_lock_date, _('tax')))
    
        locks.sort()
        return locks
