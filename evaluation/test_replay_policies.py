import unittest
from replay_policies import evaluate


class TestPolicyReplay(unittest.TestCase):
    def setUp(self):
        self.cases=[dict(id="x", family="correction", gold_action="draft", gold_draft_lines={"A":3})]
        def candidate(q, conf):
            return {"x":dict(candidate={"category":"standard","confidence":conf},
                             mapped_lines=[["A",q]], known_sender=True, seconds=1)}
        self.small=candidate(12,.95); self.big=candidate(3,.99)
        self.big["x"]["metadata"]={"usage":{"total_tokens":123,"input_tokens":100,"output_tokens":23}}
        self.pools=[self.small,self.big,{"x":{"checks":{"qty":.91},"seconds":.1}}]

    def test_semantically_wrong_but_confident(self):
        raw=evaluate(self.cases,self.pools,"confidence",.8)
        kev=evaluate(self.cases,self.pools,"kev",.9)
        self.assertEqual((raw["wrong_drafts"],raw["strong_calls"]),(1,0))
        self.assertEqual((kev["right"],kev["strong_calls"],kev["strong_tokens"]),(1,1,123))
        self.assertAlmostEqual(kev["replay_model_seconds"],2.1)

    def test_no_catalogue_match_remains_review(self):
        self.big["x"]["mapped_lines"]=[[None,3]]
        self.assertEqual(evaluate(self.cases,self.pools,"strong",0)["drafts"],0)
        self.assertEqual(evaluate(self.cases,self.pools,"strong",0)["right"],0)

    def test_strong_can_regress(self):
        self.small["x"]["mapped_lines"]=[["A",3]]
        self.big["x"]["mapped_lines"]=[["A",12]]
        self.assertEqual(evaluate(self.cases,self.pools,"small",0)["right"],1)
        self.assertEqual(evaluate(self.cases,self.pools,"kev",.9)["wrong_drafts"],1)
