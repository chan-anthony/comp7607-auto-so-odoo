import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addons/sale_email_order/models'))
from nonorder import decide,draft_followup
class NonOrderTests(unittest.TestCase):
 def test_filing(self):
  self.assertEqual(decide('We received your notice. No reply needed.',True,lambda _:None)[0],'archived')
 def test_request_survives(self):
  for s in ['Thanks for the update. Can you call me?','No reply needed, but please change the address.','For reference only. The shipment is damaged.']:
   self.assertEqual(decide(s,True,lambda _:None)[0],'human')
 def test_ticket_status(self):
  find=lambda n: n if n==321 else None
  self.assertEqual(decide('CASE-321: Thanks for the update.',True,find),('linked_no_action',321))
  self.assertEqual(decide('CASE-321: Did you sign?',True,find),('linked_human',321))
  self.assertEqual(decide('CASE-322: Thanks for the update.',True,find),('human',None))
  self.assertEqual(decide('CASE-321 and CASE-322: Thanks.',True,find),('human',None))
 def test_subject_and_sender(self):
  self.assertEqual(decide('Thanks.',True,lambda _:None,'Please send a copy')[0],'human')
  self.assertEqual(decide('Thanks.',False,lambda _:None)[0],'human')
 def test_mixed(self):self.assertTrue(draft_followup('Ship two boxes. Please explain yesterday’s charge.'))
if __name__=='__main__':unittest.main()
