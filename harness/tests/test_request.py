import unittest

from harness.pareto.request import RequestRuleError, assert_clean, build_params, params_hash
from harness.tests.fakes import params


class RequestRules(unittest.TestCase):
    def test_clean_request_ok(self):
        p = params()
        self.assertEqual(p["output_config"], {"effort": "medium"})
        self.assertEqual(p["thinking"], {"type": "adaptive"})

    def test_forbidden_fields(self):
        for k, v in [("temperature", 0), ("top_p", 1), ("top_k", 5), ("tool_choice", {"type": "any"}), ("tools", []),
                     ("betas", ["x"]), ("speed", "fast"), ("inference_geo", "us"), ("cache_control", {})]:
            p = params()
            p[k] = v
            with self.assertRaises(RequestRuleError, msg=k):
                assert_clean(p)

    def test_thinking_off_only_haiku_high_or_below(self):
        params(thinking_off=True)                                   # Haiku, medium: fine
        with self.assertRaises(RequestRuleError):
            params(model="claude-sonnet-5-5", thinking_off=True)
        with self.assertRaises(RequestRuleError):
            params(effort="xhigh", thinking_off=True)

    def test_effort_required_and_valid(self):
        p = params()
        del p["output_config"]
        with self.assertRaises(RequestRuleError):
            assert_clean(p)
        with self.assertRaises(RequestRuleError):
            params(effort="extreme")

    def test_model_and_max_tokens(self):
        with self.assertRaises(RequestRuleError):
            params(model="claude-haiku-4")
        for bad in (0, -1, 128_001, True, 1.5):
            with self.assertRaises(RequestRuleError, msg=repr(bad)):
                params(max_tokens=bad)

    def test_no_prefill_and_alternation(self):
        with self.assertRaises(RequestRuleError):
            build_params("claude-haiku-5-5", "low", 10, [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
        with self.assertRaises(RequestRuleError):
            build_params("claude-haiku-5-5", "low", 10, [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}])

    def test_hash_is_stable_and_sensitive(self):
        self.assertEqual(params_hash(params()), params_hash(params()))
        self.assertNotEqual(params_hash(params()), params_hash(params(effort="high")))


if __name__ == "__main__":
    unittest.main()
