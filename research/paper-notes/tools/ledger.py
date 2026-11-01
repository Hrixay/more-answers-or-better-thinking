"""Claims ledger tool (D-118, D-120): every number in the paper resolves by script from its pinned source. Karen (Opus 5.5).

No API calls. Reads sources only through `git show <commit>:<path>`, so a value is checked against the exact committed bytes.
Refuses `data/tasks/` and any `.env` path (task records and secrets are never read).

Row (one JSON object per line in the ledger):
  id, part, section, used_in, text, template, values[], sources{}, tier, tier_detail, holm_declared, rule[], companions[],
  origin, plan_status, status, note
A value:
  {"name", "printed", "src", one of: "key" (list of segments; a segment may be {"where": {...}} to pick the one list
   element whose fields match) | "regex" (+ optional "group", "nth") | "sha256_of_source": true (the SHA-256 of the source file's bytes at its
   commit; kind "str") | "formula" (arithmetic over other value names in the
   row), optional "scale" (default 1), "round" ("auto" = the decimals shown in `printed`, "dp:N", "sf:N", "int"),
   ("floor" = the whole-number floor, as for k), optional "kind": "str" (compare text exactly), optional "margins" (rounding must not move the value across these),
   optional "agg": "len" | "sum" | "min" | "max" (applied to the object or list the key reaches, e.g. the number of sets in a
   record), optional "hidden": true (an input that is not printed: it is read and checked against its source and can feed a
   formula, but it has no slot in the template), and "raw" (filled by `resolve`)}
A fact (optional list `facts`): a non-numeric statement the text makes, checked at its source:
  {"what", "src", "key" | "regex" (+ "group"), "expect"}   e.g. a comparison's cross_window is true, a flag's status is "not fired"

Commands:
  template LEDGER                  build each row's template from `text` and its values, taken in order of appearance
                                   (each value's `printed` must occur in the text after the previous one)
  pin LEDGER [--ref origin/main]   fill each source's commit (last commit touching the path on REF) and sha256
  resolve LEDGER                   read every value from its source and store it as `raw`
  check LEDGER [--ids C-001 ...]   verify hashes, keys, rounding, the template, bare numerals; exit 1 on any failure
  render LEDGER OUT.md             the readable table (never edited by hand)
  lint DRAFT.md LEDGER [--appendix] a draft section: every {{id.name}} tag (or {{id.name|N}}, D-154's rounding: from raw x scale, half away
                                   from zero; never after an inequality sign; never across a value's margins) resolves;
                                   a $$ … $$ display equation holds no tag and no numeral but 0, 1 and 100;
                                   --vocab also reports D-161's old project terms outside quotation marks; no bare numeral outside the allow list;
                                   no id, tag, hash or "before the data" (settlement P-2) unless --appendix
"""
import ast
import hashlib
import json
import re
import subprocess
import sys
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP

DENY = (re.compile(r"(^|/)data/tasks(/|$)"), re.compile(r"(^|/)\.env"))
TIERS = {"confirmatory (Holm)", "confirmatory-secondary", "exploratory", "descriptive", "disclosure", "interpretation"}

