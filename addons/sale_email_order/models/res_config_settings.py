import json

import requests

from odoo import api, fields, models

from .sale_email_order import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_order_strategy = fields.Selection(
        [('small', 'Qwen only'), ('strong', 'GPT-6.2 Sol only'),
         ('confidence', 'Qwen with confidence handoff'), ('kev', 'Qwen with Kev verification'), ('hybrid_risk','Local-first: calibrated risk'), ('hybrid_20','Local-first: 20% calibration budget'), ('hybrid_30','Local-first: 30% calibration budget'), ('hybrid_guard30','Local-first: guarded 30% calibration budget'), ('authority_risk','Current sender: risk target'), ('authority_20','Current sender: 20% budget'), ('authority_30','Current sender: 30% budget')],
        string='Extraction strategy', default='small',
        config_parameter='sale_email_order.strategy',
    )
    email_order_kev_url = fields.Char(string='Kev server', default='http://host.docker.internal:8008',
                                      config_parameter='sale_email_order.kev_url')
    email_order_kev_threshold = fields.Float(string='Kev error threshold', default=0.5,
                                              config_parameter='sale_email_order.kev_threshold')

    email_order_ollama_url = fields.Char(
        string="Ollama URL",
        config_parameter='sale_email_order.ollama_url',
        default=DEFAULT_OLLAMA_URL,
    )
    email_order_ollama_model = fields.Selection(
        selection='_get_ollama_model_selection',
        string="Small Model",
        config_parameter='sale_email_order.ollama_model',
        default=DEFAULT_OLLAMA_MODEL,
        help="Models found on the Ollama server by 'Test Connection', smallest first.",
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

    @api.model
    def _get_ollama_model_selection(self):
        """Models saved by the last connection test, plus the current model so its value stays valid."""
        params = self.env['ir.config_parameter'].sudo()
        selection = [tuple(option) for option in json.loads(params.get_param('sale_email_order.ollama_models') or '[]')]
        current = params.get_param('sale_email_order.ollama_model', DEFAULT_OLLAMA_MODEL)
        return selection if current in dict(selection) else [*selection, (current, current)]

    def action_test_ollama_connection(self):
        """List the models of the Ollama server, save them as Small Model options and reload the settings."""
        self.ensure_one()
        try:
            response = requests.get(f"{(self.email_order_ollama_url or '').rstrip('/')}/api/tags", timeout=10)
            response.raise_for_status()
            ollama_models = sorted(response.json()['models'], key=lambda model: model.get('size') or 0)
            selection = [
                (model['name'], f"{model['name']} ({size})" if (size := (model.get('details') or {}).get('parameter_size')) else model['name'])
                for model in ollama_models
            ]
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            return self._ollama_notification('danger', self.env._("Connection to Ollama failed: %s", error))
        if not selection:
            return self._ollama_notification('warning', self.env._("Connected, but no model is installed. Run 'ollama pull <model>' on the server."))
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('sale_email_order.ollama_url', self.email_order_ollama_url)
        params.set_param('sale_email_order.ollama_models', json.dumps(selection))
        return self._ollama_notification('success', self.env._("Connected: %s model(s) found.", len(selection)),
                                         next_action={'type': 'ir.actions.client', 'tag': 'reload'})

    def _ollama_notification(self, notification_type, message, next_action=None):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'type': notification_type, 'message': message, 'next': next_action},
        }
