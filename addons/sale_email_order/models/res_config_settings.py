import json

import requests

from odoo import api, fields, models

from .sale_email_order import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    email_order_strategy = fields.Selection(
        [('small', 'Qwen only'), ('strong', 'GPT-6.2 Sol only'), ('fallback', 'Qwen with cloud fallback'),
         ('local_first', 'Local-first risk gate'), ('current_sender', 'Current-sender authorization'),
         ('per_line', 'Per-line authorization')],
        string='Extraction strategy', default='small', config_parameter='sale_email_order.strategy',
    )
    email_order_fallback_check = fields.Selection(
        [('confidence', 'Confidence below threshold'), ('kev', 'Kev verification')],
        string='Send to cloud when', default='confidence', config_parameter='sale_email_order.fallback_check',
    )
    email_order_risk_budget = fields.Selection(
        [('risk', 'Lowest risk'), ('0.2', 'About 20% to cloud'), ('0.3', 'About 30% to cloud')],
        string='Risk budget', default='risk', config_parameter='sale_email_order.risk_budget',
        help="Calibrated operating point: how many emails the risk gate may send to the cloud model.",
    )
    email_order_local_guard = fields.Boolean(
        string='Local guard', config_parameter='sale_email_order.local_guard',
        help="Before calling any model, send fake system instructions and questions about old orders to review.",
    )
    email_order_scoped_draft = fields.Boolean(
        string='Draft short clear orders locally', config_parameter='sale_email_order.scoped_draft',
        help="Draft a short root instruction such as 'Please ship 3 FURN_7800' locally when it fully explains the order.",
    )
    email_order_sort_nonorders = fields.Boolean(
        string='Sort non-orders', config_parameter='sale_email_order.sort_nonorders',
        help="Archive emails that need no work, link emails to an open case of the same sender, "
             "and flag orders that still ask a question.",
    )
    email_order_followup_model = fields.Boolean(
        string='Check orders for extra questions with the small model', config_parameter='sale_email_order.followup_model',
        help="For each drafted order, ask the small model whether the sender also asks for something else. "
             "It can only add a Human follow-up flag, never remove one.",
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
