"""RealTransport's error mapping, with a stand-in for the SDK (the real one is not installed and is never called)."""
import sys
import types
import unittest

from harness.pareto.transport import RealTransport, TransportError
from harness.tests.fakes import guard


def fake_sdk(enter_exc=None, final_exc=None):
    """enter_exc / final_exc are functions of the fake module, so the exception classes belong to the same module."""
    m = types.ModuleType("anthropic")
    m.__version__ = "9.9.9"

    class APIError(Exception):
        pass

    class APIStatusError(APIError):
        def __init__(self, status=500):
            super().__init__(f"status {status}")
            self.status_code = status

    class APIConnectionError(APIError):
        pass

    class APITimeoutError(APIConnectionError):
        pass

    for name, status in (("RateLimitError", 429), ("BadRequestError", 400), ("AuthenticationError", 401),
                         ("PermissionDeniedError", 403), ("NotFoundError", 404)):
        setattr(m, name, type(name, (APIStatusError,), {"__init__": lambda self, st=status: APIStatusError.__init__(self, st)}))
    m.APIError, m.APIStatusError, m.APIConnectionError, m.APITimeoutError = APIError, APIStatusError, APIConnectionError, APITimeoutError

    class Final:
        _request_id = "req_1"

        def to_dict(self):
            return {"id": "m", "model": "claude-haiku-5-5", "content": [], "stop_reason": "end_turn", "usage": {}}

    class Stream:
        request_id = "req_from_headers"                 # the SDK's stream object carries the HTTP request-id (N48/S4)

        def get_final_message(self):
            if final_exc:
                raise final_exc(m)
            return Final()

    class CM:
        def __enter__(self):
            if enter_exc:
                raise enter_exc(m)
            return Stream()

        def __exit__(self, *a):
            return False

    class Messages:
        def stream(self, **kw):
            return CM()

    class Client:
        def __init__(self, **kw):
            assert kw.get("max_retries") == 0, "SDK retries must be off"
            self.messages = Messages()

    m.Anthropic = Client
    return m


