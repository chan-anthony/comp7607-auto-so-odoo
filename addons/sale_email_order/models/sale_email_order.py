import json
import math
import re
import time

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

OLLAMA_TIMEOUT = 60

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
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", readonly=True)

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
        try:
            response, logprobs = self._call_ollama()
            result = self._parse_ai_response(response, logprobs)
        except (requests.RequestException, ValueError, TypeError, KeyError) as error:
            result = {'error': error}
        self.write({
            'ai_response': response,
            'category': result.get('category'),
            'confidence': result.get('confidence', 0.0),
            'confidence_source': result.get('confidence_source'),
            'processing_time': time.time() - start,
        })
        threshold = float(self.env['ir.config_parameter'].sudo().get_param('sale_email_order.confidence_threshold', 0.8))
        if 'error' in result:
            return self._to_review(self.env._("AI call failed: %s", result['error']))
        if self.category != 'standard':
            return self._to_review(self.env._("Classified as %s.", self.category))
        if self.confidence < threshold:
            return self._to_review(self.env._("Confidence %(confidence).2f is below threshold %(threshold).2f.",
                                              confidence=self.confidence, threshold=threshold))
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
        self.state = 'review'
        self.message_post(body=self.env._("Sent to review: %s", reason))

    def _call_ollama(self):
        params = self.env['ir.config_parameter'].sudo()
        url = params.get_param('sale_email_order.ollama_url', 'http://localhost:11434')
        response = requests.post(f"{url.rstrip('/')}/api/chat", timeout=OLLAMA_TIMEOUT, json={
            'model': params.get_param('sale_email_order.ollama_model', 'qwen2.5:1.5b'),
            'stream': False,
            'logprobs': params.get_param('sale_email_order.use_logprobs') == 'True',
            'format': 'json',
            'options': {'temperature': 0},
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                *FEW_SHOT,
                {'role': 'user', 'content': self.body or self.name},
            ],
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
        if not match or not logprobs or ''.join(token['token'] for token in logprobs) != text:
            return None
        end = 0
        for token in logprobs:
            end += len(token['token'])
            if end > match.end():
                return math.exp(token['logprob'])
        return None

    def _find_product(self, reference):
        """Return the single sellable product matching the reference or name, else an empty recordset."""
        Product = self.env['product.product']
        domain = [('sale_ok', '=', True), ('company_id', 'in', [False, self.company_id.id])]
        product = (Product.search(domain + [('default_code', '=ilike', reference)], limit=1)
                   or Product.search(domain + [('name', 'ilike', reference)], limit=2))
        return product if len(product) == 1 else Product
