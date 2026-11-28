import unittest
from module_rules import rules
class NonOrderTests(unittest.TestCase):
 def test_filing(self):
  self.assertEqual(rules._disposition_route('We received your notice. No reply needed.',True,lambda _:None)[0],'archived')
 def test_request_survives(self):
  for s in ['Thanks for the update. Can you call me?','No reply needed, but please change the address.','For reference only. The shipment is damaged.']:
   self.assertEqual(rules._disposition_route(s,True,lambda _:None)[0],'human')
 def test_ticket_status(self):
  find=lambda n: n if n==321 else None
  self.assertEqual(rules._disposition_route('CASE-321: Thanks for the update.',True,find),('linked_no_action',321))
  self.assertEqual(rules._disposition_route('CASE-321: Did you sign?',True,find),('linked_human',321))
  self.assertEqual(rules._disposition_route('CASE-322: Thanks for the update.',True,find),('human',None))
  self.assertEqual(rules._disposition_route('CASE-321 and CASE-322: Thanks.',True,find),('human',None))
 def test_subject_and_sender(self):
  self.assertEqual(rules._disposition_route('Thanks.',True,lambda _:None,'Please send a copy')[0],'human')
  self.assertEqual(rules._disposition_route('Thanks.',False,lambda _:None)[0],'human')
 def test_mixed(self):self.assertTrue(rules._draft_followup('Ship two boxes. Please explain yesterday’s charge.'))
if __name__=='__main__':unittest.main()