# Numerals allowed in prose without a ledger value: names and design vocabulary, never a result. Edith checks this list.
ALLOW = [
    (r"\b(?:Claude )?(?:Haiku|Sonnet|Opus) 5\.5\b", "model name"),
    (r"\b(?:Claude )?(?:Fable|Mythos) 5(?:\.1)?\b", "model name"),
    (r"\b(?:Haiku|Sonnet|Opus) 4(?:\.\d)?\b", "model name"),
    (r"\bTests? [1-5](?:(?:,\s*|,? and |,? or |\s*[-–]\s*| to )[1-5])*\b", "test name or list of test names"),
    (r"\bTests? B[1-3](?:\s*(?:-|–|to|and)\s*B[1-3])*\b|\bB[1-3]\b", "test name"),
    (r"\bD-\d{2,3}(?:\(\w+\))?(?:\s*(?:-|–|to)\s*D-\d{2,3})?", "ruling id"),
    (r"\b[A-Z]{1,2}-\d{2,3}\b", "row or item id"),
    (r"\bitems? \d{1,2}[a-h]?(?:\s*(?:-|–|and|to)\s*\d{1,2}[a-h]?)*\b", "reporting-definitions item"),
    (r"\b(?:Deviation|Amendment|Addendum) [1-9A-C]\d?\b", "document part"),
    (r"\b[Ll]ocks? [1-4](?:\s*(?:-|–|to|and)\s*[1-4])?\b|\bprereg-lock-[1-4]\b", "lock name"),
    (r"§\s?\d+(?:\.\d+)?", "section sign"),
    (r"\b(?:Table|Figure|Appendix|Section) [A-Z]?\d+\b", "cross-reference"),
    (r"\b(?:C|E|G|R|L|X|F|P|K|S|T|TAB-|FIG-)\d{1,2}\b", "keep-list, arm or row label"),
    (r"\bH-pick8\b|\bvote@\d+\b|\bany@\d+\b|\bl1[4-6]n?\d*\b", "arm or preset label"),
    (r"(?<=\u25a1 )\((?:4|6|8|12|16|24)\)", "a length in brackets right after a value"),
    (r"\b(?:4|6|8|12|16|24)- and (?:4|6|8|12|16|24)-step\b", "two lengths (design)"),
    (r"\b20\d\d-\d\d-\d\d/\d\d\b", "a two-day date span"),
    (r"\bthe 5\.5 family\b|\bcollapses at 100%|\bevery arm at 100%", "model family; the bootstrap's ceiling case"),
    (r"\bSHA-256\b", "hash function name"),
    (r"\^(?:4|6|8|12|16|24)\b", "a step count as an exponent (compounding arithmetic)"),
    (r"\b\d{1,2}(?: and \d{1,2})? (?:January|February|March|April|May|June|July|August|September|October|November|December) 20\d\d\b",
     "date (day month year)"),
    (r"\b1/m\b|\bthe 90s\b", "the tie rule's 1/m; 'the 90s' (a decade of percent)"),
    (r"\b[Rr]ound [1-9]\b|\b[Ss]ection [1-9]\b", "round or section label"),
    (r"\bTask [1-9](?: to Task [1-9])?\b", "team task label"),
    (r"\b(?:take )?[Ss]amples? [1-9](?:\s*[-–]\s*\d{1,2}| to \d{1,2})?\b", "sample position label"),
    (r"[−-]10 margin\b|[×x] 2 shapes\b", "the margin as a signed number; 'x 2 shapes' (design)"),
    (r"\bless than 10% of the time\b", "the lowest pre-specified difficulty bin's edge"),
    (r"\b\d0\s*[-–]\s*\d0%(?:(?:,\s*|,? and )\d0\s*[-–]\s*\d0%)*\s+bins?\b|\b[Bb]elow 10% single-try accuracy\b",
     "pre-specified 10-point difficulty bins (item 20 and keep-list C9)"),
    (r"\bscored 100 on\b|\bscored exactly 0 on\b", "the perfect or zero score as a level"),
    (r"\b[Pp]er 10,000\b", "a presentation unit (per 10,000 puzzles)"),
    (r"\b48-hour (?:run )?window\b", "the pre-registered run window (design)"),
    (r"(?:^|(?<=\s))\([1-9]\)(?=\s)", "list enumeration (1), (2) ..."),
    (r"\b(?:4|6|8|12|16|24)(?:(?:,\s*|,? and |,? or | to |\s*[-–/]\s*)(?:4|6|8|12|16|24))*(?:-step|\s+steps?)\b",
     "puzzle length or list of lengths (design)"),
    (r"\bat (?:4|6|8|12|16|24)(?:(?:,\s*|,? and |,? or | to |\s*[-–]\s*)(?:4|6|8|12|16|24))*\b"
     r"(?!\s*(?:points?|%|percent|tries|times|calls|puzzles|bases|items|tokens|\.\d))",
     "puzzle length after 'at' (design; never before a unit of a result)"),
    (r"\b(?:4|6|8|12|16|24)(?:\s*(?:to|[-–])\s*(?:4|6|8|12|16|24))? in (?:the length sweep|Pilot [12])\b",
     "length range of a named run (design)"),
    (r"\b(?:1|4|6|8|12|16|24)\s?[x×]\s?(?:1|4|6|8|12|16|24)\b", "shape notation"),
    (r"\bN\s?=\s?(?:4|6|8|12|16|24)\b", "puzzle length (design)"),
    (r"\bwithin (?:5|10)(?: points?)?\b|\b(?:5|10)-point(?:-margin| (?:primary |secondary )?margin)\b|\bby more than (?:5|10)(?: points?)?\b|"
     r"\bmargin of (?:5|10)(?: points?)?\b", "pre-registered margin, in a margin phrase only (Edith, ledger check 1)"),
    (r"\b(?:90|95)% (?:intervals?|confidence|upper|lower|bounds?|CIs?|Clopper|BCa|bootstrap|Wilson|exact)\b", "interval level"),
    (r"\brepick\d\b", "rule-kind name"),
    (r"\bClaude 5\.5\b", "model family name"),
    (r"\ba value above 1\b|\b1 means no\b|\bratio below 1\b|\bbelow 1(?= at| on)", "the neutral value of a ratio index"),
    (r"\bk\s?[+−-]\s?[1-9]\b", "k-sensitivity row label (k-2 ... k+2)"),
    (r"\b1(?=/\u25a1)", "the numerator of 'about 1/k' when k is a value"),
    (r"x \(100 [-−] accuracy\)", "the constant in the per-puzzle variance formula"),
    (r"\b20\d\d-\d\d-\d\d(?:T\d\d:\d\d(?::\d\d)?Z?)?\b|\b\d\d:\d\d(?::\d\d)?Z?\b", "date or time"),
    (r"\b202\d\b", "year (2020s only; any other four-digit number needs a value)"),
    (r"\b3[–-]3 ties?\b", "a tie pattern in a 6-try vote (D-157's words), not a measured value"),
    (r"\bdata/main/free-analyses/fa\d+[a-z]?(?:r\d+)?\.json\b", "a free-analysis output file name (appendix list; Jarvis)"),
    (r"(?:(?<=\()|(?<=; ))[A-Z][A-Za-z'-]+(?: and [A-Z][A-Za-z'-]+| et al\.)?,\s(?:19\d\d|20[01]\d)(?=[,;)])",
     "year in a bracketed author-year citation (Vision; tightened by Edith)"),
    (r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}\b", "date"),
    (r"\bledger-0\.\d\b|\bv\d\b", "version label"),
    (r"\bStud(?:y|ies) 1b?\b|\bPilot [12]\b|\bH[1-4]\b|\bB5\b", "study, pilot, hypothesis or billing-rule name"),
]
ALLOW_RX = [(re.compile(p), why) for p, why in ALLOW]

