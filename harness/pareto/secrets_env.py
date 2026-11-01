"""Reading the API key. The key is read from the repo's `.env` ONLY inside `RealTransport`, after the spend guard's live
gate and the SDK pin have passed. It is never logged, never printed, never put in an error message or a manifest.

The file is a plain `KEY=value` file; only `ANTHROPIC_API_KEY` is used. Nothing here reads the process environment.
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_ENV = Path(__file__).resolve().parents[2] / ".env"
_LINE = re.compile(r"^\s*(?:export\s+)?ANTHROPIC_API_KEY\s*=\s*(.*?)\s*$")


class NoApiKey(RuntimeError):
    """The key could not be read. The message never contains any part of the file."""


def load_api_key(env_file: Path = DEFAULT_ENV) -> str:
    env_file = Path(env_file)
    if not env_file.exists():
        raise NoApiKey(f"no .env file at {env_file}")
    raw = env_file.read_bytes()
    text = None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if text is None:            # raised OUTSIDE the except block, so no UnicodeDecodeError (it carries file bytes) is chained
        raise NoApiKey("the .env file is not valid UTF-8")
    key = None
    for ln in text.splitlines():
        m = _LINE.match(ln)
        if m:
            v = m.group(1)
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            else:
                v = re.split(r"\s+#", v, maxsplit=1)[0].strip()      # an unquoted trailing comment is not part of the key
            key = v
    if not key:
        raise NoApiKey("the .env file has no ANTHROPIC_API_KEY line with a value")
    return key
