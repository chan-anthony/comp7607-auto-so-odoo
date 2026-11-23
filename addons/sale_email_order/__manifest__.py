{
    "name": "sale_email_order",
    "summary": """Turn inbound order emails into sales orders with a small local AI model (Ollama)""",
    "version": "19.0.1.0.0",
    "author": "Odoo PS",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",

        "data/ir_cron_data.xml",
        "data/mail_alias_data.xml",

        "views/sale_email_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
}