# Edith's settlement P-2 (ops/reviews/2026-10-15-plan-settlement/g5.md §2): no ruling number, keep-list id, lock tag, hash, run id,
# set id, shape code or "before the data" in a main-text row. A row is main text unless its section names the appendix.
# (One change from g5's regex: a hash must contain a letter a-f, so a long decimal such as 0.003559415 is not read as a hash;
# Edith's check 1 adds digit-only runs of exactly 40 or 64 characters, so a hash made only of digits cannot pass.)
MAIN_TEXT_BAR = re.compile(r"\bD-\d+|\bC(1[0-3]|[1-9])\b|prereg-lock|\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b|\b(?:\d{40}|\d{64})\b|ledger-l\d+n\d+-v\d|main-l14n6-1|"
                           r"study1b-1|topup-1|\b(1x6|6x1|1x24|24x1)\b|before the data")


def is_main_text(row):
    return "appendix" not in str(row.get("section", "")).lower()

_cache = {}


def die(msg):
    sys.exit(f"ledger: {msg}")


def denied(path):
    return any(rx.search(path) for rx in DENY)


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def blob(path, commit):
    if denied(path):
        raise ValueError(f"refused path {path}")
    k = (path, commit)
    if k not in _cache:
        _cache[k] = git("show", f"{commit}:{path}")
    return _cache[k]


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as e:
                    die(f"{path}:{n}: {e}")
    return rows


def save(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def walk(obj, key):
    segs = key if isinstance(key, list) else [int(s) if s.isdigit() else s for s in key.split(".")]
    for s in segs:
        if isinstance(s, dict) and "where" in s:
            hits = [e for e in obj if isinstance(e, dict) and all(e.get(f) == v for f, v in s["where"].items())]
            if len(hits) != 1:
                raise KeyError(f"where {s['where']} matched {len(hits)} elements")
            obj = hits[0]
        elif isinstance(obj, list):
            obj = obj[int(s)]
        else:
            if s not in obj and isinstance(s, int) and str(s) in obj:
                s = str(s)  # a dict keyed by digit strings (e.g. by_n.6, shapes.1x6.10)
            if s not in obj:
                raise KeyError(f"no key {s!r} (have {list(obj)[:12]})")
            obj = obj[s]
    return obj


def aggregate(obj, how):
    items = list(obj.values()) if isinstance(obj, dict) else list(obj)
    if how == "len":
        return len(items)
    nums = [num(i) for i in items]
    return {"sum": sum, "min": min, "max": max}[how](nums)


def num(x):
    if isinstance(x, bool):
        raise TypeError("boolean is not a number")
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str):
        s = x.replace(",", "").replace("\u2212", "-").strip()
        if re.fullmatch(r"-?\d+/\d+", s):  # stored fractions such as k's ratio "239909520/35755009"
            a, b = s.split("/")
            return int(a) / int(b)
        return float(s)
    raise TypeError(f"not a number: {x!r}")


