"""Top-up run tables: the plan's TAB-14 (settings and comparisons) and TAB-15 (counts). Every cell is read from the pinned top-up file
(`topup`) by key, plus, for the main-run comparator rows that Study 1 also reports (Opus-medium per shape, step voting on chain: accuracy,
interval, format compliance, costs) and a few caption counts, the Study 1 file (`main`); see paper_out_core.py for the rules. The top-up is exploratory: no Holm, no verdict. The accuracies and differences are in points (0-100) in this file.
TAB-14's note on the drift check (the spec's same-model check) cites the top-up run's specification (`topup_run_spec`, pinned text) for the check's setting and
comparison; each typed clause it rests on is guarded against the spec's line. Neither table prints a decision id, an internal record's
name or a C-/E-number, and no caption fact names an item number (`plain_print`); TAB-14 is main text (no item number anywhere).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

from .paper_out_core import (EMPTY, Cell, Ref, Source, Store, Table, YES_NO, ci_refs, derive, fa4_exact, fmt_sf, integer, interval, join_key,
                             joined, label, num, num_d, output, pct, pts, register_source, text_of, usd)
from .paper_out_names import MAIN_TEXT_ID, main_text
from .paper_out_ops import cell_ref, en_dash, group_starts, guard, line_of, single_value, unprinted

# The top-up run's specification, frozen with Lock 4: the path, commit and SHA-256 the stamped top-up file's `spec` field names (the
# file is unchanged since that commit). Its same-model section makes the check Haiku-medium at the main run's Haiku-medium settings;
# TAB-14's note cites it for that (Edith's Q26). Named for this module, so its pin does not depend on another module's.
TOPUP_SPEC = register_source(Source("topup_run_spec", "research/topup-run-spec.md", "9c007e5",
                                    "f048e73a8ccc843f9d575e4fd51a0d462d1e39d5c1635bbad5d1a493170b41c5", kind="text",
                                    what="The top-up run's specification, frozen with Lock 4 (its same-model check section)"))

DASH = label("—")
NBSP = "\u00a0"                 # a no-break space (printed "~"): a tag stays on its interval's line (Edith, proof 4, S1: "(exact)" wrapped to a second line)
# The supplement's full TAB-14 keeps the stamped values' two decimals (Edith, proof 3, C.37: its own Label cells cite Study 1's tables, which
# print accuracies, interval ends and compliance at two decimals, and its d column prints two); the paper's version rounds to one (D-161).
FULL_DP = 2
SHAPES = ("1x6", "6x1")
SHAPE_TEXT = {"1x6": "chains (1×6)", "6x1": "pieces (6×1)", "pooled": "pooled"}
ITEM24 = ("reporting", "group_b", "item_24", "table")
ZERO = "(zero width)"
FA4_EXACT = "(exact, post hoc)"            # free analysis 4's exact interval in place of a collapsed top-up bootstrap
C13_TIER = "unadjusted, exploratory, outside the pre-registered family"
S1_TIER = "comparator; pre-specified descriptive (Study 1, as TAB-04 prints it)"   # TAB-04 prints item 24 (no item number: main text)

# stamped arm ids -> display names (the comparator and challenger cells are read from the file's own fields). "{n}" is the number of
# main-run Haiku-medium samples the picker reads: it is read from the file (n_samples), never typed.
ARM_NAME = {
    "e2": "Haiku team", "h-pick8": "Haiku picker over {n} samples", "c13": "Step voting on pieces",
    "single8": "One Haiku-medium sample (the first {n} samples)", "vote8": "Haiku-medium vote of the first {n} samples",
    "any8": "Any of the first {n} Haiku-medium samples right (the ceiling for a picker)",
    "main-om": "Opus-medium, main run", "main-e3": "Step voting, main run",
    "c13 (step voting on pieces, top-up)": "Step voting on pieces, top-up run", "opus-med (main run)": "Opus-medium, main run",
    "same-model-check": "Drift check"}
SAME_WINDOW = "not needed (same run)"


def L(text: str) -> Cell:
    return label(text)


SAMPLES_RX = r"each of samples 1-(\d+) is picked"


def n_samples(S: Store) -> Cell:
    """The number of main-run Haiku-medium samples the picker reads, cut from the stamped picker-positions label ('how often each of
    samples 1-n is picked'). The build stops unless the stamped positions are exactly 1..n (plus 'none' and 'puzzles') at every shape and
    the stamped picker cost note speaks of the same n samples."""
    r = R(S, "topup", "picker_positions", "label")
    hits = re.findall(SAMPLES_RX, str(r.value))
    if len(hits) != 1:
        raise ValueError(f"picker_positions.label: {len(hits)} matches of {SAMPLES_RX!r}")
    n = int(hits[0])
    for sh in (*SHAPES, "pooled"):
        if set(S.keys("topup", join_key("picker_positions", sh))) != {str(i) for i in range(1, n + 1)} | {"none", "puzzles"}:
            raise ValueError(f"picker_positions.{sh}: the positions are not 1-{n}")
    if f"{n} samples" not in G(S, "topup", "costs", "picker_note"):
        raise ValueError(f"costs.picker_note does not speak of {n} samples")
    return Cell(hits[0], raw=r.value, refs=(r,), formula=f"the number cut from this stamped label by /{SAMPLES_RX}/")


def _name(S: Store, key: str, r: Optional[Ref]) -> Cell:
    tmpl = ARM_NAME[key]
    if "{n}" not in tmpl:
        return text_of(r, ARM_NAME) if r is not None else L(tmpl)
    label(tmpl.replace("{n}", ""))                     # the typed words around the count pass the label check
    n = n_samples(S)
    refs = ((r,) if r is not None else ()) + n.refs
    return Cell(tmpl.format(n=n.printed), raw=[r.value, n.raw] if r is not None else n.raw, refs=refs,
                formula=("the display name of the stamped arm id; " if r is not None else "") + "the sample count: " + str(n.formula))


def arm_name(S: Store, arm_id: str) -> Cell:
    """The display name of an arm this module lays out by id; a name holding the sample count reads it from n_samples."""
    return _name(S, arm_id, None)


def arm_of(S: Store, r: Ref) -> Cell:
    """The display name of a stamped arm-id field (kept as the cell's source); a name holding the sample count reads it from n_samples."""
    if r.value not in ARM_NAME:
        raise KeyError(f"{r.source}:{r.key} = {r.value!r} has no printed name")
    return _name(S, r.value, r)


def note(*parts: Any) -> List[Cell]:
    """A prose note as ONE cell: typed text (str) and read cells, keeping every part's source. A space goes between parts, except
    before , ; : . ) and after (, so no stray space lands before punctuation."""
    cells = [L(p) if isinstance(p, str) else p for p in parts]
    out = ""
    for c in cells:
        if not c.printed:
            continue
        if out and not (c.printed[0] in ",;:.)" or out.endswith("(")):
            out += " "
        out += c.printed
    refs = tuple(r for c in cells for r in c.refs)
    if not refs:
        return [L(out)]
    raws = [c.raw for c in cells if c.kind == "num"]
    return [Cell(out, raw=raws[0] if len(raws) == 1 else raws, refs=refs,
                 formula="; ".join(c.formula for c in cells if c.formula) or None)]


def R(S: Store, src: str, *segs: Any) -> Ref:
    return S.ref(src, join_key(*segs))


def G(S: Store, src: str, *segs: Any) -> Any:
    return S.get(src, join_key(*segs))


def P(r: Ref, dp: int = 1) -> Cell:
    """An accuracy or share in %, from points; one more decimal if rounding would reach 100."""
    return pct(r, dp=dp, from_proportion=False, bounds=(100.0,))


def CI(S: Store, segs: Sequence[Any], dp: int = 1, src: str = "topup") -> Cell:
    """A stamped 95% interval in %. Where the file stamps a collapsed one, free analysis 4's exact (Clopper–Pearson) interval replaces
    it, marked '(exact, post hoc)' (core.fa4_exact checks it is fa4's copy of that very interval); a collapsed one free analysis 4 does
    not cover is printed as stamped, flagged '(zero width)'. The notes say which marks are printed."""
    lo, hi = ci_refs(S, src, join_key(*segs))
    c = interval(lo, hi, dp=dp, bounds=(100.0,))
    if isinstance(lo.value, (int, float)) and isinstance(hi.value, (int, float)) and lo.value == hi.value:
        ex = fa4_exact(S, src, join_key(*segs[:-1])) if segs[-1] == "ci95" else None
        if ex is not None:
            return joined(interval(ex.lo, ex.hi, dp=dp, scale=ex.scale, bounds=(100.0,)), L(FA4_EXACT), sep=NBSP)
        return joined(c, L(ZERO), sep=NBSP)
    return c


def shp(s: str) -> Cell:
    return L(SHAPE_TEXT[s])


EXACT = "(exact)"


def CP(S: Store, sh: str, dp: int = 1) -> Cell:
    """The main run's one-try Opus-medium arm at one shape: Study 1's stamped exact (Clopper–Pearson) 95% interval (item 24, the key
    TAB-04 prints), in place of the top-up file's bootstrap. The top-up file rebuilds the same arm from the main run's log, so its
    stamped accuracy must equal item 24's (both of its stamped accuracies), or the build stops."""
    b = [*ITEM24, f"opus-med {sh}", "accuracy_cp95"]
    mine = G(S, "topup", "accuracy", "main-om", sh, "mean")
    if mine != G(S, "main", *b, "accuracy") or mine != G(S, "main", *ITEM24, f"opus-med {sh}", "accuracy_mean"):
        raise ValueError(f"main-om {sh}: the top-up accuracy is not item 24's; the exact interval would belong to another arm")
    lo, hi = ci_refs(S, "main", join_key(*b, "cp95"))
    return joined(interval(lo, hi, dp=dp, bounds=(100.0,)), L(EXACT), sep=NBSP)


def E3_CI(S: Store, dp: int = 1) -> Cell:
    """The main run's step voting (E3) on chain: Study 1's stamped cluster-bootstrap 95% interval (item 24, the key TAB-04 prints), so
    one result has one interval in the paper. The top-up file rebuilds the same arm from the main run's log; its stamped accuracy must
    equal item 24's, or the build stops."""
    b = [*ITEM24, "e3 1x6", "accuracy_interval"]
    mine = G(S, "topup", "accuracy", "main-e3", "1x6", "mean")
    if mine != G(S, "main", *b, "mean") or mine != G(S, "main", *ITEM24, "e3 1x6", "accuracy_mean"):
        raise ValueError("main-e3 1x6: the top-up accuracy is not item 24's; Study 1's interval would belong to another result")
    lo, hi = ci_refs(S, "main", join_key(*b, "ci95"))
    return interval(lo, hi, dp=dp, bounds=(100.0,))


# ---------------------------------------------------------------- what the printed words rest on, and what they must not name

SPEC_SM = r"^## \d+\. .*\b(same-model check)\b"          # the heading of the spec's section on the same-model check


def _spec_sm_line(S: Store, pattern: str, why: str) -> Cell:
    """A guard (unprinted) on the one line of the pinned top-up spec that matches `pattern` (one group), which must sit in the
    same-model check's section: below its heading and above the next section's."""
    src = TOPUP_SPEC.name
    n = line_of(S, src, pattern, expect=1)
    h = line_of(S, src, SPEC_SM, expect=1)
    nxt = [i for i in S.find_lines(src, r"^## ") if i > h]
    if not h < n < (nxt[0] if nxt else n + 1):
        raise ValueError(f"{src} line {n} is not in the same-model check's section (line {h})")
    return guard(cell_ref(S, src, n), pattern, why)


def same_model_spec(S: Store) -> List[Cell]:
    """The evidence (unprinted guard cells) behind TAB-14's typed clause that the same-model check, set by the top-up run's
    specification frozen with Lock 4, re-ran Haiku-medium at the main run's Haiku-medium settings (Edith's Q26: cite the spec that makes
    Haiku-medium the same-model arm). The build stops unless the stamped top-up file names this pinned spec (path, commit, SHA-256) as
    the spec frozen in lock 4, the spec's header says it is frozen in the Lock 4 tag, and its same-model section still says what the
    check runs. What it is compared with (the main run's first n samples) rests on `main_samples`, beside that clause."""
    s = TOPUP_SPEC
    stamped = R(S, "topup", "spec")
    if not str(stamped.value).startswith(f"{s.path} at {s.commit} (") or s.sha256 not in str(stamped.value):
        raise ValueError(f"topup: its stamped spec is not the pinned {s.name} ({s.path} at {s.commit})")
    head = line_of(S, s.name, r"frozen in `prereg-lock-4`", expect=1)
    sec = line_of(S, s.name, SPEC_SM, expect=1)
    return [guard(stamped, r"(the spec frozen in lock 4)", "the top-up analysis ran under the spec frozen in lock 4"),
            guard(cell_ref(S, s.name, head), r"(frozen in `prereg-lock-4`)", "the top-up spec is frozen at the Lock 4 tag"),
            guard(cell_ref(S, s.name, sec), SPEC_SM, "the spec has a section on the same-model check"),
            _spec_sm_line(S, r"^\*\*What it is:\*\* (Haiku-medium) ×\d+, at the main run's Haiku-medium settings exactly",
                          "the same-model check runs Haiku-medium at the main run's Haiku-medium settings")]


# the spec's line on what the check is compared with: the main run's Haiku-medium samples 1 to n of the same puzzles (n is cut)
SPEC_VS = r"^\*\*What it's compared with:\*\* the main run's Haiku-medium \*\*samples 1[–-](\d+)\*\* of the same (?:\d+) puzzles\."


def main_samples(S: Store) -> Cell:
    """The number of main-run Haiku-medium samples per puzzle the same-model check is set against (TAB-14 prints 'the main run's first
    n Haiku-medium samples on each of the same puzzles'): the stamped main-run calls of the check over its stamped puzzles. The cell
    also carries the guard on the pinned spec's line ('samples 1–n of the same N puzzles', in the same-model section). The build stops
    unless the quotient is a whole number equal to the spec's n and to the stamped tries per puzzle (the top-up side), and the spec's N
    is the stamped number of puzzles."""
    smc = ["same_model_check"]
    d = derive("main-run calls of the same-model check / its puzzles (the main run's Haiku-medium samples per puzzle it is set against)",
               lambda c, p: c / p, R(S, "topup", *smc, "refusals_truncations", "main", "calls"), R(S, "topup", *smc, "pooled", "n_puzzles"))
    vs = _spec_sm_line(S, SPEC_VS, "the same-model check is set against the main run's Haiku-medium samples 1 to n of the same puzzles")
    tries = G(S, "topup", *smc, "tries_per_puzzle")
    if not float(d.value).is_integer() or int(d.value) != int(vs.raw) or int(d.value) != tries:
        raise ValueError(f"same_model_check: main-run samples per puzzle {d.value} vs the spec's samples 1-{vs.raw} vs the stamped "
                         f"tries per puzzle {tries}: rewrite TAB-14's same-model note")
    spec_puzzles = re.search(r"of the same (\d+) puzzles", str(vs.refs[0].value))
    if spec_puzzles is None or int(spec_puzzles.group(1)) != G(S, "topup", *smc, "pooled", "n_puzzles"):
        raise ValueError("the spec's same-model puzzle count is not the stamped number of puzzles: rewrite TAB-14's same-model note")
    return joined(num_d(d, dp=0), vs)


# Printed words these tables must not hold (Edith's PO-1, Q22 and N-11): a decision id or an internal record's name anywhere (the
# decision register is not released); a keep-list C-number or an E-number anywhere (the arms print by name); an item number in a
# caption fact. TAB-14 is also checked whole by paper_out_names.main_text (no item number anywhere).
DECISION_ID = re.compile(r"\bD-\d")
INTERNAL_NAME = re.compile(r"(?i)LOG\.md|findings register|spend log|decision register")
CODE_ID = re.compile(r"\b[CE]-?\d")
ITEM_ID = re.compile(r"(?i)\bitems? \d")


def _printed_texts(t: Table) -> Iterator[Tuple[str, str]]:
    """(where, text) for every printed text of a table: its columns, cells, notes, caption facts, panel titles and panels."""
    for c in t.columns:
        yield "column", c.printed
    for r in t.rows:
        for c in r:
            yield "cell", c.printed
    for n in [*t.notes, *(t.main_notes or [])]:
        yield "note", " ".join(c.printed for c in n if c.printed)
    for k, v in [*t.caption.items(), *(t.main_caption or {}).items()]:
        yield f"caption fact {k!r}", " ".join(c.printed for c in v if c.printed)
    for name, p in t.panels:
        yield "panel title", name
        yield from _printed_texts(p)


def plain_print(t: Table) -> Table:
    """The build stops if a printed text holds a decision id, an internal record's name or a C-/E-number, or a caption fact holds an
    item number."""
    for where, text in _printed_texts(t):
        for rx in (DECISION_ID, INTERNAL_NAME, CODE_ID) + ((ITEM_ID,) if where.startswith("caption") else ()):
            if rx.search(text):
                raise ValueError(f"a {where} names an internal id or record ({rx.pattern}): {text!r}")
    return t


# ---------------------------------------------------------------- TAB-14


def _arm_rows(S: Store) -> List[List[Cell]]:
    """One row per arm and shape: accuracy [95%], format compliance, cost, cost per correct answer, tier. A comparator row says so in
    its Tier cell, beside its tier: the top-up file's own label for the rows the top-up analysis rebuilds from the main run's log (the
    first n samples, pooled Opus-medium); pre-specified descriptive (Study 1's item 24, as TAB-04 prints it) for the rows that print
    Study 1's own stamped values (Opus-medium per shape, step voting on chain)."""
    tier_top = text_of(R(S, "topup", "label"))
    tier_c13 = L(C13_TIER)
    tier_rebuilt = joined(L("comparator;"), tier_top)
    tier_s1 = L(S1_TIER)
    top = L("top-up run")
    main = L("main run, rebuilt from its log")
    main_s1 = L("main run (Study 1)")
    rows: List[List[Cell]] = []

    def acc(arm: str, sh: str) -> List[Cell]:
        a = ["accuracy", arm, sh]
        return [P(R(S, "topup", *a, "mean"), dp=FULL_DP), CI(S, [*a, "ci95"], dp=FULL_DP)]

    # ---- Haiku team (E2)
    for sh in (*SHAPES, "pooled"):
        flag = ["format_refusals_truncations_missing", "item_17_flags", f"e2 {sh}"]
        fmt = (num_d(derive("100 * format_ok / answered", lambda ok, n: 100.0 * ok / n, R(S, "topup", *flag, "format_ok"),
                            R(S, "topup", *flag, "answered")), dp=FULL_DP, bounds=(100.0,)) if sh != "pooled" else EMPTY)
        cp = ["costs", "per_puzzle", "e2", sh]
        rows.append([arm_name(S, "e2"), shp(sh), top, *acc("e2", sh), fmt, EMPTY, usd(R(S, "topup", *cp, "mean")), EMPTY,
                     usd(R(S, "topup", *cp, "cpc", "cpc")) if sh != "pooled" else EMPTY, tier_top])
    # ---- Haiku picker
    for sh in (*SHAPES, "pooled"):
        un = ["format_refusals_truncations_missing", "rates", f"h_pick8 {sh}", "unreadable_pick_among_answered"]
        readable = (num_d(derive("100 * (answered - unreadable) / answered", lambda n, c: 100.0 * (n - c) / n, R(S, "topup", *un, "answered"),
                                 R(S, "topup", *un, "count")), dp=FULL_DP, bounds=(100.0,)) if sh != "pooled" else EMPTY)
        tot = ["costs", "per_puzzle", "h-pick8-total", sh]
        ext = ["costs", "per_puzzle", "h-pick8-extra", sh]
        rows.append([arm_name(S, "h-pick8"), shp(sh), top, *acc("h-pick8", sh), EMPTY, readable, usd(R(S, "topup", *tot, "mean")),
                     usd(R(S, "topup", *ext, "mean")), usd(R(S, "topup", *tot, "cpc", "cpc")) if sh != "pooled" else EMPTY, tier_top])
    # ---- C13 (pieces only)
    cp = ["costs", "per_puzzle", "c13", "6x1"]
    rows.append([arm_name(S, "c13"), shp("6x1"), top, *acc("c13", "6x1"), EMPTY, EMPTY, usd(R(S, "topup", *cp, "mean")), EMPTY,
                 usd(R(S, "topup", *cp, "cpc", "cpc")), tier_c13])
    # ---- comparators the top-up analysis builds from the main run's first n Haiku-medium samples. Cost: for the vote, the picker's
    # total minus its extra (the n samples); none for the one try (not stamped) or for any-of-n (a ceiling that needs the answer key,
    # not a setup one could run, so it is given no price)
    for arm in ("single8", "vote8", "any8"):
        for sh in (*SHAPES, "pooled"):
            cost = _usd_from_derived(S, sh) if arm == "vote8" else EMPTY
            rows.append([arm_name(S, arm), shp(sh), main, *acc(arm, sh), EMPTY, EMPTY, cost, EMPTY, EMPTY, tier_rebuilt])
    # ---- Opus-medium and E3, main run. The one-try Opus-medium rows per shape print Study 1's own stamped values (item 24, as TAB-04
    # does: accuracy, exact interval, format compliance, costs; the top-up's rebuilt accuracy must be equal, see CP). The pooled row is
    # the top-up file's rebuild with its bootstrap (item 24 has no pooled row).
    for sh in (*SHAPES, "pooled"):
        if sh == "pooled":
            cost, cpc, fmt = EMPTY, EMPTY, EMPTY
            a, window, tier = acc("main-om", sh), main, tier_rebuilt
        else:
            rk = f"opus-med {sh}"
            cost = usd(R(S, "main", *ITEM24, rk, "cost_per_puzzle", "mean"))
            cpc = usd(R(S, "main", *ITEM24, rk, "cpc", "cpc"))
            fmt = pct(R(S, "main", *ITEM24, rk, "format_compliance", "format_compliance"), dp=FULL_DP, from_proportion=True,
                      bounds=(100.0,))
            ci = CP(S, sh, FULL_DP)                                          # checks the rebuilt accuracy equals item 24's first
            a, window, tier = [P(R(S, "main", *ITEM24, rk, "accuracy_mean"), dp=FULL_DP), ci], main_s1, tier_s1
        rows.append([arm_name(S, "main-om"), shp(sh), window, *a, fmt, EMPTY, cost, EMPTY, cpc, tier])
    # step voting (E3) on chain: Study 1's own stamped values (item 24), as TAB-04 prints them (E3_CI checks the rebuild is equal)
    ci = E3_CI(S, FULL_DP)
    rows.append([arm_name(S, "main-e3"), shp("1x6"), main_s1, P(R(S, "main", *ITEM24, "e3 1x6", "accuracy_mean"), dp=FULL_DP), ci, EMPTY, EMPTY,
                 usd(R(S, "main", *ITEM24, "e3 1x6", "cost_per_puzzle", "mean")), EMPTY, usd(R(S, "main", *ITEM24, "e3 1x6", "cpc", "cpc")),
                 tier_s1])
    return rows


def _usd_from_derived(S: Store, sh: str) -> Cell:
    """List cost per puzzle of the main-run samples the picker reads: the picker's total minus the picker's own call (three significant
    figures, as usd() prints a stamped cost)."""
    d = derive("h-pick8-total mean minus h-pick8-extra mean (the list cost of the main-run samples the picker reads)", lambda t, e: t - e,
               R(S, "topup", "costs", "per_puzzle", "h-pick8-total", sh, "mean"), R(S, "topup", "costs", "per_puzzle", "h-pick8-extra", sh, "mean"))
    return Cell(fmt_sf(d.value, 3), raw=d.value, refs=d.refs, formula=d.formula)


def _comparison_rows(S: Store) -> List[List[Cell]]:
    rows: List[List[Cell]] = []
    keys = [k for k in S.keys("topup", "comparisons") if k.startswith("topup:")]
    for k in keys:
        c = ["comparisons", k]
        lo, hi = ci_refs(S, "topup", join_key(*c, "ci95"))
        ch = arm_of(S, R(S, "topup", *c, "challenger"))
        cmp_ = arm_of(S, R(S, "topup", *c, "comparator"))
        cross = text_of(R(S, "topup", *c, "cross_window"), YES_NO)
        flag = text_of(R(S, "topup", *c, "same_model_flag")) if S.has("topup", join_key(*c, "same_model_flag")) else L(SAME_WINDOW)
        if G(S, "topup", *c, "cross_window") is False and S.has("topup", join_key(*c, "same_model_flag")):
            raise ValueError(f"{k}: a within-window comparison carries a same-model flag")
        rows.append([ch, cmp_, text_of(R(S, "topup", *c, "shape"), SHAPE_TEXT), integer(R(S, "topup", *c, "n")),
                     pts(R(S, "topup", *c, "d"), margin=float(G(S, "topup", "constants", "margin"))),
                     interval(lo, hi, dp=2, signed=True, bounds=(0.0, float(G(S, "topup", "constants", "margin")))),
                     cross, flag, text_of(R(S, "topup", "comparisons", "label"))])
    # step voting on pieces against the main run's Opus-medium (a separate block: Test 4's pieces counterpart)
    t4 = ["test4_pieces"]
    lo, hi = ci_refs(S, "topup", join_key(*t4, "as_deployed", "ci95"))
    rows.append([arm_of(S, R(S, "topup", *t4, "challenger")), arm_of(S, R(S, "topup", *t4, "comparator")),
                 text_of(R(S, "topup", *t4, "shape"), SHAPE_TEXT), integer(R(S, "topup", *t4, "as_deployed", "n")),
                 pts(R(S, "topup", *t4, "as_deployed", "d"), margin=float(G(S, "topup", *t4, "margin"))),
                 interval(lo, hi, dp=2, signed=True, bounds=(0.0, float(G(S, "topup", *t4, "margin")))),
                 _t4_cross_window(S), text_of(R(S, "topup", *t4, "same_model_flag")), L(C13_TIER)])
    return rows


T4_CROSS = "and Test 4 at pieces."


def _t4_cross_window(S: Store) -> Cell:
    """'yes' for step voting on pieces against the main run's Opus-medium. test4_pieces stamps no cross_window field (if it ever does,
    that field is printed), but the file's stamped list of cross-window comparisons (choices.cross_window) names it ('Test 4 at
    pieces'), and its methods note says it ran in a different window from its comparator; the build stops if either stops saying so."""
    t4 = ["test4_pieces"]
    if S.has("topup", join_key(*t4, "cross_window")):
        return text_of(R(S, "topup", *t4, "cross_window"), YES_NO)
    r = R(S, "topup", "choices", "cross_window")
    if not str(r.value).startswith("Cross-window comparisons") or T4_CROSS not in str(r.value):
        raise ValueError(f"choices.cross_window no longer lists {T4_CROSS!r} among the cross-window comparisons")
    if "a different window from its comparator" not in str(G(S, "topup", *t4, "methods_note")):
        raise ValueError("test4_pieces.methods_note no longer says the arm ran in a different window from its comparator")
    return Cell("yes", raw=r.value, refs=(r,), formula=f"yes: this stamped list of cross-window comparisons names {T4_CROSS[4:-1]!r}")


def _interval_note(S: Store, n_fa4: int) -> List[Cell]:
    """Which rows print Study 1's interval in place of the top-up file's bootstrap, and why. Free analysis 4's post hoc exact interval for
    the Opus-medium pieces cell is quoted and must equal the printed one (both are stamped; the build stops if they differ). The top-up
    file's own bootstraps for those rows are not printed (one result, one interval); the build checks the one called collapsed is.
    `n_fa4` is the number of other rows that print free analysis 4's exact interval in place of a collapsed top-up bootstrap."""
    ex = fa4_exact(S, "topup", "accuracy.main-om.6x1")        # checks fa4's copy is the top-up file's collapsed interval
    if ex is None or ex.scale != 1.0:
        raise ValueError("free analysis 4 has no exact interval in points for the top-up's Opus-medium pieces cell: rewrite the interval note")
    fa = [ex.lo.value, ex.hi.value]
    cp = G(S, "main", *ITEM24, "opus-med 6x1", "accuracy_cp95", "cp95")
    if any(abs(a - b) > 1e-9 for a, b in zip(fa, cp)):
        raise ValueError(f"fa4 exact95 {fa} is not item 24's cp95 {cp} for Opus-medium pieces")
    lo, hi = G(S, "topup", "accuracy", "main-om", "6x1", "ci95")
    if lo != hi:
        raise ValueError("the top-up bootstrap for Opus-medium on pieces no longer collapses: rewrite the interval note")
    if any("pooled" in k for k in S.keys("main", join_key(*ITEM24))):
        raise ValueError("item 24 now has a pooled row: the interval note no longer holds")
    rest = (". Every other row keeps the top-up file's cluster bootstrap" if not n_fa4 else
            ". Every other row keeps the top-up file's cluster bootstrap, or free analysis 4's exact interval where that collapsed "
            "(marked \"(exact, post hoc)\")")
    return note("\"(exact)\" marks an exact (Clopper–Pearson) 95% interval. The main-run rows that Study 1 also reports print the interval "
                "Study 1 stamps for the same result (as TAB-04 prints it), so the paper gives one interval per result: Opus-medium's "
                "one sample on chains and on pieces (exact) and step voting on chains (Study 1's cluster bootstrap). The top-up file's own "
                "bootstraps for these rows are not printed; for Opus-medium on pieces it collapsed to one value. The same exact interval for "
                "the Opus-medium pieces cell is stamped by free analysis 4 (post hoc):",
                interval(ex.lo, ex.hi, dp=FULL_DP, bounds=(100.0,)),
                rest + "; Study 1's pre-registered settings table (TAB-04) has no row for the top-up designs, the first",
                n_samples(S), "Haiku-medium samples or pooled shapes.")


def _picker_note_facts(S: Store) -> None:
    """The build stops if the stamped picker cost note no longer says what the picker cost notes (TAB-14 and its paper version) say."""
    pn = G(S, "topup", "costs", "picker_note")
    for fact in ("h-pick8-extra is the picker call alone", "the extra cost over vote@8's 8 samples", "h-pick8-total adds those 8 main-run samples",
                 "cost per correct answer is given for h-pick8-total only"):
        if fact not in pn:
            raise ValueError(f"costs.picker_note no longer says {fact!r}: rewrite the picker cost note")


def _picker_cost_note(S: Store) -> List[Cell]:
    """The picker's two cost figures in plain words (the stamped picker note names internal arm ids). The build stops if the stamped
    note no longer says what this sentence says."""
    _picker_note_facts(S)
    n = n_samples(S)
    return note("Picker cost: the list cost per puzzle is the total, the", n, "main-run samples plus the picker call; the extra list cost "
                "is the picker call alone, on top of the", n, "samples that the vote of", n, "also uses. Cost per correct answer is given "
                "for the total only.")


def _set_caption(S: Store) -> List[Cell]:
    """The puzzle set in plain words (set ids stay in the methods appendix): the top-up ran on Study 1's main-run set. The build stops
    unless Study 1 is at 6 steps and the top-up file's stamped set is the one every stamped Study 1 real-time puzzle id names."""
    sid = G(S, "topup", "inputs", "set", "set_id")
    sets = {re.sub(r"-\d+-(?:1x6|6x1)$", "", p) for p in G(S, "main", "reporting", "realtime", "puzzles")}
    if G(S, "main", "n") != 6 or sets != {sid}:
        raise ValueError(f"top-up set {sid!r} is not Study 1's ({sorted(sets)}, n = {G(S, 'main', 'n')})")
    return [L("the Study 1 main-run puzzle set at 6 steps, which the top-up run also used: each puzzle as a chain (1×6) and as "
              "pieces (6×1)")]


WITHIN = "topup:e2-e3:6x1"       # the one comparison the top-up file stamps as within the top-up window (its comparator field: C13)


def _study_caption(S: Store) -> List[Cell]:
    """TAB-14's study fact: the top-up arms against main-run comparators, and, on pieces, the Haiku team against step voting on pieces
    in the same window (Edith's §5: not every comparison is across run windows). The build stops unless that comparison is the only
    one the top-up file stamps as within its window (every other one, and Test 4 at pieces, is cross-window) and its stamped
    challenger, comparator and shape are the Haiku team, step voting on pieces and pieces."""
    keys = [k for k in S.keys("topup", "comparisons") if k.startswith("topup:")]
    within = [k for k in keys if G(S, "topup", "comparisons", k, "cross_window") is not True]
    if within != [WITHIN] or G(S, "topup", "comparisons", WITHIN, "cross_window") is not False:
        raise ValueError(f"within-window comparisons are {within}, not [{WITHIN!r}]: rewrite TAB-14's study fact")
    c = ["comparisons", WITHIN]
    if (G(S, "topup", *c, "challenger"), G(S, "topup", *c, "comparator"), G(S, "topup", *c, "shape")) != ("e2", "c13", "6x1"):
        raise ValueError(f"comparisons[{WITHIN!r}] is no longer the Haiku team against step voting on pieces: rewrite TAB-14's study fact")
    if _t4_cross_window(S).printed != "yes":
        raise ValueError("Test 4 at pieces is no longer cross-window: rewrite TAB-14's study fact")
    return note("Top-up run (6 steps, a separate run): the Haiku team, the Haiku picker and step voting on pieces, against main-run "
                "comparators; on", text_of(R(S, "topup", *c, "shape"), {"6x1": "pieces"}), ", also the Haiku team against",
                text_of(R(S, "topup", *c, "comparator"), {"c13": "step voting on pieces"}), ", both in the top-up run",
                guard(R(S, "topup", *c, "cross_window"), r"^(False)$", "the Haiku team and step voting on pieces are compared within "
                      "the top-up run"),
                "; the drift check between the two runs, for every comparison across them:", drift_status(S))


def drift_status(S: Store) -> Cell:
    """The one drift-check (same-model check) status every comparison across the two runs carries: the stamped flag of each top-up
    comparison marked cross-window and of Test 4 at pieces, all kept as the cell's sources. The build stops unless each of them stamps a
    flag and all the flags are the same (TAB-14's study fact gives one status; its paper version's d's are among these comparisons)."""
    keys = [k for k in S.keys("topup", "comparisons") if k.startswith("topup:") and G(S, "topup", "comparisons", k, "cross_window") is True]
    if any(not S.has("topup", join_key("comparisons", k, "same_model_flag")) for k in keys):
        raise ValueError("a cross-window comparison stamps no drift-check flag: rewrite TAB-14's study fact")
    if _t4_cross_window(S).printed != "yes":
        raise ValueError("Test 4 at pieces is no longer cross-window: rewrite TAB-14's study fact")
    refs = tuple(R(S, "topup", "comparisons", k, "same_model_flag") for k in keys) + (R(S, "topup", "test4_pieces", "same_model_flag"),)
    if len({r.value for r in refs}) != 1 or not isinstance(refs[0].value, str):
        raise ValueError(f"the cross-window comparisons' drift-check flags differ: {[r.value for r in refs]}; TAB-14's study fact gives one")
    return Cell(refs[0].value, raw=[r.value for r in refs], refs=refs,
                formula="the one status that every cross-window comparison's stamped drift-check (same-model check) flag gives; the "
                        "build checks they are all equal")


def _tier_caption(S: Store) -> List[Cell]:
    """TAB-14's tier fact (the full table's and its paper version's): the top-up file's label for the run; step voting on pieces'
    own label, as the full table's Tier column prints it (C13_TIER, for its arm row and for its d against Opus-medium, the pieces
    counterpart of Test 4); and the comparator rows that print Study 1's values. The paper version has no Tier column, so its rows'
    two tiers are named here (Edith's polish §9.3: a float that mixes tiers names them in its caption). The build stops unless the
    stamped Test 4 at pieces block still calls itself unadjusted, exploratory and outside the Holm family."""
    t4 = ["test4_pieces"]
    why = "Test 4 at pieces is unadjusted, exploratory and outside the pre-registered (Holm) family"
    return note(text_of(R(S, "topup", "label")), "; step voting on pieces, whose d against one Opus-medium answer from the main run is "
                "the pieces counterpart of Test 4, is",
                joined(L(C13_TIER), guard(R(S, "topup", *t4, "label"), r"^(unadjusted) \(exploratory, outside Holm\)$", why),
                       guard(R(S, "topup", *t4, "exploratory"), r"^(True)$", why),
                       guard(R(S, "topup", *t4, "outside_holm_family"), r"^(True)$", why)),
                "; the comparator rows that print Study 1's own values are pre-specified descriptive (Label column)")


def _n_base(S: Store) -> Cell:
    """Base puzzles per shape: one stamped n_base, which must be the same on every accuracy entry of the top-up file and on every
    item 24 row this table prints."""
    r = R(S, "topup", "accuracy", "e2", "1x6", "n_base")
    for a in S.keys("topup", "accuracy"):
        if a == "label":
            continue
        for sh in S.keys("topup", join_key("accuracy", a)):
            if G(S, "topup", "accuracy", a, sh, "n_base") != r.value:
                raise ValueError(f"accuracy.{a}.{sh}.n_base differs from {r.value}: one base-puzzle count no longer covers the table")
    for rk in ("opus-med 1x6", "opus-med 6x1", "e3 1x6"):
        if G(S, "main", *ITEM24, rk, "base_puzzles") != r.value:
            raise ValueError(f"item 24 {rk}: base puzzles differ from the top-up's {r.value}")
    return integer(r)


def _picker_calls(S: Store) -> Cell:
    """Picker calls per puzzle: the stamped designed calls over the stamped base puzzles on chains (the same on pieces, or the build
    stops). No key stamps the per-puzzle count, so it is derived."""
    ratio = {sh: G(S, "topup", "format_refusals_truncations_missing", "rates", f"h_pick8 {sh}", "designed_calls")
             / G(S, "topup", "accuracy", "h-pick8", sh, "n_base") for sh in SHAPES}
    if len(set(ratio.values())) != 1:
        raise ValueError(f"picker calls per puzzle differ by shape: {ratio}")
    return num_d(derive("designed calls / base puzzles", lambda c, b: c / b,
                        R(S, "topup", "format_refusals_truncations_missing", "rates", "h_pick8 1x6", "designed_calls"),
                        R(S, "topup", "accuracy", "h-pick8", "1x6", "n_base")), dp=0)


def _n_caption(S: Store) -> List[Cell]:
    """n: base puzzles per shape, and the tries or calls per puzzle behind each kind of row (stamped counts; the adaptive arms' total
    calls, since their calls per puzzle vary)."""
    if "pooled = each base's mean over its two shapes" not in G(S, "topup", "choices", "accuracy_names"):
        raise ValueError("choices.accuracy_names no longer defines pooled as each base's mean over its two shapes")
    if G(S, "main", *ITEM24, "opus-med 1x6", "cost_per_puzzle", "k") != G(S, "main", *ITEM24, "opus-med 6x1", "cost_per_puzzle", "k"):
        raise ValueError("Opus-medium's tries per puzzle differ by shape")
    for a in ("e2", "c13"):
        if not G(S, "topup", "completeness", "arms", a, "designed_rule").endswith("(an adaptive arm: a lower bound)"):
            raise ValueError(f"completeness.arms.{a} is no longer an adaptive arm")
    e3 = [*ITEM24, "e3 1x6", "refusals_and_truncations"]
    if "E3 has no designed count" not in G(S, "main", *e3, "label"):
        raise ValueError("item 24's step voting row no longer says it has no designed count")
    ca = ["completeness", "arms"]
    return note("puzzles per shape:", _n_base(S), "in every row (the pooled rows take each puzzle's mean over both shapes). "
                "Per puzzle, the picker makes", _picker_calls(S), "call and reads the first", n_samples(S), "main-run Haiku-medium samples, "
                "which the one-sample, vote and any-of rows also use; Opus-medium makes",
                integer(R(S, "main", *ITEM24, "opus-med 1x6", "cost_per_puzzle", "k")), "sample. The Haiku team and step voting are "
                "adaptive, so their calls per puzzle vary: the Haiku team made", integer(R(S, "topup", *ca, "e2", "final")), "calls over",
                integer(R(S, "topup", *ca, "e2", "puzzles")), "puzzle-shape pairs, step voting on pieces",
                integer(R(S, "topup", *ca, "c13", "final")), "over", integer(R(S, "topup", *ca, "c13", "puzzles")),
                "and step voting on chains (main run)", integer(R(S, "main", *e3, "calls_made")), "over",
                integer(R(S, "main", *ITEM24, "e3 1x6", "base_puzzles")), ".")


# ---------------------------------------------------------------- TAB-14's paper version (D-160, D-161; Vision's plan §3)

# The top-up run's three designs, per shape (the comparisons with Opus-medium and FIG-06 are per shape; the pooled rows stay in the
# supplement's full table), with their names in the paper's words (the shape is its own column; the picker's sample count is in its
# note, so the column stays narrow enough for the text width at \small) and their cost keys. Below them, Opus-medium per shape, the
# comparator of every d (the full table's main-run comparator rows, Study 1's own stamped values), so its accuracy and cost can be
# read beside the designs'. A design is a multi-call setting (D-161), so the first column, which also holds Opus-medium, is "Setting".
PAPER_DESIGNS = (("e2", SHAPES), ("h-pick8", SHAPES), ("c13", ("6x1",)))
PAPER_NAME = {"e2": "Haiku team", "h-pick8": "Haiku picker", "c13": "Step voting", "main-om": "Opus-medium"}
PAPER_SHAPE = {"1x6": "chains", "6x1": "pieces"}     # one label in every table's Shape column: "chains" (Edith, proof 4, Tables 8-12)
PAPER_COST = {"e2": "e2", "h-pick8": "h-pick8-total", "c13": "c13"}
T4_ARMS = ("c13 (step voting on pieces, top-up)", "opus-med (main run)", "6x1")   # test4_pieces: challenger, comparator, shape
PAPER_COST_COL = "List cost per puzzle ($)"

# OPEN (a must in Edith's check of batch (f), round 3; it needs the user's ruling, so it is not fixed here). US dollars print at 3
# significant figures (D-161 rule 2), as the full table, FIG-06's alt text and the body do; TAB-14's list costs per puzzle straddle 0.01,
# so the paper column mixes 5 and 4 decimals, against one number of decimals per column (rule 3; Edith's polish §2.8). Until the ruling,
# paper_decimals checks this column for 3 significant figures instead (column header -> why) and the build reports it as open.
# PAPER_USD_DP applies the ruling if it is a fixed number of decimals (5 prints 0.00623, 0.00649, 0.01033, 0.01015, 0.00351, 0.04024,
# 0.04812): set it, and the column leaves SF3_COLUMNS and must meet rule 3 like every other.
PAPER_USD_DP: Optional[int] = None
SF3_COLUMNS = {PAPER_COST_COL: "US dollars at 3 significant figures (D-161 rule 2) straddle 0.01; one number of decimals per column "
                               "(rule 3) would change them: OPEN, the user's ruling is pending"}


def _paper_usd(r: Ref) -> Cell:
    """A list cost in the paper version: 3 significant figures (usd, as the full table) until the ruling; PAPER_USD_DP fixed decimals
    after it."""
    return usd(r) if PAPER_USD_DP is None else num(r, dp=PAPER_USD_DP)


NUM_TOKEN = re.compile(r"[+\-\u2212]?\d[\d,]*(?:\.\d+)?")
NOTE_CHARS = 220          # D-160 rule 5: a short note prints on at most two lines, about 220 characters


def flat(*parts: Cell) -> Cell:
    """joined(), with the parts' raw values flattened into one list in printed order (a number, then an interval's two ends), so that
    each printed number sits beside its own raw value and ref. Parts with a formula are refused (one formula would cover them all)."""
    c = joined(*parts)
    raws: List[Any] = []
    for p in parts:
        if p.kind != "num":
            continue
        if p.formula:
            raise ValueError(f"flat(): {p.printed!r} carries a formula ({p.formula})")
        raws += list(p.raw) if isinstance(p.raw, list) else [p.raw]
    if [r.value for r in c.refs] != raws:
        raise ValueError(f"flat(): the raw values of {c.printed!r} do not match its refs")
    return Cell(c.printed, raw=raws[0] if len(raws) == 1 else raws, refs=c.refs)


def paper_decimals(t: Table, bounds: Sequence[float], sf3: Dict[str, str] = {}) -> List[str]:
    """D-161 rule 3 and Edith's polish §2.8 on a paper version, at build: in every column after the first, every printed number of the
    number cells has the same number of decimals. The one allowed exception is the one-more-decimal guard: a number one decimal longer
    that sits within one unit of the column's last place of a bound (0, 100 or a margin, `bounds`), where the shorter form would have
    reached or crossed it. A column named in `sf3` (an open exception, pending a ruling) is checked for 3 significant figures instead
    and reported as open. The build stops otherwise. Returns the guard cells ('column: cell') and the open columns ('OPEN column: why'),
    for the report."""
    guards: List[str] = []
    for j, col in enumerate(t.columns[1:], 1):
        toks = [(r[j].printed, m.group(0)) for r in t.rows if r[j].kind == "num" for m in NUM_TOKEN.finditer(r[j].printed)]
        if not toks:
            continue
        if col.printed in sf3:
            bad = [tk for _, tk in toks if len(re.sub(r"[^0-9]", "", tk).lstrip("0")) != 3]
            if bad:
                raise ValueError(f"{col.printed!r}: not 3 significant figures: {bad}")
            guards.append(f"OPEN {col.printed}: {sf3[col.printed]}")
            continue
        decs = [len(tk.split(".")[1]) if "." in tk else 0 for _, tk in toks]
        base = min(decs)
        for (cell, tk), d in zip(toks, decs):
            if d == base:
                continue
            v = float(tk.replace("\u2212", "-").replace(",", ""))
            if d != base + 1 or not any(abs(v - b) < 10 ** -base for b in bounds):
                raise ValueError(f"{col.printed!r}: {tk} in {cell!r} has {d} decimals, the column {base}, and is no guard cell")
            guards.append(f"{col.printed}: {cell}")
    return guards


def paper_note_lengths(t: Table) -> None:
    """D-160 rule 5: a paper version prints only its short notes (at most 2), each at most NOTE_CHARS characters; the build stops
    otherwise."""
    if len(t.notes) > 2 or sorted(t.short_notes) != list(range(len(t.notes))):
        raise ValueError(f"a paper version prints only its notes, at most 2, all short: {len(t.notes)} notes, short {t.short_notes}")
    for n in t.notes:
        text = " ".join(c.printed for c in n if c.printed)
        if len(text) > NOTE_CHARS:
            raise ValueError(f"a short note has {len(text)} characters (at most {NOTE_CHARS}): {text!r}")


def _paper_d(S: Store, arm: str, sh: str) -> Optional[Tuple[Cell, Ref, Cell, Ref]]:
    """d (one decimal, the one-more-decimal guard at 0 and the margin) and its 95% interval (positive end unsigned) of a design against
    the main run's one Opus-medium answer at this shape, with the comparison's stamped drift-check flag, the (unprinted) record that
    it compares two separate runs and the comparison's stamped comparator field; None where the top-up file stamps no such comparison
    (the picker). The Haiku team's are its
    comparisons against main-om; step voting on pieces' is the test4_pieces block (its only comparison with Opus-medium). Each is
    cross-window and on the table's puzzles, or the build stops."""
    hits = [k for k in S.keys("topup", "comparisons") if k.startswith("topup:")
            and (G(S, "topup", "comparisons", k, "challenger"), G(S, "topup", "comparisons", k, "comparator"),
                 G(S, "topup", "comparisons", k, "shape")) == (arm, "main-om", sh)]
    why = "this d compares two separate runs (cross-window)"
    if arm == "c13":
        t4 = ["test4_pieces"]
        if hits or (G(S, "topup", *t4, "challenger"), G(S, "topup", *t4, "comparator"), G(S, "topup", *t4, "shape")) != (*T4_ARMS[:2], sh):
            raise ValueError("step voting on pieces' comparison with Opus-medium is no longer test4_pieces alone")
        cross = _t4_cross_window(S)
        if cross.printed != "yes":
            raise ValueError("test4_pieces is no longer cross-window: rewrite the paper version's note on d")
        blk, m, flag = [*t4, "as_deployed"], float(G(S, "topup", *t4, "margin")), R(S, "topup", *t4, "same_model_flag")
        cross, cmp_ = unprinted(cross, why), R(S, "topup", *t4, "comparator")
    elif len(hits) == 1:
        c = ["comparisons", hits[0]]
        if G(S, "topup", *c, "cross_window") is not True:
            raise ValueError(f"{hits[0]} is not cross-window: rewrite the paper version's note on d")
        blk, m, flag = c, float(G(S, "topup", "constants", "margin")), R(S, "topup", *c, "same_model_flag")
        cross, cmp_ = guard(R(S, "topup", *c, "cross_window"), r"^(True)$", why), R(S, "topup", *c, "comparator")
    elif not hits:
        return None
    else:
        raise ValueError(f"{arm} {sh}: {len(hits)} comparisons with the main run's Opus-medium")
    if G(S, "topup", *blk, "n") != G(S, "topup", "accuracy", arm, sh, "n_base"):
        raise ValueError(f"{arm} {sh}: the comparison's puzzles are not the accuracy's")
    lo, hi = ci_refs(S, "topup", join_key(*blk, "ci95"))
    return flat(pts(R(S, "topup", *blk, "d"), dp=1, margin=m), interval(lo, hi, dp=1, signed=False, bounds=(0.0, m))), flag, cross, cmp_


def _no_d(S: Store, arm: str, sh: str) -> Cell:
    """The d cell of a design with no paired comparison with Opus-medium (the picker): a dash, as a number cell (so the d column stays
    a right-aligned number column, as TAB-01's joined dash cells do), whose record names the comparator field of every comparison the
    top-up file stamps for this design at this shape. The build stops if there is none or one of them is Opus-medium."""
    keys = [k for k in S.keys("topup", "comparisons") if k.startswith("topup:")
            and (G(S, "topup", "comparisons", k, "challenger"), G(S, "topup", "comparisons", k, "shape")) == (arm, sh)]
    refs = tuple(R(S, "topup", "comparisons", k, "comparator") for k in keys)
    if not refs or any(r.value == "main-om" for r in refs):
        raise ValueError(f"{arm} {sh}: comparators {[r.value for r in refs]}; the dash says it has none with Opus-medium")
    return Cell(DASH.printed, raw=[r.value for r in refs], refs=refs,
                formula="a dash: the top-up file stamps this design's comparisons at this shape with these comparators only, none "
                        "with Opus-medium (main-om)")


def _paper_om(S: Store, sh: str) -> Tuple[Cell, Cell, Cell]:
    """Opus-medium's accuracy, its 95% interval and its list cost per puzzle at one shape, from the keys the full table's 'Opus-medium,
    main run' row reads (Study 1's own stamped values, item 24, as TAB-04 prints them): the exact (Clopper–Pearson) interval, at one
    decimal. CP is called first: it stops the build unless the top-up file's rebuilt accuracy is item 24's (the comparator of every d)."""
    rk = f"opus-med {sh}"
    CP(S, sh)
    lo, hi = ci_refs(S, "main", join_key(*ITEM24, rk, "accuracy_cp95", "cp95"))
    return (P(R(S, "main", *ITEM24, rk, "accuracy_mean")), interval(lo, hi, dp=1, bounds=(100.0,)),
            _paper_usd(R(S, "main", *ITEM24, rk, "cost_per_puzzle", "mean")))


def _om_dash(sh: str, comparators: List[Ref]) -> Cell:
    """The d cell of Opus-medium's own row: a dash, as a number cell (so the d column stays a right-aligned number column), whose
    record names the stamped comparator field of every printed d at this shape. The build stops if there is none."""
    if not comparators:
        raise ValueError(f"Opus-medium {sh}: no printed d at this shape names it as comparator")
    return Cell(DASH.printed, raw=[r.value for r in comparators], refs=tuple(comparators),
                formula="a dash: this row is Opus-medium, the stamped comparator of every d printed at this shape")


def paper_ids(t: Table, oid: str) -> Table:
    """A paper version prints no internal id (Edith's polish §4.2): no pre-registration item number, keep-list C-number or E-number
    (MAIN_TEXT_ID, as main_text checks), no decision id or internal record's name (plain_print), in its columns, cells, notes or
    caption facts. The build stops otherwise."""
    bad = sorted({s for _, s in _printed_texts(t) if MAIN_TEXT_ID.search(s)})
    if bad:
        raise ValueError(f"{oid}'s paper version names an internal id: {bad}")
    return plain_print(t)


def _paper_14(S: Store, caption: Dict[str, List[Cell]]) -> Table:
    """TAB-14 in the paper (D-160; Vision's plan §3, Edith-accepted; D-161): Setting · Shape · Accuracy · its 95% interval · List cost per
    puzzle · d [95% interval] (d against Opus-medium, defined in note 0), for the top-up run's three designs per shape, then Opus-medium
    per shape (the comparator of every d; Edith's check of batch (f), round 3), at one decimal for % and points. The window, the tiers
    (step voting on pieces' own label among them) and the drift check's status are left to the caption facts (the full table's), as
    the design asks. The picker-only columns, format compliance, cost per correct answer, the pooled rows, the other main-run comparator
    rows and the comparisons panel stay in the supplement's full table. Every value is read from the same keys as the full table's, and
    each printed d is checked to be its design's accuracy minus Opus-medium's (rule 8: the merged rows agree)."""
    _picker_note_facts(S)
    n = n_samples(S)
    rows: List[List[Cell]] = []
    flags: List[Ref] = []
    cross: List[Cell] = []
    om = {sh: _paper_om(S, sh) for sh in SHAPES}
    vs_om: Dict[str, List[Ref]] = {sh: [] for sh in SHAPES}
    for arm, shapes in PAPER_DESIGNS:
        for sh in shapes:
            a = ["accuracy", arm, sh]
            acc, acc_ci = P(R(S, "topup", *a, "mean")), CI(S, [*a, "ci95"])
            if FA4_EXACT in acc_ci.printed or ZERO in acc_ci.printed:
                raise ValueError(f"{arm} {sh}: the accuracy interval is marked {acc_ci.printed!r}; the paper version has no note for it")
            d = _paper_d(S, arm, sh)
            if (d is None) != (arm == "h-pick8"):
                raise ValueError(f"{arm} {sh}: the note says only the picker has no paired comparison with Opus-medium")
            if d is not None:
                if abs(d[0].raw[0] - (acc.raw - om[sh][0].raw)) > 1e-9:
                    raise ValueError(f"{arm} {sh}: d {d[0].raw[0]} is not the accuracy {acc.raw} minus Opus-medium's "
                                     f"{om[sh][0].raw}; the Opus-medium row would not be the d's comparator")
                flags.append(d[1])
                cross.append(d[2])
                vs_om[sh].append(d[3])
            rows.append([L(PAPER_NAME[arm]), L(PAPER_SHAPE[sh]), acc, acc_ci,
                         _paper_usd(R(S, "topup", "costs", "per_puzzle", PAPER_COST[arm], sh, "mean")),
                         _no_d(S, arm, sh) if d is None else d[0]])
    for sh in SHAPES:
        rows.append([L(PAPER_NAME["main-om"]), L(PAPER_SHAPE[sh]), *om[sh], _om_dash(sh, vs_om[sh])])   # accuracy, interval, cost
    # the drift check's status is in the caption's study fact (a claim's companion, D-160 rule 5): it must cover every printed d
    status = {r.key for r in drift_status(S).refs}
    if any(f.key not in status for f in flags):
        raise ValueError("a printed d's drift-check flag is not among those the study fact's status covers")
    # The two notes print as one paragraph of at most two lines (proof 2: Edith's p. 38 row; typeset, they fill two lines, the second
    # 453.5 of 468 pt; the "with it" after "no paired comparison" is kept: without it the note would say the picker has no paired
    # comparison at all, and the picker's six paired comparisons are in the supplement's panel). Carried by the caption facts instead, so not repeated: the exact (Clopper–Pearson) interval for Opus-medium's one sample
    # and the paired BCa bootstrap of the differences (the interval fact), and Opus-medium's one sample per puzzle and the picker's one
    # call over the first samples it reads (the n fact).
    notes = [note("d: the design minus Opus-medium (main run), paired; each d compares two separate runs.", *cross),
             note("Picker cost: its call plus the", n, "main-run samples it reads. — marks no d (Opus-medium is the comparator; the picker "
                  "has no paired comparison with it).")]
    # Row groups (Edith §7.7; her p. 38 row): a setting's rows together, the setting printed once, and the Opus-medium comparator rows
    # set apart from the top-up designs above them.
    # The accuracy and its interval are two columns, so the estimates' decimal points line up (a joined "100.0 [95.5, 100.0]" sat 4.6 pt
    # left of its column, Edith's proof 4 LOW on Table 12, §2.8); d keeps its interval beside it (all its cells are as wide as each other)
    p = Table([L(c) for c in ("Setting", "Shape", "Accuracy (%)", "95% interval (%)", PAPER_COST_COL, "d (points) [95% interval]")],
              rows, notes, caption, short_notes=[0, 1], layout="float", groups=group_starts(rows, 0), once=[0])
    paper_decimals(p, (0.0, 100.0, float(G(S, "topup", "constants", "margin")), float(G(S, "topup", "test4_pieces", "margin"))),
                   SF3_COLUMNS if PAPER_USD_DP is None else {})
    paper_note_lengths(p)
    return paper_ids(p, "TAB-14")


@output("TAB-14")
@main_text
def tab_14(S: Store) -> Table:
    cols = ["Setting", "Shape", "Run", "Accuracy (%)", "Accuracy 95% interval", "Format compliance (%)", "Readable picks (%)",
            "List cost per puzzle ($)", "Extra list cost of the picker call alone ($)", "List cost per correct answer ($)", "Label"]
    ccols = ["Challenger", "Comparator", "Shape", "d (points)", "d 95% interval", "Across runs", "Drift check (top-up)", "Label"]
    smc = ["same_model_check"]
    sm_lo, sm_hi = ci_refs(S, "topup", join_key(*smc, "pooled", "ci95"))
    n = n_samples(S)
    # The comparison on pieces whose key names E3 is against C13 (its comparator field), within the top-up window. The second panel
    # prints every comparator from its field; the key itself is disclosed in the data README (TAB-22), not here.
    e2p = ["comparisons", "topup:e2-e3:6x1"]
    if (G(S, "topup", *e2p, "challenger"), G(S, "topup", *e2p, "comparator"), G(S, "topup", *e2p, "cross_window"),
            G(S, "topup", *e2p, "shape")) != ("e2", "c13", False, "6x1"):
        raise ValueError("comparisons['topup:e2-e3:6x1'] is no longer E2 against C13 on pieces within the top-up window: rewrite note 1")
    if S.has("main", join_key(*ITEM24, "e3 6x1")) or not S.has("main", join_key(*ITEM24, "e3 1x6")):
        raise ValueError("item 24 now has step voting on pieces (or not on chains): note 1 no longer holds")
    rows = _arm_rows(S)
    n_fa4 = sum(FA4_EXACT in c.printed for r in rows for c in r)
    notes = [
        note("On", text_of(R(S, "topup", *e2p, "shape"), {"6x1": "pieces"}), "the Haiku team is compared with",
             text_of(R(S, "topup", *e2p, "comparator"), {"c13": "step voting on pieces"}),
             ", both in the top-up run (across runs:", text_of(R(S, "topup", *e2p, "cross_window"), YES_NO),
             "); in the main run, step voting ran on chains only."),
        note("The top-up is", text_of(R(S, "topup", "label")), ". Step voting on pieces against one Opus-medium answer from the main "
             "run is the pieces counterpart of Test 4, not one of Tests 1–5: it is labelled", text_of(R(S, "topup", "test4_pieces", "label")),
             "and is outside the pre-registered family; the drift check between runs:", text_of(R(S, "topup", "test4_pieces", "same_model_flag")), "."),
        note("A comparison across runs sets a top-up setting against a main-run setting run at another time, and carries the status of "
             "the drift check between runs.",
             joined(L("The drift check, set by the top-up run's specification (frozen with Lock 4), re-ran Haiku-medium at the main "
                      "run's Haiku-medium settings on"), *same_model_spec(S)),
             integer(R(S, "topup", *smc, "bases")), "puzzles in both shapes (",
             integer(R(S, "topup", *smc, "pooled", "n_puzzles")), "puzzle-shape pairs,", integer(R(S, "topup", *smc, "tries_per_puzzle")),
             "samples each,", integer(R(S, "topup", *smc, "refusals_truncations", "top_up", "calls")),
             "calls) and set it against the main run's first", main_samples(S), "Haiku-medium samples on each of the same puzzles: "
             "pooled d (top-up minus main run) =",
             pts(R(S, "topup", *smc, "pooled", "d")),
             "points (95% interval", pts(sm_lo), "to", pts(sm_hi), "); mean output tokens per call changed by",
             num(R(S, "topup", *smc, "output_tokens", "relative_change"), dp=2, signed=True, scale=100.0, bounds=(0.0,), suffix="%"),
             "; status:", text_of(R(S, "topup", *smc, "flag", "status")), "(", text_of(R(S, "topup", *smc, "label")), ")."),
        note("Rule for the drift check between runs:", text_of(R(S, "topup", *smc, "flag", "rule")), "."),
        _picker_cost_note(S),
        note("A Label cell that starts with \"comparator\" marks a main-run comparator. The rows of the first", n, "Haiku-medium samples "
             "and the pooled Opus-medium row are "
             "rebuilt by the top-up analysis from the main run's log; the Opus-medium rows per shape and step voting on chains print Study 1's "
             "own stamped values (the rebuild gives the same accuracies). The vote of", n, "is priced at the list cost of its", n,
             "samples, the picker's stamped total minus its stamped extra. The one-sample row has no stamped cost. The any-of row is a ceiling "
             "that needs the answer key, not a setup one could run, so it is given no cost."),
        note("Format compliance is the share of answered replies whose format was ok, where a file stamps it: the Haiku team's (top-up file) "
             "and Opus-medium's (Study 1). Readable picks is the share of picker replies that named one of the samples. Other empty cells "
             "are not stamped."),
        _interval_note(S, n_fa4),
    ]
    caption = {
        "tier": _tier_caption(S),
        "study": _study_caption(S),
        "set": _set_caption(S),
        "n": _n_caption(S),
        "interval": note("95%. Accuracy: the top-up file's cluster bootstrap over puzzles,", integer(R(S, "topup", "constants", "draws")),
                         "resamples, except the main-run rows Study 1 also reports, which print Study 1's stamped interval (as TAB-04 prints it): exact "
                         "(Clopper–Pearson) for Opus-medium's one sample on chains and on pieces, Study 1's cluster bootstrap for step voting on "
                         "chains" + ("" if not n_fa4 else "; free analysis 4's exact (Clopper–Pearson, post hoc) interval where a top-up "
                                    "bootstrap collapsed") + ". Differences: paired BCa bootstrap, B =",
                         integer(R(S, "topup", "constants", "B"))),
        "price": [L("US dollars per puzzle at list price (Study 1's pre-registered price table)")]}
    if n_fa4:
        notes.append(note("\"(exact, post hoc)\" marks free analysis 4's exact (Clopper–Pearson) 95% interval over puzzles, printed in "
                          "place of a top-up bootstrap interval that collapsed to one value: post hoc, a presentation only, not a test."))
    if any(ZERO in c.printed for r in rows for c in r):
        notes.append(note("\"(zero width)\" marks a bootstrap interval that collapsed to one value; free analysis 4 stamps no exact "
                          "interval for it."))
    # 11 columns, two with long text: two parts on the sideways page, each with the setting and shape repeated, read in the order
    # identity, estimates, costs, label (0 setting, 1 shape, 2 run, 3-4 accuracy and its interval, 5-6 format compliance and readable
    # picks, 7-9 costs, 10 label): part 1 = run, accuracy, interval, format compliance, readable picks; part 2 = the costs and the label
    t = Table([L(c) for c in cols], rows, notes, caption, layout="split landscape", groups=group_starts(rows, 0),
              split_key=[0, 1], split_parts=[(None, [2, 3, 4, 5, 6]), (None, [7, 8, 9, 10])], font="footnotesize")
    crows = _comparison_rows(S)
    # the comparisons' puzzle count is one value in every row: a panel note, not a column (Edith's polish standard, section 7.3)
    puzzles = single_value([r[3] for r in crows], "TAB-14 comparisons: puzzles")
    crows = [r[:3] + r[4:] for r in crows]
    t.panels = [("Comparisons (d = challenger minus comparator, points)",
                 Table([L(c) for c in ccols], crows, [note("Every comparison is paired over", puzzles, "puzzles at its shape.")],
                       layout="landscape", groups=group_starts(crows, 0), font="footnotesize"))]
    t.main_table = _paper_14(S, caption)
    return plain_print(t)


# ---------------------------------------------------------------- TAB-15


def count_list(r: Ref) -> Cell:
    """The number of entries in a stamped list (an empty list prints 0)."""
    if not isinstance(r.value, list):
        raise TypeError(f"{r.source}:{r.key} is {r.value!r}, not a list")
    return Cell(str(len(r.value)), raw=r.value, refs=(r,), formula="the number of entries in the stamped list")

# row names start with a capital (Edith, proof 4, p. 121: one form for row names)
ORDINAL = {"1": "First sample", "2": "Second sample", "3": "Third sample", "4": "Fourth sample", "5": "Fifth sample", "6": "Sixth sample",
           "7": "Seventh sample", "8": "Eighth sample", "none": "No readable pick", "puzzles": "Total puzzle-shape pairs"}
# stamped adaptive-arm ids -> their names inside a sentence (TAB-15's note on adaptive arms; the panel's rows use ARM_NAME)
IN_SENTENCE = {"c13": "step voting on pieces", "e2": "the Haiku team"}


@output("TAB-15")
def tab_15(S: Store) -> Table:
    # One row per count, one column per shape (the picker panel's orientation): a row of the old layout was a shape, and its nine
    # narrow count columns wrapped their headers over two data rows. The headers of the old columns are the rows' first cells.
    cols = ["Count", "Chains (1×6)", "Pieces (6×1)"]
    by_shape: Dict[str, List[Tuple[str, Cell]]] = {}
    # four counts print one value at both shapes (the puzzles, those with a failed plan, the unfinished ones and those with a final
    # aggregator): a note, not rows (Edith's polish standard, section 7.3); single_value stops the build if that stops being true
    const: Dict[str, List[Cell]] = {"puzzles": [], "failed_plan": [], "unfinished": [], "final_aggregator": []}
    for sh in SHAPES:
        e = ["e2_counts", sh]
        ag = [*e, "aggregator_changes"]
        const["puzzles"].append(integer(R(S, "topup", *e, "puzzles")))
        const["failed_plan"].append(integer(R(S, "topup", *e, "failed_plans", "puzzles")))
        const["unfinished"].append(integer(R(S, "topup", *e, "unfinished_puzzles")))
        const["final_aggregator"].append(integer(R(S, "topup", *ag, "over_puzzles_with_a_final_aggregator")))
        by_shape[sh] = [("Puzzles with a failed task", integer(R(S, "topup", *e, "failed_tasks", "puzzles"))),
                        ("Failed tasks", integer(R(S, "topup", *e, "failed_tasks", "tasks"))),
                        ("Helper draws", integer(R(S, "topup", *e, "helper_draws"))),
                        ("Aggregator changed the helpers' answer", integer(R(S, "topup", *ag, "changed"))),
                        ("Helpers' results right, final answer wrong", integer(R(S, "topup", *ag, "right_chain_turned_wrong"))),
                        ("Helpers' results wrong, final answer right", integer(R(S, "topup", *ag, "wrong_chain_turned_right"))),
                        ("Changed: aggregator unreadable", integer(R(S, "topup", *ag, "of_which_aggregator_unreadable"))),
                        ("Changed: helpers had no result", integer(R(S, "topup", *ag, "of_which_helpers_had_no_result")))]
    if len({tuple(h for h, _ in by_shape[sh]) for sh in SHAPES}) != 1:
        raise ValueError("TAB-15: the counts differ between the two shapes")
    rows: List[List[Cell]] = [[L(h), by_shape["1x6"][i][1], by_shape["6x1"][i][1]] for i, (h, _) in enumerate(by_shape["1x6"])]
    one = {k: single_value(v, f"TAB-15: {k}") for k, v in const.items()}
    # picker positions: rows are the positions (spelled out), columns the shapes
    pcols = ["Picked", "Chains (1×6)", "Pieces (6×1)", "Pooled"]
    prows: List[List[Cell]] = []
    for k in S.keys("topup", "picker_positions.1x6"):
        if k not in ORDINAL:
            raise KeyError(f"picker position {k!r} has no printed name")
        prows.append([L(ORDINAL[k]), integer(R(S, "topup", "picker_positions", "1x6", k)), integer(R(S, "topup", "picker_positions", "6x1", k)),
                      integer(R(S, "topup", "picker_positions", "pooled", k))])
    # completeness
    ccols = ["Setting", "Designed calls", "Final calls", "Puzzle-shape pairs", "Pairs unfinished"]
    crows: List[List[Cell]] = []
    completed: List[Cell] = []
    missing: List[Cell] = []
    adaptive: List[Cell] = []
    for a in S.keys("topup", "completeness.arms"):
        c = ["completeness", "arms", a]
        # "Completed" (yes) and "Missing calls" (0) print one value for every setting: a panel note, not columns (section 7.3)
        completed.append(text_of(R(S, "topup", *c, "completed"), YES_NO))
        missing.append(integer(R(S, "topup", *c, "missing")))
        crows.append([arm_of(S, R(S, "topup", *c, "arm")),
                      integer(R(S, "topup", *c, "designed")), integer(R(S, "topup", *c, "final")),
                      integer(R(S, "topup", *c, "puzzles")) if S.has("topup", join_key(*c, "puzzles")) else DASH,
                      integer(R(S, "topup", *c, "puzzles_unfinished")) if S.has("topup", join_key(*c, "puzzles_unfinished")) else DASH])
        if S.has("topup", join_key(*c, "designed_rule")):
            # the stamped rule names code functions; the note says it in plain words, and the build stops if the rule changes kind
            if not G(S, "topup", *c, "designed_rule").endswith("(an adaptive arm: a lower bound)"):
                raise ValueError(f"completeness.arms.{a}.designed_rule is no longer an adaptive arm's lower bound: rewrite the note")
            adaptive.append(text_of(R(S, "topup", *c, "arm"), IN_SENTENCE))     # the arm's name inside the note's sentence
    if len(adaptive) != 2:
        raise ValueError(f"{len(adaptive)} adaptive arms in completeness: the designed-calls note names two")
    base = G(S, "topup", "e2_counts", "1x6", "puzzles")
    if any(G(S, "topup", "e2_counts", sh, "puzzles") != base or G(S, "topup", "picker_positions", sh, "puzzles") != base for sh in SHAPES):
        raise ValueError("the Haiku team's and the picker's puzzles per shape differ: the caption's one base-puzzle count no longer holds")
    notes = [
        note("At each shape:", one["puzzles"], "puzzles,", one["failed_plan"], "of them with a failed plan,", one["unfinished"],
             "unfinished, and", one["final_aggregator"], "with a final aggregator."),
        note("Counts only; they are exploratory and carry no test. Aggregator changes are counted over puzzles with a final aggregator: a change "
             "is a puzzle whose final answer (the aggregator's graded whole answer) is not the helpers' results taken in order. \"Helpers' "
             "results\" means the helpers' answers in order, at either shape; it is not the chain shape."),
        note("A setting is \"not completed\" if a designed call has no final record. Settings not completed:",
             count_list(R(S, "topup", "completeness", "not_completed")), "."),
        note("Adaptive designs (their number of calls is not fixed in advance):", adaptive[0], "and", adaptive[1], ". Their designed calls "
             "are the final calls plus the calls the runner's own logic would still have made when the analysis ran: a lower bound."),
        note("Picker positions are", en_dash(text_of(R(S, "topup", "picker_positions", "label"))), "."),
    ]
    caption = {
        "tier": [L("exploratory counts")],
        "study": [L("Top-up run (6 steps, a separate run)")],
        "set": _set_caption(S),
        "n": note("puzzles per shape:", integer(R(S, "topup", "e2_counts", "1x6", "puzzles")), "(Haiku team and picker). Per puzzle, "
                  "the Haiku team's calls vary (adaptive; the completeness panel gives its calls in all) and the picker makes",
                  _picker_calls(S), "call over the first", n_samples(S), "main-run Haiku-medium samples. The drift check between runs re-ran",
                  integer(R(S, "topup", "same_model_check", "bases")), "puzzles in both shapes,",
                  integer(R(S, "topup", "same_model_check", "tries_per_puzzle")), "samples each."),
        "interval": [L("none (counts)")],
        "price": [L("not applicable (no cost column)")]}
    t = Table([L(c) for c in cols], rows, notes, caption, layout="float", groups=[3])
    t.panels = [("Picker positions (counts of puzzle-shape pairs)", Table([L(c) for c in pcols], prows, layout="float")),
                ("Completeness by setting (calls)", Table([L(c) for c in ccols], crows, [
                    note("For every setting listed, completed:", single_value(completed, "TAB-15: completed"), "; missing calls:",
                         single_value(missing, "TAB-15: missing calls"), "."),
                    note("A dash: the setting's completeness record gives no value for that column.")],   # Edith, M2-6
                    layout="float"))]
    return plain_print(t)
