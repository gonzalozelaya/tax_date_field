from odoo import models, api, fields, Command, _
from odoo.tools import format_date
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)
class AccountMove(models.Model):
    _inherit = 'account.move'

    tax_date = fields.Date(
        string='Fecha Impositiva',
        index=True,
        compute='_compute_tax_date', store=True, required=True, readonly=False, precompute=True,
        copy=False,
        tracking=True,
    )

    def _get_tax_date(self, invoice_date, has_tax):
        lock_dates = self._get_violated_lock_dates(invoice_date, True)
        today = fields.Date.context_today(self)
        if lock_dates:
            # Check if any of the lock dates is a tax lock date
            if any(lock_type == 'tax' for _, lock_type in lock_dates):
                # Get the first tax lock date (if multiple exist)
                tax_lock_date = next((date for date, lock_type in lock_dates if lock_type == 'tax'), None)
                if tax_lock_date:
                    invoice_date = tax_lock_date + timedelta(days=1)
        if self.is_sale_document(include_receipts=True):
            if lock_dates:
                if not highest_name or number_reset == 'month':
                    return min(today, date_utils.get_month(invoice_date)[1])
                elif number_reset == 'year':
                    return min(today, date_utils.end_of(invoice_date, 'year'))
        return invoice_date
    
    def _get_accounting_date(self, invoice_date, has_tax):
        """Get correct accounting date for previous periods, taking tax lock date into account.
        When registering an invoice in the past, we still want the sequence to be increasing.
        We then take the last day of the period, depending on the sequence format.

        If there is a tax lock date and there are taxes involved, we register the invoice at the
        last date of the first open period.
        :param invoice_date (datetime.date): The invoice date
        :param has_tax (bool): Iff any taxes are involved in the lines of the invoice
        :return (datetime.date):
        """
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
        today = fields.Date.context_today(self)
        highest_name = self.highest_name or self._get_last_sequence(relaxed=True)
        number_reset = self._deduce_sequence_number_reset(highest_name)
        if lock_dates:
            # Check if any of the lock dates is a tax lock date
            if any(lock_type == 'user' for _, lock_type in lock_dates):
                # Get the first tax lock date (if multiple exist)
                user_lock_date = next((date for date, lock_type in lock_dates if lock_type == 'user'), None)
                if user_lock_date:
                    invoice_date = user_lock_date + timedelta(days=1)
        if self.is_sale_document(include_receipts=True):
            if lock_dates:
                if not highest_name or number_reset == 'month':
                    return min(today, date_utils.get_month(invoice_date)[1])
                elif number_reset == 'year':
                    return min(today, date_utils.end_of(invoice_date, 'year'))
        return invoice_date

    
    @api.depends('invoice_date', 'company_id')  # Añadir 'date' a los depends
    def _compute_tax_date(self):
        for move in self:
            # Primero intentamos con invoice_date, si no existe usamos date
            source_date = move.invoice_date or move.date
            if not source_date:
                if not move.tax_date:
                    move.tax_date = fields.Date.context_today(self)
                continue
                
            accounting_date = source_date
            if not move.is_sale_document(include_receipts=True):
                accounting_date = move._get_tax_date(source_date, move._affect_tax_report())
                
            if accounting_date and accounting_date != move.tax_date:
                move.tax_date = accounting_date
                # _affect_tax_report may trigger premature recompute of line_ids.date
                self.env.add_to_compute(move.line_ids._fields['tax_date'], move.line_ids)
                # might be protected because `_get_accounting_date` requires the `name`
                self.env.add_to_compute(self._fields['name'], move)

    def _get_violated_lock_dates(self, invoice_date, has_tax):
        """Get all the lock dates affecting the current invoice_date.
        :param invoice_date: The invoice date
        :param has_tax: If any taxes are involved in the lines of the invoice
        :return: a list of tuples containing the lock dates affecting this move, ordered chronologically.
        """
        return self.company_id._get_violated_lock_dates(invoice_date, has_tax,self.invoice_date)

    def _get_lock_date_message(self, invoice_date, has_tax, tax_date=None):
        """Get a message describing the latest lock date affecting the specified date.
        :param invoice_date: The date to be checked
        :param has_tax: If any taxes are involved in the lines of the invoice
        :param tax_date: The tax date to be verified against the lock date
        :return: a message describing the latest lock date affecting this move and the date it will be
                 accounted on if posted, or False if no lock dates affect this move.
        """
        lock_dates = self._get_violated_lock_dates(invoice_date, has_tax)
    
        # Si no hay fechas de bloqueo, no hay mensaje
        if not lock_dates:
            return False
    
        # Obtiene la última fecha de bloqueo aplicable
        lock_date, lock_type = lock_dates[-1]
    
    
        # Si el único lock_date es 'impuesto', debe compararse con tax_date
        if lock_type == 'impuesto':
            if not self.tax_date or self.tax_date > lock_date:
                return False  # No hay problema si tax_date no está bloqueado
            invoice_date = self._get_tax_date(self.tax_date, has_tax)
        else:
            invoice_date = self._get_accounting_date(invoice_date, has_tax)
    
        tax_lock_date_message = _(
            "La fecha es antes del bloqueo al %(lock_date)s. "
            "Las fechas contables se moveran automaticamente a un dia posterior al bloqueo correspondiente.",
            #lock_type=lock_type,
            lock_date=format_date(self.env, lock_date),
            invoice_date=format_date(self.env, invoice_date)
        )
    
        return tax_lock_date_message


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    tax_date = fields.Date(
        related='move_id.tax_date', store=True,
        copy=False,
        group_operator='min',
    )

    def _check_tax_lock_date(self):
        for line in self.filtered(lambda l: l.move_id.state == 'posted'):
            move = line.move_id
            if self.env.user.has_group('account.group_account_manager'):
                continue
            if move.company_id.max_tax_lock_date and move.tax_date <= move.company_id.max_tax_lock_date and line._affect_tax_report():
                raise UserError(_("La operación ha fallado ya que afectara impuestos que ya han sido bloqueados. "
                                  "Por favor cambie la fecha impositiva o la fecha de bloqueo (%s) para continuar.",
                                  format_date(self.env, move.company_id.max_tax_lock_date)))




    