from math import ceil as _ceil  # a "≤" bound is rounded up (Edith, pr27 §20)
from statistics import NormalDist as _NormalDist
_NORMAL = _NormalDist()


TAG_RE = re.compile(r"\{\{([\w-]+)\.(\w+)(?:\|(\d))?\}\}")  # a ledger tag; D-154's optional |N rounds it to N decimals


def tag_print(v, places=None):
    """What a tag prints: the value's stored text, or, with D-154's marker |N, the value rounded to N decimals from its raw number
    (times its scale), half away from zero, a leading "+" kept, and a value that rounds to zero printed without a sign. This is
    Vision's paper/tools/tagfmt.py rule, with the scale applied (a share stored as 0.9575 and printed as a percentage)."""
    if places in (None, ""):
        return v["printed"]
    raw = v.get("raw")
    if v.get("kind") == "str" or isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"{v['name']}: no numeric raw value to round")
    n = int(places)
    r = (Decimal(repr(raw)) * Decimal(repr(v.get("scale", 1)))).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP)
    if r == 0:
        return f"{abs(r):.{n}f}"
    return ("+" if r > 0 and str(v.get("printed", "")).startswith("+") else "") + f"{r:.{n}f}"


def safe_eval(expr, env):
    tree = ast.parse(expr, mode="eval")
    funcs = {"min": min, "max": max, "abs": abs, "ceil": _ceil, "ncdf": _NORMAL.cdf, "nppf": _NORMAL.inv_cdf}  # normal cdf and its inverse
    ok = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div,
          ast.Pow, ast.USub, ast.UAdd, ast.Call)
    for node in ast.walk(tree):
        if not isinstance(node, ok):
            raise ValueError(f"formula: {type(node).__name__} not allowed")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in funcs):
            raise ValueError("formula: only min, max, abs, ceil, ncdf and nppf may be called")
        if isinstance(node, ast.Name) and node.id not in env and node.id not in funcs:
            raise KeyError(f"formula: unknown name {node.id}")
    return eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, {**env, **funcs})


def resolve_row(row):
    raws = {}
    pending = list(row.get("values", []))
    for _ in range(len(pending) + 1):
        left = []
        for v in pending:
            if "formula" in v:
                try:
                    v["raw"] = safe_eval(v["formula"], raws)
                except KeyError:
                    left.append(v)
                    continue
            else:
                src = row["sources"][v["src"]]
                data = blob(src["path"], src["commit"])
                if v.get("sha256_of_source"):  # the SHA-256 of the pinned source file itself (an output's fingerprint)
                    v["raw"] = hashlib.sha256(data).hexdigest()
                elif "key" in v:
                    v["raw"] = walk(json.loads(data), v["key"])
                    if v.get("agg"):
                        v["raw"] = aggregate(v["raw"], v["agg"])
                elif "regex" in v:
                    text = data.decode("utf-8")
                    ms = list(re.finditer(v["regex"], text, re.M))
                    nth = v.get("nth")
                    if nth is None and len(ms) != 1:
                        raise ValueError(f"{row['id']}.{v['name']}: regex matched {len(ms)} times")
                    if nth is not None and len(ms) <= nth:
                        raise ValueError(f"{row['id']}.{v['name']}: regex matched {len(ms)} times, nth {nth}")
                    v["raw"] = ms[nth or 0].group(v.get("group", 1))
                else:
                    raise ValueError(f"{row['id']}.{v['name']}: no key, regex, formula or sha256_of_source")
            if v.get("kind") != "str":
                raws[v["name"]] = num(v["raw"])
        if not left:
            return
        pending = left
    raise ValueError(f"{row['id']}: formulas could not be resolved: {[v['name'] for v in pending]}")


def parse_printed(p):
    s = p.replace("\u2212", "-").replace(",", "").replace("$", "").replace("%", "").replace("+", "").strip()
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", s)
    if not m:
        raise ValueError(f"cannot read printed {p!r}")
    dec = len(s.split(".")[1]) if "." in s else 0
    return Decimal(s), dec


def rounded_all(x, how, dec):
    """The printed value may follow any common convention: half-up on the shortest decimal form, or half-up or half-even on the
    exact binary value (what Python's own formatting does). All three agree except at a decimal tie."""
    out = []
    for d, mode in ((Decimal(repr(float(x))), ROUND_HALF_UP), (Decimal(float(x)), ROUND_HALF_UP), (Decimal(float(x)), ROUND_HALF_EVEN)):
        out.append(rounded_d(d, how, dec, mode))
    return out


def rounded(x, how, dec):
    return rounded_d(Decimal(repr(float(x))), how, dec, ROUND_HALF_UP)


