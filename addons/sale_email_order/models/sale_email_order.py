import json
import math
import re
import time

import requests

from .strong_backend import extract as extract_strong

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import email_normalize, html2plaintext

OLLAMA_TIMEOUT = 60
DEFAULT_OLLAMA_URL = 'http://localhost:11434'
DEFAULT_OLLAMA_MODEL = 'qwen2.5:1.5b'

SYSTEM_PROMPT = """You classify B2B purchase emails and extract the ordered products.
Answer with ONE JSON object only, no other text, using exactly this format:
{"category": "standard" | "complex" | "quote", "confidence": <number 0-1>, "lines": [{"product": "<product reference or name>", "quantity": <number>}]}
Categories:
- standard: clear products and quantities, no special conditions.
- complex: ambiguous products, custom pricing or several delivery addresses.
- quote: the customer only asks for a price or an offer.
confidence is your probability that the category and lines are correct.
Use an empty "lines" list when no product can be identified."""

FEW_SHOT = [
    {'role': 'user', 'content': "Hello, please send us 10 x FURN_7800 Desk Combination and 5 x Office Chair. Thanks, Mark"},
    {'role': 'assistant', 'content': '{"category": "standard", "confidence": 0.95, "lines": [{"product": "FURN_7800", "quantity": 10}, {"product": "Office Chair", "quantity": 5}]}'},
    {'role': 'user', 'content': "Hi, we need some of those large desks, half shipped to Paris and half to Brussels, at last year's price."},
    {'role': 'assistant', 'content': '{"category": "complex", "confidence": 0.9, "lines": []}'},
    {'role': 'user', 'content': "Could you tell me your price for 200 storage boxes?"},
    {'role': 'assistant', 'content': '{"category": "quote", "confidence": 0.9, "lines": [{"product": "Storage Box", "quantity": 200}]}'},
]