class RealTransportMapping(unittest.TestCase):
    def run_with(self, sdk):
        old = sys.modules.get("anthropic")
        sys.modules["anthropic"] = sdk
        try:
            class G:
                def require_live(self):
                    pass
            return RealTransport(G(), requirements=self.pin_file("anthropic==9.9.9"), env_file=self.env_file())
        finally:
            if old is None:
                del sys.modules["anthropic"]
            else:
                sys.modules["anthropic"] = old

    def env_file(self, text="ANTHROPIC_API_KEY=sk-ant-test-key\n"):
        import tempfile
        from pathlib import Path
        p = Path(tempfile.mkdtemp()) / ".env"
        p.write_text(text)
        return p

    def test_key_is_read_only_here_and_never_in_error_text(self):
        from harness.pareto.secrets_env import NoApiKey, load_api_key
        self.assertEqual(load_api_key(self.env_file("# c\nexport ANTHROPIC_API_KEY='abc123'\nOTHER=x\n")), "abc123")
        for bad in ("", "OTHER=1\n", "ANTHROPIC_API_KEY=\n"):
            with self.assertRaises(NoApiKey) as cm:
                load_api_key(self.env_file(bad))
            self.assertNotIn("sk-ant", str(cm.exception))
        with self.assertRaises(NoApiKey):
            load_api_key(self.env_file().parent / "missing.env")

    def test_non_utf8_env_does_not_leak_and_comments_are_stripped(self):
        import tempfile
        from pathlib import Path
        from harness.pareto.secrets_env import NoApiKey, load_api_key
        p = Path(tempfile.mkdtemp()) / ".env"
        p.write_bytes(b"ANTHROPIC_API_KEY=sk-ant-SECRET\n\xff\xfe junk\n")
        with self.assertRaises(NoApiKey) as cm:
            load_api_key(p)
        self.assertNotIn("SECRET", repr(cm.exception) + str(cm.exception.args))
        self.assertIsNone(cm.exception.__context__)                 # no chained decoder error holding file bytes
        self.assertEqual(load_api_key(self.env_file("ANTHROPIC_API_KEY=abc123   # my key\n")), "abc123")
        self.assertEqual(load_api_key(self.env_file("ANTHROPIC_API_KEY=\"ab#c\"\n")), "ab#c")

    def test_base_url_is_fixed_and_a_redirect_is_refused(self):
        import os
        sdk = fake_sdk()
        seen = {}
        orig = sdk.Anthropic

        def Anthropic(**kw):
            seen.update(kw)
            return orig(**kw)
        sdk.Anthropic = Anthropic
        self.run_with(sdk)
        self.assertEqual(seen["base_url"], "https://api.anthropic.com")
        old = os.environ.get("ANTHROPIC_BASE_URL")
        try:
            os.environ["ANTHROPIC_BASE_URL"] = "https://evil.example"
            with self.assertRaises(RuntimeError):
                self.run_with(fake_sdk())
            os.environ["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com/"      # the real address is fine
            self.run_with(fake_sdk())
        finally:
            if old is None:
                os.environ.pop("ANTHROPIC_BASE_URL", None)
            else:
                os.environ["ANTHROPIC_BASE_URL"] = old

    def test_key_reaches_the_client_and_transport_refuses_without_one(self):
        sdk = fake_sdk()
        seen = {}
        orig = sdk.Anthropic

        def Anthropic(**kw):
            seen.update(kw)
            return orig(**kw)
        sdk.Anthropic = Anthropic
        self.run_with(sdk)
        self.assertEqual(seen["api_key"], "sk-ant-test-key")
        from harness.pareto.secrets_env import NoApiKey
        old = sys.modules.get("anthropic")
        sys.modules["anthropic"] = fake_sdk()
        try:
            class G:
                def require_live(self):
                    pass
            with self.assertRaises(NoApiKey):
                RealTransport(G(), requirements=self.pin_file("anthropic==9.9.9"), env_file=self.env_file("x=1"))
        finally:
            if old is None:
                del sys.modules["anthropic"]
            else:
                sys.modules["anthropic"] = old

    def pin_file(self, text):
        import tempfile
        from pathlib import Path
        p = Path(tempfile.mkdtemp()) / "requirements.txt"
        p.write_text(text + "\n")
        return p

    def test_sdk_must_be_pinned_and_match(self):
        from harness.pareto.transport import check_sdk_pin, pinned_sdk_version
        sdk = fake_sdk()
        self.assertEqual(check_sdk_pin(sdk, self.pin_file("anthropic==9.9.9")), "9.9.9")
        with self.assertRaises(RuntimeError):
            check_sdk_pin(sdk, self.pin_file("anthropic==1.0.0"))        # installed 9.9.9 is not the pin
        with self.assertRaises(RuntimeError):
            check_sdk_pin(sdk, self.pin_file("# no pin yet"))
        self.assertIsNone(pinned_sdk_version(self.pin_file("anthropic>=1.0")))   # a range is not a pin

    def test_the_repo_pins_the_sdk(self):
        from harness.pareto.transport import pinned_sdk_version
        self.assertEqual(pinned_sdk_version(), "0.125.0")

    def test_real_transport_refuses_an_unpinned_or_different_sdk(self):
        sdk = fake_sdk()
        old = sys.modules.get("anthropic")
        sys.modules["anthropic"] = sdk
        try:
            class G:
                def require_live(self):
                    pass
            for text in ("# nothing pinned", "anthropic==1.0.0"):
                with self.assertRaises(RuntimeError):
                    RealTransport(G(), requirements=self.pin_file(text), env_file=self.env_file())
        finally:
            if old is None:
                del sys.modules["anthropic"]
            else:
                sys.modules["anthropic"] = old

    def test_status_below_400_is_not_an_http_error_response(self):
        t = self.run_with(fake_sdk(enter_exc=lambda m: m.APIStatusError(200)))
        with self.assertRaises(TransportError) as cm:
            t.send({})
        self.assertEqual((cm.exception.billed, cm.exception.retryable), ("unknown", False))

    def test_ok(self):
        t = self.run_with(fake_sdk())
        self.assertEqual(t.send({})["_request_id"], "req_from_headers")      # from the stream's response headers, not the message

    def test_http_errors_before_stream_are_unbilled(self):
        for name, retry in (("RateLimitError", True), ("BadRequestError", False), ("AuthenticationError", False),
                            ("NotFoundError", False)):
            t = self.run_with(fake_sdk(enter_exc=lambda m, n=name: getattr(m, n)()))
            with self.assertRaises(TransportError) as cm:
                t.send({})
            self.assertEqual((cm.exception.billed, cm.exception.retryable), ("no", retry), name)

    def test_5xx_before_stream_unbilled_and_retryable(self):
        t = self.run_with(fake_sdk(enter_exc=lambda m: m.APIStatusError(529)))
        with self.assertRaises(TransportError) as cm:
            t.send({})
        self.assertEqual((cm.exception.billed, cm.exception.retryable), ("no", True))

    def test_timeout_and_disconnect_are_unknown(self):
        for make in (lambda m: m.APITimeoutError("t"), lambda m: m.APIConnectionError("c")):
            t = self.run_with(fake_sdk(enter_exc=make))
            with self.assertRaises(TransportError) as cm:
                t.send({})
            self.assertEqual((cm.exception.billed, cm.exception.retryable), ("unknown", False))

    def test_error_after_stream_started_is_unknown_even_if_it_looks_like_a_5xx(self):
        for make in (lambda m: m.APIStatusError(529), lambda m: RuntimeError("stream died")):
            t = self.run_with(fake_sdk(final_exc=make))
            with self.assertRaises(TransportError) as cm:
                t.send({})
            self.assertEqual((cm.exception.kind, cm.exception.billed, cm.exception.retryable), ("mid_stream", "unknown", False))


if __name__ == "__main__":
    unittest.main()