def rounded_d(d, how, dec, mode):
    if how in (None, "auto"):
        return d.quantize(Decimal(1).scaleb(-dec), rounding=mode)
    if how == "int":
        return d.quantize(Decimal(1), rounding=mode)
    if how == "floor":  # whole-number floor, as k is the floor of a cost ratio
        return d.quantize(Decimal(1), rounding=ROUND_FLOOR)
    kind, n = how.split(":")
    n = int(n)
    if kind == "dp":
        return d.quantize(Decimal(1).scaleb(-n), rounding=mode)
    if kind == "sf":
        if d == 0:
            return d
        e = d.adjusted() - n + 1
        return d.quantize(Decimal(1).scaleb(e), rounding=mode)
    raise ValueError(f"unknown rounding {how!r}")


def allowed_mask(text):
    covered = [False] * len(text)
    for rx, _ in ALLOW_RX:
        for m in rx.finditer(text):
            for i in range(m.start(), m.end()):
                covered[i] = True
    return covered


def bare_numerals(text):
    """Digit runs in `text` that no allow pattern covers."""
    covered = allowed_mask(text)
    out = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*", text):
        if not all(covered[i] for i in range(m.start(), m.end())):
            out.append(m.group(0))
    return out


def check_row(row, problems):
    rid = row.get("id", "?")
    def bad(msg):
        problems.append(f"{rid}: {msg}")
    for f in ("id", "text", "template", "values", "sources", "tier", "status"):
        if f not in row:
            bad(f"missing field {f}")
    if row.get("tier") not in TIERS:
        bad(f"tier {row.get('tier')!r} not one of {sorted(TIERS)}")
    for sid, src in row.get("sources", {}).items():
        if denied(src.get("path", "")):
            bad(f"source {sid} is a refused path")
            continue
        try:
            h = hashlib.sha256(blob(src["path"], src["commit"])).hexdigest()
            if h != src.get("sha256"):
                bad(f"source {sid} {src['path']}@{src['commit']}: sha256 {h[:12]} != pinned {str(src.get('sha256'))[:12]}")
        except Exception as e:  # noqa: BLE001
            bad(f"source {sid}: {e}")
    try:
        fresh = json.loads(json.dumps(row))
        resolve_row(fresh)
    except Exception as e:  # noqa: BLE001
        bad(f"resolve: {e}")
        return
    names = set()
    for v, fv in zip(row["values"], fresh["values"]):
        names.add(v["name"])
        if "raw" in v and v["raw"] != fv["raw"]:
            bad(f"{v['name']}: stored raw {v['raw']!r} != source {fv['raw']!r}")
        if v.get("hidden") and not v.get("printed"):
            continue  # a hidden input; one that keeps a printed text (printed only through {{id.name|N}}) is checked like any value
        if v.get("kind") == "str":
            if str(fv["raw"]) != v["printed"]:
                bad(f"{v['name']}: printed {v['printed']!r} != source text {fv['raw']!r}")
            continue
        try:
            p, dec = parse_printed(v["printed"])
            x = num(fv["raw"]) * v.get("scale", 1)
            options = rounded_all(x, v.get("round", "auto"), dec)
            r = next((o for o in options if o == p), options[0])
            if r != p:
                bad(f"{v['name']}: printed {v['printed']} but source gives {x!r} -> {options[0]}")
            for m in v.get("margins", []):
                if (x > m) != (r > m) or (x < m) != (r < m):
                    bad(f"{v['name']}: rounding {x!r} to {r} crosses {m}")
        except Exception as e:  # noqa: BLE001
            bad(f"{v['name']}: {e}")
    for f in row.get("facts", []):
        try:
            src = row["sources"][f["src"]]
            data = blob(src["path"], src["commit"])
            if "key" in f:
                got = walk(json.loads(data), f["key"])
            else:
                ms = list(re.finditer(f["regex"], data.decode("utf-8"), re.M))
                got = ms[0].group(f.get("group", 0)) if len(ms) == 1 else f"<regex matched {len(ms)} times>"
            if got != f["expect"]:
                bad(f"fact {f.get('what', '?')!r}: source has {got!r}, expected {f['expect']!r}")
        except Exception as e:  # noqa: BLE001
            bad(f"fact {f.get('what', '?')!r}: {e}")
    slots = set(re.findall(r"\{(\w+)\}", row.get("template", "")))
    names = {v["name"] for v in row["values"] if not v.get("hidden")}
    if slots - names:
        bad(f"template slots without values: {sorted(slots - names)}")
    if names - slots:
        bad(f"values not used in the template: {sorted(names - slots)}")
    if is_main_text(row):
        hit = MAIN_TEXT_BAR.search(row.get("text", ""))
        if hit:
            bad(f"main-text row carries {hit.group(0)!r} (settlement P-2: plain words in the main text)")
    raws = {v["name"]: v.get("raw") for v in row["values"]}
    for v in row["values"]:
        other = v.get("equals")  # a value that must equal another (e.g. a p-value at its bootstrap floor)
        if other:
            a, b = v.get("raw"), raws.get(other)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or abs(a - b) > 1e-12 * max(1.0, abs(a)):
                bad(f"value {v['name']} = {a!r} does not equal {other} = {b!r}")
    rendered = row["template"]
    for v in row["values"]:
        if not v.get("hidden"):
            rendered = rendered.replace("{" + v["name"] + "}", v["printed"])
    if rendered != row["text"]:
        bad("template does not render to text")
    masked = re.sub(r"\{\w+\}", "\u25a1", row["template"])
    left = bare_numerals(masked)
    if left:
        bad(f"bare numerals not in a value or the allow list: {left}")


