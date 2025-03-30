from odoo import models, api, fields, Command, _
from odoo.tools import format_date
from odoo.exceptions import UserError
import datetime
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

    @api.depends('invoice_date', 'date', 'company_id')  # Añadir 'date' a los depends
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
                accounting_date = move._get_accounting_date(source_date, move._affect_tax_report())
                
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
        return self.company_id._get_violated_lock_dates(invoice_date, has_tax,self.tax_date)

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
            invoice_date = self._get_accounting_date(self.tax_date, has_tax)
        else:
            invoice_date = self._get_accounting_date(invoice_date, has_tax)
    
        tax_lock_date_message = _(
            "The date is being set prior to the %(lock_type)s lock date %(lock_date)s. "
            "The Journal Entry will be accounted on %(invoice_date)s upon posting.",
            lock_type=lock_type,
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
            if move.company_id.max_tax_lock_date and move.tax_date <= move.company_id.max_tax_lock_date and line._affect_tax_report():
                raise UserError(_("La operación ha fallado ya que afectara impuestos que ya han sido bloqueados. "
                                  "Por favor cambie la fecha impositiva o la fecha de bloqueo (%s) para continuar.",
                                  format_date(self.env, move.company_id.max_tax_lock_date)))




    