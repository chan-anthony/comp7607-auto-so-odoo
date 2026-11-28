{
    "name": "Sale Email Order",
    "summary": """Turn inbound order emails into draft quotations and triage non-orders with local-first AI""",
    "category": "Sales/Sales",
    "version": "19.0.1.0.0",
    "author": "Anthony Chan and Isidore Chan",
    "depends": [
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rules.xml",
        "data/ir_cron_data.xml",
        "data/mail_alias_data.xml",
        "views/sale_email_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
}
