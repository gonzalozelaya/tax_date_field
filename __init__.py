# -*- coding: utf-8 -*-

from . import models

import logging

_logger = logging.getLogger(__name__)
def populate_tax_date(env):
    
    AccountMove = env['account.move']
    # Buscar movimientos sin tax_date
    moves = AccountMove.search([])
    
    _logger.info(f"Actualizando tax_date para {len(moves)} movimientos contables")
    
    for move in moves:
        # Reutilizar la lógica del compute
        source_date = move.invoice_date or move.date
        if not source_date:
            continue
        
        move.tax_date = source_date
    
    _logger.info("Actualización de tax_date completada")