"""Offline unit tests for current-sender gates, scorer alignment and calibration."""
import unittest
from meta_router import fit,verdict,rules
from authority_policy import decision
CAT=[('AA-4','Binder',20)]
class GateTests(unittest.TestCase):
    def test_current_instruction(self):
        branch,_=rules._triage_authority('Please send 4 AA-4.',CAT,[('AA-4',4)],True)
        self.assertEqual(branch,'verified_draft')
    def test_quoted_imperative(self):
        msg='Can you see who wrote this?\n> Please send 4 AA-4.'
        self.assertEqual(rules._clip_thread(msg)[0],'Can you see who wrote this?')
        self.assertEqual(rules._triage_authority(msg,CAT,[('AA-4',4)],True)[0],'local_review')
    def test_conditional(self):
        self.assertEqual(rules._triage_authority('If approved, please send 4 AA-4.',CAT,[('AA-4',4)],True)[0],'local_review')
    def test_quantity_disagreement(self):
        self.assertEqual(rules._triage_authority('Please send 4 AA-4.',CAT,[('AA-4',9)],True)[0],'assess')
    def test_review_cannot_escalate(self):
        self.assertEqual(decision('local_review',1.,0.),'review')
        self.assertEqual(decision('verified_draft',1.,0.),'small')
        self.assertEqual(decision('assess',.5,.5),'strong')
    def test_uncertainty_from_values(self):
        t='{"category":"standard","product":"夾","quantity":4,"confidence":0.9}'
        b=[dict(bytes=[v],logprob=-1.) for v in t.encode()]
        a=rules._field_logprobs(t,b)
        self.assertEqual(set(a),{'category','product','quantity'})
        self.assertEqual(a['product']['tokens'],3)
        self.assertIsNone(rules._field_logprobs(t,b[:-1]))
    def test_fit_export_direction(self):
        x=[[0],[0],[1],[1]];m=fit(x,[False,False,True,True])
        self.assertLess(rules._risk_probability([0],m),.5);self.assertGreater(rules._risk_probability([1],m),.5)
if __name__=='__main__':unittest.main()