def build_template(r, skip_allowed):
    text, out, pos = r["text"], [], 0
    allowed = allowed_mask(text)
    for v in r["values"]:
        if v.get("hidden"):
            continue
        p = v["printed"]
        def ok(i):
            if i > 0 and (text[i - 1].isdigit() or text[i - 1] == "."):
                return False  # inside a longer number
            if i + len(p) < len(text) and text[i + len(p)].isdigit():
                return False
            return not (skip_allowed and all(allowed[i:i + len(p)]))
        i = text.find(p, pos)
        while i >= 0 and not ok(i):
            i = text.find(p, i + 1)
        if i < 0 and skip_allowed:  # the value's only occurrences are design vocabulary: take the first plain one
            i = text.find(p, pos)
            while i >= 0 and ((i > 0 and (text[i - 1].isdigit() or text[i - 1] == ".")) or
                              (i + len(p) < len(text) and text[i + len(p)].isdigit())):
                i = text.find(p, i + 1)
        if i < 0:
            return None, v["name"], pos
        out.append(text[pos:i] + "{" + v["name"] + "}")
        pos = i + len(p)
    return "".join(out) + text[pos:], None, None


def cmd_template(path):
    """Place each value at its first occurrence after the previous one, preferring occurrences outside design vocabulary
    (e.g. a '8' that is a result, not the '8' in '4, 6, 8 steps'); if that cannot place every value, place them plainly."""
    rows = load(path)
    for r in rows:
        plain, miss, pos = build_template(r, False)
        pref, _, _ = build_template(r, True)
        def bare(t):
            return len(bare_numerals(re.sub(r"\{\w+\}", "\u25a1", t))) if t is not None else 10 ** 9
        if plain is None and pref is None:
            die(f"{r['id']}.{miss}: printed value not found after position {pos}")
        r["template"] = pref if bare(pref) < bare(plain) else plain  # plain order unless it leaves more bare numerals
    save(path, rows)
    print(f"templated {len(rows)} rows")


def cmd_pin(path, ref):
    rows = load(path)
    for r in rows:
        for src in r.get("sources", {}).values():
            if denied(src["path"]):
                die(f"{r['id']}: refused path {src['path']}")
            if not src.get("commit"):
                c = git("log", "-1", "--format=%H", ref, "--", src["path"]).decode().strip()
                if not c:
                    die(f"{r['id']}: {src['path']} is not on {ref}")
                src["commit"] = c[:12]
            src["sha256"] = hashlib.sha256(blob(src["path"], src["commit"])).hexdigest()
    save(path, rows)
    print(f"pinned {len(rows)} rows")


def cmd_resolve(path):
    rows = load(path)
    for r in rows:
        resolve_row(r)
    save(path, rows)
    print(f"resolved {sum(len(r['values']) for r in rows)} values in {len(rows)} rows")


def caption_block(src, block):
    """One caption from the captions file: the "### TAB-xx" block, with the review marks (⟨rows ...⟩, ‡, †) removed."""
    text = blob(src["path"], src["commit"]).decode("utf-8")
    m = re.search(r"^### " + re.escape(block) + r"\s*\n(.*?)(?=^### |\Z)", text, re.S | re.M)
    if not m:
        raise KeyError(f"no caption block {block}")
    t = re.sub(r"⟨[^⟩]*⟩", "", m.group(1)).replace("‡", "").replace("†", "")
    return " ".join(t.split())


