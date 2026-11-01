"""Build and check the parameters of one model call. Every call in the study is built here and nowhere else.

The rules (harness/README.md "Rules for every paid call", ops/review-checklist.md 2a "Request rules"):
- effort is always set explicitly (`output_config.effort`);
- thinking is adaptive; "off" exists only for Haiku, only at effort high or below;
- never temperature, top_p, top_k, tool_choice, tools, fallbacks, betas, speed, inference_geo, context editing,
  compaction, caching switches or an assistant prefill;
- model ids come from one list; max_tokens stays within the 128K output limit.

`build_params` can only produce a clean request; `assert_clean` re-checks any params dict (used on everything that is
about to be sent, including requests built by other code).
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional

MODEL_IDS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MAX_OUTPUT_TOKENS = 128_000

# The only top-level keys a call may carry. Anything else (temperature, top_p, top_k, tool_choice, tools, betas,
# fallbacks, speed, inference_geo, cache_control, context_management, ...) is refused.
ALLOWED_TOP_LEVEL = {"model", "max_tokens", "messages", "output_config", "thinking", "system"}


class RequestRuleError(ValueError):
    """The call would break a rule of the study."""


def build_params(model: str, effort: str, max_tokens: int, messages: List[Dict[str, str]],
                 system: Optional[str] = None, thinking_off: bool = False) -> Dict[str, object]:
    """One clean request. `messages` alternate user/assistant and must end with a user turn (no prefill)."""
    params: Dict[str, object] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [dict(m) for m in messages],
        "output_config": {"effort": effort},
        "thinking": {"type": "disabled"} if thinking_off else {"type": "adaptive"},
    }
    if system is not None:
        params["system"] = system
    assert_clean(params)
    return params


def assert_clean(params: Dict[str, object]) -> None:
    extra = set(params) - ALLOWED_TOP_LEVEL
    if extra:
        raise RequestRuleError(f"forbidden request fields: {sorted(extra)}")
    model = params.get("model")
    if model not in MODEL_IDS:
        raise RequestRuleError(f"model {model!r} is not one of {MODEL_IDS}")
    mt = params.get("max_tokens")
    if not isinstance(mt, int) or isinstance(mt, bool) or not 1 <= mt <= MAX_OUTPUT_TOKENS:
        raise RequestRuleError(f"max_tokens must be an integer in 1..{MAX_OUTPUT_TOKENS}, got {mt!r}")
    oc = params.get("output_config")
    if not isinstance(oc, dict) or set(oc) != {"effort"} or oc["effort"] not in EFFORTS:
        raise RequestRuleError(f"output_config must be exactly {{'effort': one of {EFFORTS}}}, got {oc!r}")
    th = params.get("thinking")
    if th == {"type": "adaptive"}:
        pass
    elif th == {"type": "disabled"}:
        # facts-checked.md correction 2: only Haiku, only at high or below. Opus/Fable/Sonnet reject it with a 400.
        if model != "claude-haiku-5-5" or oc["effort"] in ("xhigh", "max"):
            raise RequestRuleError("thinking can be switched off only on Haiku, at effort high or below")
    else:
        raise RequestRuleError(f"thinking must be {{'type': 'adaptive'}} or Haiku's {{'type': 'disabled'}}, got {th!r}")
    msgs = params.get("messages")
    if not isinstance(msgs, list) or not msgs:
        raise RequestRuleError("messages must be a non-empty list")
    roles = [m.get("role") for m in msgs]
    if roles[0] != "user" or roles[-1] != "user" or any(r not in ("user", "assistant") for r in roles):
        raise RequestRuleError("messages must start and end with a user turn and hold only user/assistant turns "
                               "(no assistant prefill, no mid-conversation system messages)")
    for a, b in zip(roles, roles[1:]):
        if a == b:
            raise RequestRuleError("user and assistant turns must alternate")
    for m in msgs:
        if set(m) != {"role", "content"} or not isinstance(m["content"], str) or not m["content"].strip():
            raise RequestRuleError("each message is exactly {role, content} with non-empty text")
    if "system" in params and not (isinstance(params["system"], str) and params["system"].strip()):
        raise RequestRuleError("system, if present, is a non-empty string")


def params_hash(params: Dict[str, object]) -> str:
    """Stable hash of the full request (what the model sees plus every setting)."""
    return hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prompt_text(params: Dict[str, object]) -> str:
    """All text sent to the model, for input-size estimates and the prompt hash."""
    parts = [str(params.get("system") or "")] + [m["content"] for m in params["messages"]]  # type: ignore[index]
    return "\n".join(parts)
