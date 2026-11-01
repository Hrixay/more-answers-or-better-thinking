import unittest

from harness.pareto.outcome import normalize
from harness.tests.fakes import reply


class Normalize(unittest.TestCase):
    def test_answered(self):
        o = normalize(reply(), "claude-haiku-5-5")
        self.assertEqual((o.kind, o.is_failure, o.model_matches), ("answered", False, True))
        self.assertEqual((o.usage.input_tokens, o.usage.output_tokens), (100, 50))

    def test_empty_is_failure(self):
        self.assertEqual(normalize(reply(text="  "), "claude-haiku-5-5").kind, "empty")
        self.assertEqual(normalize(reply(text=None), "claude-haiku-5-5").kind, "empty")

    def test_refusal_keeps_category_and_usage(self):
        o = normalize(reply(stop="refusal", category="reasoning_extraction", text=None, tin=70, tout=0), "claude-haiku-5-5")
        self.assertEqual((o.kind, o.refusal_category, o.usage.input_tokens), ("refusal", "reasoning_extraction", 70))
        self.assertTrue(o.is_failure)

    def test_refusal_billing_rule_b5a(self):
        def r(cat, text=None):
            return normalize(reply(stop="refusal", category=cat, text=text, tin=412, tout=0), "claude-haiku-5-5")
        for cat in ("bio", "frontier_llm", "reasoning_extraction"):
            self.assertTrue(r(cat).refusal_billed_by_rule, cat)
        for cat in ("cyber", "general_harms", None):
            self.assertFalse(r(cat).refusal_billed_by_rule, cat)
        self.assertTrue(r("cyber", text="partial output").refusal_billed_by_rule)        # mid-stream: billed
        self.assertIsNone(normalize(reply(), "claude-haiku-5-5").refusal_billed_by_rule)

    def test_truncated_and_unexpected(self):
        self.assertEqual(normalize(reply(stop="max_tokens"), "claude-haiku-5-5").kind, "truncated")
        for s in ("pause_turn", "tool_use", None, "something_new"):
            self.assertEqual(normalize(reply(stop=s), "claude-haiku-5-5").kind, "unexpected_stop", s)

    def test_model_mismatch_flagged(self):
        o = normalize(reply(model="claude-opus-5-5"), "claude-haiku-5-5")
        self.assertFalse(o.model_matches)

    def test_cache_split(self):
        d = reply(cache_write=500, cache_read=200)
        d["usage"]["cache_creation"] = {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 300}
        o = normalize(d, "claude-haiku-5-5")
        self.assertEqual((o.usage.cache_write_5m_tokens, o.usage.cache_write_1h_tokens, o.usage.cache_read_tokens), (200, 300, 200))
        # no breakdown: everything at the 5-minute rate
        o2 = normalize(reply(cache_write=500), "claude-haiku-5-5")
        self.assertEqual(o2.usage.cache_write_5m_tokens, 500)

    def test_thinking_blocks_not_in_answer(self):
        d = reply()
        d["content"].insert(0, {"type": "thinking", "thinking": "secret"})
        o = normalize(d, "claude-haiku-5-5")
        self.assertEqual((o.answer_text, o.thinking_blocks), ("Answer: 1 = 5", 1))


if __name__ == "__main__":
    unittest.main()
