from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_order_ollama_url = fields.Char(
        string="Ollama URL",
        config_parameter='sale_email_order.ollama_url',
        default='http://localhost:11434',
    )
    email_order_ollama_model = fields.Char(
        string="Small Model",
        config_parameter='sale_email_order.ollama_model',
        default='qwen2.5:1.5b',
    )
    email_order_confidence_threshold = fields.Float(
        string="Confidence Threshold",
        config_parameter='sale_email_order.confidence_threshold',
        default=0.8,
        help="Emails classified below this confidence are sent to the review queue instead of creating an order.",
    )
    email_order_use_logprobs = fields.Boolean(
        string="Use Token Probabilities",
        config_parameter='sale_email_order.use_logprobs',
        help="Use the model's token probability (logprobs) for the category as confidence instead of its self-reported estimate.",
    )