def as_number(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    if isinstance(x, str) and re.fullmatch(r"[-+\u2212]?\d[\d,]*(\.\d+)?", x.strip()):
        return float(x.strip().replace(",", "").replace("\u2212", "-"))
    return None


def check_captions(rows, ids, problems):
    """Caption rows (Edith's ruling, latex-build-1): (1) the row's text equals its caption block rendered with the ledger's printed
    values; (2) every visible value equals one of the row's hidden caption-fact values, unless named in caption_exempt with a reason."""
    by_id = {r.get("id"): r for r in rows}
    for r in rows:
        cap = r.get("caption")
        if not cap or (ids and r.get("id") not in ids):
            continue
        try:
            raw = caption_block(r["sources"][cap["src"]], cap["block"])
        except Exception as e:
            problems.append(f"{r['id']}: caption: {e}")
            continue
        def tag(m):
            row = by_id.get(m.group(1))
            vals = {v["name"]: v for v in (row or {}).get("values", [])}
            if m.group(2) not in vals:
                problems.append(f"{r['id']}: caption tag {m.group(0)} does not resolve")
                return m.group(0)
            return tag_print(vals[m.group(2)], m.group(3))
        rendered = TAG_RE.sub(tag, raw)
        if rendered != r.get("text"):
            problems.append(f"{r['id']}: text differs from caption {cap['block']} at {r['sources'][cap['src']]['commit'][:7]}")
        if r.get("no_caption_facts"):
            continue  # a drawn figure: its numbers are tags on other rows, checked there
        facts = [as_number(v.get("raw")) for v in r["values"] if v.get("caption_fact")]
        exempt = r.get("caption_exempt", {})
        for v in r["values"]:
            if v.get("hidden") or v["name"] in exempt:
                continue
            x = as_number(v.get("raw"))
            if x is not None and not any(f is not None and abs(f - x) <= 1e-9 * max(1.0, abs(x)) for f in facts):
                problems.append(f"{r['id']}: caption value {v['name']} = {v['printed']} matches no caption fact")


def cmd_check(path, ids):
    rows = load(path)
    seen, problems = set(), []
    for r in rows:
        if r.get("id") in seen:
            problems.append(f"{r.get('id')}: duplicate id")
        seen.add(r.get("id"))
        if ids and r.get("id") not in ids:
            continue
        check_row(r, problems)
    for r in rows:
        for c in r.get("companions", []):
            if c not in seen:
                problems.append(f"{r['id']}: companion {c} is not in the ledger")
    check_captions(rows, ids, problems)
    n = len([r for r in rows if not ids or r.get("id") in ids])
    nv = sum(len(r.get("values", [])) for r in rows if not ids or r.get("id") in ids)
    for p in problems:
        print("FAIL", p)
    print(f"checked {n} rows, {nv} values: {len(problems)} problems")
    return 1 if problems else 0


def cmd_render(path, out):
    rows = load(path)
    lines = ["# Claims ledger (rendered from claims-ledger.jsonl; never edit by hand)", "",
             "| id | tier | status | text | values (printed ← source key) |", "|---|---|---|---|---|"]
    for r in rows:
        vals = "; ".join(f"{v['name']}={v['printed']} ← {r['sources'].get(v.get('src'), {}).get('path', 'formula')}"
                         for v in r["values"])
        lines.append(f"| {r['id']} | {r['tier']} | {r['status']} | {r['text'].replace('|', '/')} | {vals.replace('|', '/')} |")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


# D-161: standard wording replaces the project terms (Edith's conditions: one name per term, labels keep their meaning). `lint --vocab`
# reports each old term outside quotation marks; a term quoted in its one defining sentence ('an "arm" in the pre-registration') passes.
VOCAB = [
    (r"\barms?\b", "setting (\"design\" for multi-call, \"preset\" for Pilot 1)"),
    (r"\bbase puzzles?\b", "puzzle (defined as one puzzle in both shapes)"),
    (r"\btries\b|\b(?:one|a|single|each|per|\d+-)\s*try\b", "sample"),
    (r"\bequal[- ]money\b", "cost-matched"),
    (r"\b(?:Holm-)?declar(?:ed|ation|ations)\b", "shown no worse than X by more than N points (Holm-adjusted)"),
    (r"\bsame-model check\b", "the drift check (defined once)"),
    (r"\bthree-way readings?\b", "the pre-registered decision rule (defined once)"),
    (r"\brun windows?\b", "plain words (e.g. a separate run), defined once"),
    (r"\btiers?\b", "plain words (post hoc / exploratory / confirmatory)"),
    (r"\bnon-inferior(?:ity)?\b", "only in quotation marks (C-165); otherwise 'no worse than X by more than N points'"),
    (r"significant after Holm", "ruled out (D-161): 'shown no worse … (Holm-adjusted)'"),
]
VOCAB_RX = [(re.compile(p, re.I), why) for p, why in VOCAB]
QUOTED = re.compile(r"\u201c[^\u201d]*\u201d|\"[^\"\n]*\"|'[^'\n]{1,40}'")


DISPLAY_MATH = re.compile(r"(?ms)^\$\$[ \t]*\n(.*?)\n\$\$[ \t]*$")
MATH_CONSTANTS = {"0", "1", "100"}  # notation only: H_0/H_1, a branch scoring 0, \frac{1}{m}, x100 for points


def cmd_lint(draft, path):
    rows = {r["id"]: r for r in load(path)}
    text = open(draft, encoding="utf-8").read()
    problems = []
    for m in TAG_RE.finditer(text):
        r = rows.get(m.group(1))
        if not r or m.group(2) not in {v["name"] for v in r["values"]}:
            problems.append(f"tag {m.group(0)} does not resolve")
            continue
        if not str(r.get("status", "")).startswith(("edith_checked", "user_approved")):
            problems.append(f"tag {m.group(0)}: row status {r.get('status')} is not checked yet")
        if m.group(3) is not None:  # D-154: prose may round a value; the rounding is checked here
            v = {x["name"]: x for x in r["values"]}[m.group(2)]
            try:
                shown = tag_print(v, m.group(3))
            except ValueError as e:
                problems.append(f"tag {m.group(0)}: {e}")
                continue
            if re.search(r"[≤≥<>]\s*\$?$", text[:m.start()]):  # a bound is rounded outward, never to nearest (pr27 §20)
                problems.append(f"tag {m.group(0)}: a bound after an inequality sign may not use the rounding marker")
            x = num(v["raw"]) * v.get("scale", 1)
            shown_n = float(shown)
            for mg in v.get("margins", []):  # rounding must not move the value across a margin (e.g. -4.96 shown as -5)
                if (x > mg) != (shown_n > mg) or (x < mg) != (shown_n < mg):
                    problems.append(f"tag {m.group(0)}: {x!r} shown as {shown} crosses the margin {mg}")
    # display equations (a paragraph of "$$", LaTeX lines, "$$"): structure only. No tag inside, and no numeral other than the
    # constants 0, 1 and 100 (Vision's fix #11 equations: H_0, \frac{1}{m}, 1 - a_b, 100 for points); every value sits in the prose, tagged.
    for m in DISPLAY_MATH.finditer(text):
        body = m.group(1)
        if TAG_RE.search(body):
            problems.append(f"display equation holds a tag: {TAG_RE.search(body).group(0)} (values go in the sentence, tagged)")
        for n in re.findall(r"(?<![A-Za-z\\])\d+(?:\.\d+)?", TAG_RE.sub("", body)):
            if n not in MATH_CONSTANTS:
                problems.append(f"display equation holds the numeral {n!r} (only {sorted(MATH_CONSTANTS)} are allowed inside $$ … $$)")
    masked = TAG_RE.sub("\u25a1", DISPLAY_MATH.sub("\u25a1", text))
    if "--vocab" in sys.argv:  # D-161's standard wording: report every old project term outside quotation marks
        plain = QUOTED.sub(" ", re.sub(r"⟨[^⟩]*⟩", " ", masked))
        for rx, why in VOCAB_RX:
            hits = rx.findall(plain)
            if hits:
                problems.append(f"old term {hits[0]!r} x{len(hits)} (D-161: {why})")
    if "--appendix" not in sys.argv:
        for m in MAIN_TEXT_BAR.finditer(masked):
            problems.append(f"main text carries {m.group(0)!r} (settlement P-2)")
    for n in bare_numerals(masked):
        problems.append(f"bare numeral {n!r}")
    for p in problems:
        print("FAIL", p)
    print(f"{len(problems)} problems")
    return 1 if problems else 0


def main(argv):
    if len(argv) < 2:
        die(__doc__)
    cmd, rest = argv[1], argv[2:]
    if cmd == "template":
        cmd_template(rest[0])
    elif cmd == "pin":
        ref = rest[rest.index("--ref") + 1] if "--ref" in rest else "origin/main"
        cmd_pin(rest[0], ref)
    elif cmd == "resolve":
        cmd_resolve(rest[0])
    elif cmd == "check":
        ids = set(rest[rest.index("--ids") + 1:]) if "--ids" in rest else set()
        sys.exit(cmd_check(rest[0], ids))
    elif cmd == "render":
        cmd_render(rest[0], rest[1])
    elif cmd == "lint":
        sys.exit(cmd_lint(rest[0], rest[1]))
    else:
        die(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv)
