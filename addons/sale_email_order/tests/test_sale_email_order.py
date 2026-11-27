import math
from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.sale_email_order.models.sale_email_order import SaleEmailOrder

STANDARD = '{"category": "standard", "confidence": 0.95, "lines": [{"product": "furn_7800", "quantity": 3}]}'


@tagged('post_install', '-at_install')
class TestSaleEmailOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Mark', 'email': 'mark@example.com'})
        cls.desk = cls.env['product.product'].create({'name': 'Desk Combination', 'default_code': 'FURN_7800'})
        cls.env['product.product'].create([{'name': 'Office Chair Black'}, {'name': 'Office Chair White'}])
        cls.env['ir.config_parameter'].set_param('sale_email_order.confidence_threshold', 0.8)

    def _process(self, answer, logprobs=None, **vals):
        request = self.env['sale.email.order'].create({'name': 'Order', 'partner_id': self.partner.id, 'body': 'x', **vals})
        result = answer if isinstance(answer, Exception) else (answer, logprobs)
        with patch.object(SaleEmailOrder, '_call_ollama', side_effect=[result]):  # raises if result is an exception
            request._process()
        return request

    def test_standard_order_created(self):
        request = self._process(f"```json\n{STANDARD}\n```")
        self.assertRecordValues(request, [{'state': 'done', 'category': 'standard', 'confidence': 0.95, 'confidence_source': 'model'}])
        self.assertRecordValues(request.sale_order_id, [{'partner_id': self.partner.id, 'origin': 'Order'}])
        self.assertRecordValues(request.sale_order_id.order_line, [{'product_id': self.desk.id, 'product_uom_qty': 3}])

    def test_threshold_boundary(self):
        for confidence, state in ((1.0, 'done'), (0.8, 'done'), (0.79, 'review'), (0.0, 'review')):
            with self.subTest(confidence=confidence):
                answer = f'{{"category": "standard", "confidence": {confidence}, "lines": [{{"product": "FURN_7800", "quantity": 1}}]}}'
                self.assertEqual(self._process(answer).state, state)

    def test_confidence_handoff_replaces_lines_before_creating_draft(self):
        self.env['ir.config_parameter'].set_param('sale_email_order.strategy', 'confidence')
        cheap = STANDARD.replace('0.95', '0.45').replace('"quantity": 3', '"quantity": 12')
        with patch('odoo.addons.sale_email_order.models.sale_email_order.extract_strong',
                   return_value=(STANDARD, {})) as strong:
            request = self._process(cheap)
            strong.assert_called_once()
            self.assertRecordValues(request.sale_order_id.order_line, [{'product_uom_qty': 3}])
            self.assertEqual(request.sale_order_id.state, 'draft')
            self._process(STANDARD)
            self.assertEqual(strong.call_count, 1)

    def test_strong_failure_does_not_create_order(self):
        self.env['ir.config_parameter'].set_param('sale_email_order.strategy', 'strong')
        with patch('odoo.addons.sale_email_order.models.sale_email_order.extract_strong',
                   side_effect=ValueError('OpenAI extraction connection failed')):
            request = self._process(AssertionError('strong-only must not call Ollama'))
            self.assertRecordValues(request, [{'state': 'review', 'sale_order_id': False}])

    def test_customer_found_from_email(self):
        # Imported record (no gateway author): the customer is looked up from the sender address.
        request = self._process(STANDARD, partner_id=False, email_from='"Mark" <MARK@example.com>')
        self.assertRecordValues(request, [{'state': 'done', 'partner_id': self.partner.id, 'review_reason': False}])
        # Unknown sender goes to review; once the contact exists, processing again creates the order.
        request = self._process(STANDARD, partner_id=False, email_from='jane@example.com')
        self.assertRecordValues(request, [{'state': 'review', 'review_reason': 'No customer found for jane@example.com.'}])
        jane = self.env['res.partner'].create({'name': 'Jane', 'email': 'jane@example.com'})
        with patch.object(SaleEmailOrder, '_call_ollama', return_value=(STANDARD, None)):
            request._process()
        self.assertRecordValues(request, [{'state': 'done', 'partner_id': jane.id, 'review_reason': False}])

    def test_sent_to_review(self):
        cases = {
            'low confidence': ('{"category": "standard", "confidence": 0.4, "lines": [{"product": "FURN_7800", "quantity": 1}]}', {}),
            'quote': ('{"category": "quote", "confidence": 0.9, "lines": []}', {}),
            'no customer': (STANDARD, {'partner_id': False}),
            'no lines': ('{"category": "standard", "confidence": 0.9, "lines": []}', {}),
            'unknown product': ('{"category": "standard", "confidence": 0.9, "lines": [{"product": "Spaceship", "quantity": 1}]}', {}),
            'ambiguous product': ('{"category": "standard", "confidence": 0.9, "lines": [{"product": "Office Chair", "quantity": 1}]}', {}),
        }
        for case, (answer, vals) in cases.items():
            with self.subTest(case=case):
                request = self._process(answer, **vals)
                self.assertRecordValues(request, [{'state': 'review', 'sale_order_id': False}])

    def test_malformed_answer_goes_to_review(self):
        cases = {
            'no json': 'Sorry, I cannot help.',
            'invalid json': '{"category": "standard",',
            'unknown category': '{"category": "spam", "confidence": 0.9}',
            'bad quantity': '{"category": "standard", "confidence": 0.9, "lines": [{"product": "FURN_7800", "quantity": "many"}]}',
            'connection error': requests.ConnectionError("refused"),
        }
        for case, answer in cases.items():
            with self.subTest(case=case):
                request = self._process(answer)
                self.assertRecordValues(request, [{'state': 'review', 'category': False, 'confidence': 0.0}])
                self.assertIn("AI call failed", request.message_ids[0].body)

    def test_reprocess_clears_previous_result(self):
        request = self._process('{"category": "quote", "confidence": 0.9, "lines": []}')
        with patch.object(SaleEmailOrder, '_call_ollama', side_effect=requests.Timeout()):
            request._process()
        self.assertRecordValues(request, [{'state': 'review', 'category': False, 'ai_response': False}])

    def test_order_creation_error_goes_to_review(self):
        with patch.object(type(self.env['sale.order']), 'create', side_effect=UserError("Blocked")):
            request = self._process(STANDARD)
        self.assertRecordValues(request, [{'state': 'review', 'sale_order_id': False}])

    def test_call_ollama_payload(self):
        self.env['ir.config_parameter'].set_param('sale_email_order.ollama_url', 'http://ollama:11434/')
        self.env['ir.config_parameter'].set_param('sale_email_order.ollama_model', 'tiny')
        request = self.env['sale.email.order'].create({'name': 'Order', 'body': 'Send 3 desks'})
        with patch.object(requests, 'post') as post:
            post.return_value.json.return_value = {'message': {'content': STANDARD}}
            self.assertEqual(request._call_ollama(), (STANDARD, None))
            self.env['ir.config_parameter'].set_param('sale_email_order.use_logprobs', True)
            request._call_ollama()
        url, payload = post.call_args.args[0], post.call_args.kwargs['json']
        self.assertEqual(url, 'http://ollama:11434/api/chat')
        self.assertEqual((payload['model'], payload['format'], payload['messages'][-1]['content']), ('tiny', 'json', 'Send 3 desks'))
        self.assertEqual([call.kwargs['json']['logprobs'] for call in post.call_args_list], [False, True])

    def test_logprobs_confidence(self):
        answer = '{"category": "standard", "confidence": 0.99, "lines": [{"product": "FURN_7800", "quantity": 1}]}'
        prefix = '{"category": "'

        def tokens(decision_logprob, first=prefix, rest=answer[len(prefix) + 5:]):
            # Split like a tokenizer would: the prefix, the token where the category is picked, then the rest.
            return [{'token': first, 'logprob': 0.0}, {'token': 'stand', 'logprob': decision_logprob}, {'token': rest, 'logprob': 0.0}]

        request = self._process(answer, tokens(math.log(0.9)))
        self.assertRecordValues(request, [{'state': 'done', 'confidence': 0.9, 'confidence_source': 'logprobs'}])
        request = self._process(answer, tokens(math.log(0.55)))
        self.assertRecordValues(request, [{'state': 'review', 'confidence': 0.55, 'confidence_source': 'logprobs'}])
        # Non-ASCII after the category is split into byte tokens that do not rebuild the text: still usable.
        request = self._process(answer, tokens(math.log(0.55), rest=answer[len(prefix) + 5:].replace('FURN', 'F\ufffd\ufffdRN')))
        self.assertRecordValues(request, [{'confidence': 0.55, 'confidence_source': 'logprobs'}])
        # Tokens that do not rebuild the text up to the category cannot be trusted: fall back to the model estimate.
        for broken in (tokens(math.log(0.55), first='{"kategorie": "'), tokens(math.log(0.55))[:1]):
            request = self._process(answer, broken)
            self.assertRecordValues(request, [{'state': 'done', 'confidence': 0.99, 'confidence_source': 'model'}])

    def test_gateway_queues_and_cron_processes(self):
        email = (
            "From: Mark <mark@example.com>\nTo: orders@example.com\nSubject: New order\n"
            "Message-ID: <order-1@example.com>\nContent-Type: text/html\n\n<p>Please send 3 x FURN_7800.</p>"
        )
        request = self.env['sale.email.order'].browse(self.env['mail.thread'].message_process('sale.email.order', email))
        self.assertRecordValues(request, [{'state': 'new', 'partner_id': self.partner.id, 'name': 'New order'}])
        self.assertEqual(request.body.strip(), 'Please send 3 x FURN_7800.')
        with patch.object(SaleEmailOrder, '_call_ollama', return_value=(STANDARD, None)), \
                patch.object(type(self.env['ir.cron']), '_commit_progress', return_value=1):
            self.env['sale.email.order']._cron_process()
        self.assertEqual(request.state, 'done')

    def test_action_process_requeues(self):
        done = self._process(STANDARD)
        review = self._process('{"category": "quote", "confidence": 0.9, "lines": []}')
        (done | review).action_process()
        self.assertRecordValues(done | review, [{'state': 'done'}, {'state': 'new'}])

    def test_ollama_connection_lists_models(self):
        settings = self.env['res.config.settings'].create({'email_order_ollama_url': 'http://ollama:11434/'})
        with patch.object(requests, 'get') as get:
            get.return_value.json.return_value = {'models': [
                {'name': 'llama3.1:8b', 'size': 4_900_000_000, 'details': {'parameter_size': '8.0B'}},
                {'name': 'qwen2.5:0.5b', 'size': 390_000_000, 'details': {'parameter_size': '494.03M'}},
                {'name': 'custom:latest', 'size': 1_000_000_000},
            ]}
            action = settings.action_test_ollama_connection()
        get.assert_called_once_with('http://ollama:11434/api/tags', timeout=10)
        self.assertEqual((action['params']['type'], action['params']['next']['tag']), ('success', 'reload'))
        self.assertEqual(self.env['ir.config_parameter'].get_param('sale_email_order.ollama_url'), 'http://ollama:11434/')
        # Smallest first, and the current model stays selectable even if it is not on the server.
        self.assertEqual(settings._get_ollama_model_selection(), [
            ('qwen2.5:0.5b', 'qwen2.5:0.5b (494.03M)'), ('custom:latest', 'custom:latest'),
            ('llama3.1:8b', 'llama3.1:8b (8.0B)'), ('qwen2.5:1.5b', 'qwen2.5:1.5b'),
        ])
        settings.email_order_ollama_model = 'qwen2.5:0.5b'
        settings.execute()
        self.assertEqual(self.env['ir.config_parameter'].get_param('sale_email_order.ollama_model'), 'qwen2.5:0.5b')

    def test_ollama_connection_failure(self):
        settings = self.env['res.config.settings'].create({'email_order_ollama_url': 'http://down:11434'})
        with patch.object(requests, 'get', side_effect=requests.ConnectionError("refused")):
            self.assertEqual(settings.action_test_ollama_connection()['params']['type'], 'danger')
        with patch.object(requests, 'get') as get:
            get.return_value.json.return_value = {'models': []}
            self.assertEqual(settings.action_test_ollama_connection()['params']['type'], 'warning')
        # Nothing saved: only the current (default) model can be picked.
        self.assertEqual(settings._get_ollama_model_selection(), [('qwen2.5:1.5b', 'qwen2.5:1.5b')])

    def test_duplicate_sku_does_not_choose_arbitrary_product(self):
        self.env['product.product'].create({'name': 'Alternate desk', 'default_code': 'FURN_7800'})
        request = self._process(STANDARD)
        self.assertFalse(request.sale_order_id)
        self.assertEqual(request.state, 'review')

    def test_product_reference_is_literal_not_a_pattern(self):
        self.env['product.product'].create({'name': 'Literal test item', 'default_code': 'ZX7ABC123'})
        request = self.env['sale.email.order'].create({'name': 'Literal lookup'})
        self.assertFalse(request._find_product('ZX_ABC123'))
        self.assertFalse(request._find_product('ZX%123'))
        self.assertEqual(request._find_product('furn_7800'), self.desk)

    def test_duplicate_mail_starts_without_previous_quotation(self):
        original = self._process(STANDARD)
        copied = original.copy()
        self.assertEqual(copied.state, 'new')
        self.assertFalse(copied.sale_order_id)
        self.assertFalse(copied.inference_trace)
        self.assertFalse(copied.category)
        self.assertFalse(copied.processing_time)
        self.assertTrue(original.sale_order_id)

    def test_catalogue_prefilter_preserves_aliases_and_company_scope(self):
        product = self.env['product.product']
        pairs = [
            ('TST-ITEM-741', 'Cabinet 41 cm'),
            ('TST', 'Short Code'),
            ('ITEM', 'Middle Token'),
            ('SKU_53', 'Literal Underscore'),
            ('!BOX', 'Special Box'),
            ('TST-ITEM-999', 'Unmentioned Furniture'),
        ]
        product.create([{'default_code': sku, 'name': name} for sku, name in pairs])
        request = self.env['sale.email.order'].create({'name': 'Test catalogue'})
        candidates = dict(request._candidate_catalogue('Please send 2 tst-item-741, 3 SKU_53 and 4 !BOX.'))
        for sku in ('TST-ITEM-741', 'TST', 'ITEM', 'SKU_53', '!BOX'):
            self.assertIn(sku, candidates)
        self.assertNotIn('TST-ITEM-999', candidates)
        self.assertIn('TST-ITEM-741', dict(request._candidate_catalogue('Send 2 cabinet 41 cm.')))
        self.assertEqual(request._candidate_catalogue(''), [])

    def test_company_specific_links_are_consistent(self):
        other = self.env['res.company'].create({'name': 'Email workflow other company'})
        foreign = self.env['sale.email.order'].with_company(other).create({'name': 'Other case'})
        request = self.env['sale.email.order'].create({'name': 'Local case'})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            request.related_case_id = foreign
        product = self.env['product.product'].with_company(other).create({
            'name': 'Foreign Cabinet', 'default_code': 'FOREIGN-SKU-19', 'company_id': other.id,
        })
        self.assertNotIn(product.default_code, dict(request._candidate_catalogue('Send 2 FOREIGN-SKU-19 or 2 Foreign Cabinet')))