class SaleEmailOrder(models.Model):
    _name = 'sale.email.order'
    _description = "Email Order Request"
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(string="Subject", required=True, default=lambda self: self.env._("No Subject"))
    email_from = fields.Char()
    partner_id = fields.Many2one('res.partner', string="Customer")
    body = fields.Text()
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    state = fields.Selection(
        selection=[
            ('new', "New"),
            ('done', "Order Created"),
            ('review', "To Review"),
        ],
        default='new',
        required=True,
        tracking=True,
    )
    category = fields.Selection(
        selection=[
            ('standard', "Standard"),
            ('complex', "Complex"),
            ('quote', "Quote Request"),
        ],
    )
    confidence = fields.Float(digits=(3, 2))
    confidence_source = fields.Selection(
        selection=[
            ('model', "Model Estimate"),
            ('logprobs', "Token Probability"),
        ],
    )
    processing_time = fields.Float(string="Processing Time (s)", digits=(16, 2))
    ai_response = fields.Text(string="AI Response", readonly=True)
    inference_trace = fields.Json(string="Inference trace", readonly=True, copy=False)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", readonly=True)
    review_reason = fields.Char(readonly=True)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        defaults = {
            'name': msg_dict.get('subject') or self.env._("No Subject"),
            'email_from': msg_dict.get('from'),
            'partner_id': msg_dict.get('author_id'),
            'body': html2plaintext(msg_dict.get('body') or ''),
            **(custom_values or {}),
        }
        request = super().message_new(msg_dict, custom_values=defaults)
        self.env.ref('sale_email_order.ir_cron_process_email_orders').sudo()._trigger()
        return request

    def action_process(self):
        self.filtered(lambda r: r.state != 'done').state = 'new'
        self.env.ref('sale_email_order.ir_cron_process_email_orders').sudo()._trigger()

    @api.model
    def _cron_process(self):
        requests_todo = self.search([('state', '=', 'new')], order='id')
        self.env['ir.cron']._commit_progress(remaining=len(requests_todo))
        for request in requests_todo:
            request.with_company(request.company_id)._process()
            if not self.env['ir.cron']._commit_progress(1):
                break

    def _process(self):
        """Classify the email with the small model, then create the order or send it to review."""
        self.ensure_one()
        start, response = time.time(), False
        params = self.env['ir.config_parameter'].sudo()
        mode = params.get_param('sale_email_order.strategy', 'small')
        threshold = float(params.get_param('sale_email_order.confidence_threshold', 0.8))
        path = []
        trace = {'strategy': mode, 'accept_threshold': threshold}
        try:
            if mode != 'strong':
                path.append('Qwen')
                response, logprobs = self._call_ollama()
                result = self._parse_ai_response(response, logprobs)
                trace['small_candidate'] = result.copy()
            kev_escalate = False
            if mode == 'kev':
                path.append('Kev')
                checks = self._kev_check(result)
                cutoff = float(params.get_param('sale_email_order.kev_threshold', 0.5))
                trace.update(kev_checks=checks, kev_error_threshold=cutoff)
                kev_escalate = max(checks.values()) >= cutoff
                self.message_post(body=self.env._("Kev verification: %s", json.dumps(checks)))
            if mode == 'strong' or kev_escalate or (mode == 'confidence' and result['confidence'] < threshold):
                path.append('GPT-6.2 Sol')
                response, metadata = extract_strong(self._extraction_messages())
                trace['strong_call'] = metadata
                result = self._parse_ai_response(response)
                self.message_post(body=self.env._("Strong extraction: %s", json.dumps(metadata)))
        except (requests.RequestException, ValueError, TypeError, KeyError) as error:
            result = {'error': error}
        self.write({
            'inference_trace': dict(trace, path=path),
            'ai_response': response,
            'category': result.get('category'),
            'confidence': result.get('confidence', 0.0),
            'confidence_source': result.get('confidence_source'),
            'processing_time': time.time() - start,
            'review_reason': False,
        })
        self.message_post(body=self.env._("Extraction path: %s", ' → '.join(path)))
        if 'error' in result:
            return self._to_review(self.env._("AI call failed: %s", result['error']))
        if self.category != 'standard':
            return self._to_review(self.env._("Classified as %s.", self.category))
        if self.confidence < threshold:
            return self._to_review(self.env._("Confidence %(confidence).2f is below threshold %(threshold).2f.",
                                              confidence=self.confidence, threshold=threshold))
        if not self.partner_id and self.email_from:
            # Only gateway emails get the sender as author: imported records or contacts created later need a lookup.
            self.partner_id = self.env['res.partner'].search([('email_normalized', '=', email_normalize(self.email_from))], limit=1)
        if not self.partner_id:
            return self._to_review(self.env._("No customer found for %s.", self.email_from))
        if not result['lines']:
            return self._to_review(self.env._("No product found in the email."))

        order_lines = []
        for line in result['lines']:
            product = self._find_product(line['product'])
            if not product:
                return self._to_review(self.env._("Product '%s' not found or ambiguous.", line['product']))
            order_lines.append(fields.Command.create({'product_id': product.id, 'product_uom_qty': line['quantity']}))
        try:
            with self.env.cr.savepoint():
                self.sale_order_id = self.env['sale.order'].create({
                    'partner_id': self.partner_id.id,
                    'company_id': self.company_id.id,
                    'origin': self.name,
                    'order_line': order_lines,
                })
        except UserError as error:
            return self._to_review(self.env._("Order creation failed: %s", error))
        self.state = 'done'
        self.message_post(body=self.env._("Quotation %s created automatically.", self.sale_order_id._get_html_link()))

    def _to_review(self, reason):
        self.write({'state': 'review', 'review_reason': reason})
        self.message_post(body=self.env._("Sent to review: %s", reason))

    def action_generate_report(self):
        return self.env.ref('sale_email_order.email_order_decision_report').report_action(self)

    def _kev_check(self, candidate):
        url = self.env['ir.config_parameter'].sudo().get_param(
            'sale_email_order.kev_url', 'http://host.docker.internal:8008')
        rules = {
            'category': 'Is the proposed category inconsistent with the current customer request?',
            'product': 'Is any currently requested product missing, substituted, or included only from a quotation, cancellation or signature?',
            'quantity': 'Does any proposed quantity disagree with the final amount requested for that product?',
        }
        state = {'email': self.body or self.name, 'category': candidate['category'], 'lines': candidate['lines'],
                 'category_guide': 'standard: clear order; complex: ambiguous or special conditions; quote: price inquiry'}
        reply = requests.post(url.rstrip('/') + '/v1/systemone', timeout=60, json={
            'model': 'kev-latest', 'state': json.dumps(state, ensure_ascii=False),
            'questions': {k: {'type': 'noul', 'instructions': v} for k, v in rules.items()}})
        reply.raise_for_status()
        answers = reply.json()['answers']
        checks = {k: float(answers[k]['noul']) for k in rules}
        if not all(0 <= x <= 1 for x in checks.values()):
            raise ValueError('Invalid Kev probability')
        return checks

    def _extraction_messages(self):
        return [{'role': 'system', 'content': SYSTEM_PROMPT}, *FEW_SHOT,
                {'role': 'user', 'content': self.body or self.name}]

    def _call_ollama(self):
        params = self.env['ir.config_parameter'].sudo()
        url = params.get_param('sale_email_order.ollama_url', DEFAULT_OLLAMA_URL)
        response = requests.post(f"{url.rstrip('/')}/api/chat", timeout=OLLAMA_TIMEOUT, json={
            'model': params.get_param('sale_email_order.ollama_model', DEFAULT_OLLAMA_MODEL),
            'stream': False,
            'logprobs': params.get_param('sale_email_order.use_logprobs') == 'True',
            'format': 'json',
            'options': {'temperature': 0},
            'messages': self._extraction_messages(),
        })
        response.raise_for_status()
        data = response.json()
        return data['message']['content'], data.get('logprobs')

    @api.model
    def _parse_ai_response(self, text, logprobs=None):
        """Extract and validate the JSON object; raise ValueError/TypeError when the answer is malformed."""
        start, end = text.find('{'), text.rfind('}')
        if start == -1 or end < start:
            raise ValueError(self.env._("No JSON object in the response."))
        data = json.loads(text[start:end + 1])
        if data.get('category') not in dict(self._fields['category'].selection):
            raise ValueError(self.env._("Unknown category '%s'.", data.get('category')))
        lines = [
            {'product': str(line['product']).strip(), 'quantity': float(line.get('quantity') or 0)}
            for line in data.get('lines') or []
            if isinstance(line, dict) and line.get('product')
        ]
        token_confidence = self._logprob_confidence(text, logprobs)
        return {
            'category': data['category'],
            'confidence': min(max(float(data.get('confidence') or 0), 0.0), 1.0) if token_confidence is None else token_confidence,
            'confidence_source': 'model' if token_confidence is None else 'logprobs',
            'lines': [line for line in lines if line['quantity'] > 0],
        }

    @api.model
    def _logprob_confidence(self, text, logprobs):
        """Probability of the token starting the category value, None if unavailable.

        The categories start with different letters, so this token is where the model picks the category.
        """
        match = re.search(r'"category"\s*:\s*"', text)
        built = ''
        for token in (logprobs or []) if match else []:
            built += token['token']
            if len(built) > match.end():
                # Only the text up to the category must match: later non-ASCII may come as partial byte tokens.
                return math.exp(token['logprob']) if text.startswith(built) else None
        return None

    def _find_product(self, reference):
        """Return the single sellable product matching the reference or name, else an empty recordset."""
        Product = self.env['product.product']
        domain = [('sale_ok', '=', True), ('company_id', 'in', [False, self.company_id.id])]
        product = (Product.search(domain + [('default_code', '=ilike', reference)], limit=1)
                   or Product.search(domain + [('name', 'ilike', reference)], limit=2))
        return product if len(product) == 1 else Product
