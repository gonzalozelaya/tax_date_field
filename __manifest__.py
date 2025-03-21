# -*- coding: utf-8 -*-
{
    'name': "Añadir fecha impositiva en factura",

    'summary': """
        Añade el campo fecha impositiva en la factura""",

    'description': """
        Añade el campo fecha impositiva en la factura 
    """,

    'author': "OutsourceArg",
    'website': "https://www.outsourcearg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['account'],
    'data':[
        'views/account_move_views.xml',
    ]
}