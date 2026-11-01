"""Every table and figure of the paper, built by script from the locked result files (D-118, D-120; the master plan's "Tables and
figures (for Friday)", decisions/briefings/2026-10-15-compiler/master-plan.md at 7b43f91, raw plan-result.json `plan.tables_figures`).

    python3 -m harness.analysis.paper_outputs --out data/paper-outputs            # everything, with MANIFEST.json and MANIFEST.md (development repository only)
    python3 -m harness.analysis.paper_outputs --out <dir> --only TAB-02,FIG-01      # a few outputs, no manifest (for development)
    python3 -m harness.analysis.paper_outputs --from-disk --out <empty dir>          # a copy without the history (D-207; see below); never --out data/paper-outputs

What it writes, per output id (TAB-nn, FIG-nn), all deterministic (the same sources and code give the same bytes):
- a table: `<id>.csv` (the printed cells), `<id>.tex` (booktabs tabular) and `<id>.cells.json` (every cell with its raw value and its
  source and key, in the claims ledger's form: research/paper-notes/claims-ledger-format.md);
- a figure: `<id>.pdf`, `<id>.png`, `<id>.alt.txt` (alt text for arXiv's HTML) and `<id>.data.json` (every plotted value with its
  source and key);
- an output that waits on a free analysis the user has not yet approved: `<id>.stub.json` (what it waits for and why), plus the part
  that can be built now, if any, as `<id>.partial.*` (none now: the two plan ids whose analyses were never approved, TAB-32 and TAB-33,
  are dropped, paper_out_core.DROPPED, and listed under "dropped" in the manifest);
- `MANIFEST.json`: per output its plan entry (title, section, label), status, the SHA-256 of each file and the pinned sources used;
  `MANIFEST.md`: the same as a table for reading.

The pinned sources, the key syntax and the no-typed-numbers rule are in `paper_out_core.py`; the figure style in `paper_out_style.py`.
`--from-disk` (or PARETO_FROM_DISK=1, or automatically when the repository lacks a pinned commit) reads each pinned file from its path
instead of its commit, SHA-256 checked as ever; an output whose files the copy does not hold, or whose checks read the history, refuses
(`NotShipped`, `NeedsHistory`) and ships as built.
No model or API call. Never reads data/tasks/ or .env.
"""

from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import paper_out_core as core
from .paper_out_core import FigureOut, Meta, Store, Stub, Table

MODULES = ("paper_out_overview", "paper_out_study1", "paper_out_study1b", "paper_out_topup", "paper_out_ops", "paper_out_disclosure",
           "paper_out_timeline", "paper_out_fa_votes", "paper_out_fa_checks", "paper_out_fa_desc", "paper_out_derived", "paper_out_cost_target", "paper_out_fa_more", "paper_out_fig00",
           "paper_out_figures", "paper_out_main")
GENERATOR = "harness/analysis/paper_outputs.py"


def load_registry(modules: Optional[Sequence[str]] = None) -> Dict[str, core.Spec]:
    for m in list(modules or MODULES) + ["paper_out_anon"]:          # the anonymous variants' module registers its own source
        try:
            importlib.import_module(f"{__package__}.{m}")
        except ModuleNotFoundError as e:
            if e.name != f"{__package__}.{m}":
                raise
    return core.REGISTRY


def _meta_doc(m: Meta) -> Dict[str, str]:
    return {"id": m.id, "kind": m.kind, "title": m.title, "section": m.section, "label": m.label}


def _write(out: Path, name: str, data: bytes, files: Dict[str, str]) -> None:
    (out / name).write_bytes(data)
    files[name] = core.sha256(data)


def _write_table(out: Path, oid: str, stem: str, t: Table, meta: Meta, used: Dict[str, Any], files: Dict[str, str],
                 style: Optional[Dict[str, List[str]]] = None, enforce: bool = True) -> None:
    t.check()
    _style(oid, stem, t, style, enforce)
    if "." not in stem:                                   # a supplement table: its sideways units share pages where they fit
        core.plan_packing(t)
    _write(out, f"{stem}.csv", core.table_csv(t), files)
    _write_tex(out, oid, stem, t, f"{stem}.cells.json", files)
    doc = {"output": _meta_doc(meta), "sources": used, "table": core._cells_doc(t),
           "panels": [{"name": n, "table": core._cells_doc(p)} for n, p in t.panels]}
    _write(out, f"{stem}.cells.json", core.dumps(doc), files)
    for i, (n, p) in enumerate(t.panels, 1):
        p.check()
        _write(out, f"{stem}.panel{i}.csv", core.table_csv(p), files)
        _write_tex(out, f"{oid} panel {i}: {core.ID_REF.sub(lambda m: '⟦' + m.group(1) + '⟧', n)}", f"{stem}.panel{i}", p,
                   f"{stem}.cells.json, panels[{i - 1}]", files)


def _style(oid: str, stem: str, t: Table, style: Optional[Dict[str, List[str]]], enforce: bool = True) -> None:
    """Edith's polish-standard table checks (paper_out_lint) on a table and its panels. A paper version (<id>.main, or a body table
    printed as is) with any problem not waived in paper_out_lint.WAIVERS refuses the build; a full table's problems are recorded in
    the manifest (the supplement pass fixes them). An old narrow version (paper_out_narrow, being replaced) is recorded, not refused."""
    from . import paper_out_lint as lint
    # while a fix pass is under way, PAPER_STYLE_RECORD_ONLY=1 records a paper version's problems in the manifest instead of refusing
    enforce = enforce and not os.environ.get("PAPER_STYLE_RECORD_ONLY")
    for name, tab in [(stem, t)] + [(f"{stem}.panel{i}", p) for i, (_, p) in enumerate(t.panels, 1)]:
        probs = lint.unwaived(name, lint.table_problems(tab, oid, name))
        if probs and enforce and lint.is_paper(oid, name, tab):
            raise ValueError(f"{name}: the paper's version fails the polish standard's table checks: {probs}")
        if probs and style is not None:
            style[name] = probs


def _write_tex(out: Path, oid: str, stem: str, t: Table, cells: str, files: Dict[str, str]) -> None:
    """<stem>.tex, or for a split table <stem>.tex, <stem>.part2.tex, ... (the layout mark on the first file only; Vision's converter
    sets the rest as "(continued)" floats with the same number). A long table carries \\caption{⟦CAPTION⟧}\\label{⟦LABEL⟧}, which the
    converter fills per build (tab:<id>, or tab:<id>-full for a full table in the paper's appendix)."""
    if t.layout in core.SPLITS and t.split_parts:
        for k, part in enumerate(core.split_tables(t)):
            name = stem if k == 0 else f"{stem}.part{k + 1}"
            _write(out, f"{name}.tex", core.table_tex(part, oid if k == 0 else _continued(oid), cells=cells, mark=k == 0), files)
    else:
        _write(out, f"{stem}.tex", core.table_tex(t, oid, cells=cells), files)


def _continued(oid: str) -> str:
    """A split panel's later part carries its title as "(continued)": the converter prints the header line's title above each part
    ("Panel 4: (continued)" under "Table SN: (continued)"), and the full title printed twice read as two panels (Edith, proof 4 D-168,
    pp. 83 and 90). A table's own header line (no panel title) is unchanged."""
    m = re.match(r"^(TAB-\d+ panel \d+): ", oid)
    return f"{m.group(1)}: (continued)" if m else oid


def _anon_title(title: str) -> str:
    """A panel's title in the anonymous copy: "(anonymous copy)" joins the title's own closing parenthesis ("Runs (every run that sent an
    API call; anonymous copy)") instead of standing beside it (Edith, proof 4 D-168, pp. 37-38)."""
    return title[:-1] + "; anonymous copy)" if title.endswith(")") else title + " (anonymous copy)"


def _write_anon(out: Path, oid: str, t: Table, meta: Meta, used: Dict[str, Any], files: Dict[str, str]) -> List[str]:
    """The anonymous TMLR copy's variant (paper_out_anon): `<id>.anon.tex` and each panel's `<id>.panelN.anon.tex` (the names Vision's
    build pairs with `<id>.tex` and `<id>.panelN.tex`), their CSVs and one cells file with the rules' firing counts."""
    t.check()
    core.plan_packing(t)
    names = [f"{oid}.anon.tex"]
    _write(out, f"{oid}.anon.csv", core.table_csv(t), files)
    if t.layout in core.SPLITS and t.split_parts:
        # a split table: X.anon.tex, X.part2.anon.tex, ... (the converter swaps each named part for its twin; the layout mark on the
        # first file only), as _write_tex writes the named parts
        for k, part in enumerate(core.split_tables(t)):
            name = f"{oid}.anon" if k == 0 else f"{oid}.part{k + 1}.anon"
            _write(out, f"{name}.tex", core.table_tex(part, f"{oid} (anonymous copy)", cells=f"{oid}.anon.cells.json", mark=k == 0), files)
            if k:
                names.append(f"{name}.tex")
    else:
        _write(out, f"{oid}.anon.tex", core.table_tex(t, f"{oid} (anonymous copy)", cells=f"{oid}.anon.cells.json"), files)
    doc = {"output": _meta_doc(meta), "sources": used, "anonymous": True, "rules_fired": getattr(t, "anon_rules", {}),
           "table": core._cells_doc(t), "panels": [{"name": n, "table": core._cells_doc(p)} for n, p in t.panels]}
    _write(out, f"{oid}.anon.cells.json", core.dumps(doc), files)
    for i, (n, p) in enumerate(t.panels, 1):
        p.check()
        _write(out, f"{oid}.panel{i}.anon.csv", core.table_csv(p), files)
        _write(out, f"{oid}.panel{i}.anon.tex", core.table_tex(p, f"{oid} panel {i}: {_anon_title(n)}",
                                                               cells=f"{oid}.anon.cells.json, panels[{i - 1}]"), files)
        names.append(f"{oid}.panel{i}.anon.tex")
    return names


def _cites(res: Any, source: str) -> bool:
    """Does any cell of a built table or figure (with its panels and main-text notes) name `source`? The plan is read for every
    output's title, so it is listed among an output's sources only when a printed cell cites it."""
    if isinstance(res, Table):
        docs: List[Any] = [core._cells_doc(res)] + [core._cells_doc(p) for _, p in res.panels]
        docs += [[[c.record() for c in n] for n in (res.main_notes or [])],
                 {k: [c.record() for c in v] for k, v in (res.main_caption or {}).items()}]
    elif isinstance(res, FigureOut):
        docs = [res.points, [c.record() for c in res.alt], {k: [c.record() for c in v] for k, v in res.caption.items()}]
        for _, v in res.variants:
            docs += [v.points, [c.record() for c in v.alt], {k: [c.record() for c in w] for k, w in v.caption.items()}]
    else:
        return False
    return any(r.get("source") == source for d in docs for c in _cell_records(d) for r in (c.get("refs") or []))


def _floor_note(t: Table) -> None:
    """A table (or panel) that prints a p at the bootstrap's floor ("≤", core.pvalue_bound) carries core.FLOOR_NOTE once, as its last
    note unless a builder already gave it; the main-text version gets it with the rest of the notes."""
    def floored(tab: Table) -> bool:
        return any(c.printed.startswith("\u2264 ") and (c.formula or "").startswith("p at the bootstrap's floor") for r in tab.rows for c in r)
    for tab in [t] + [p for _, p in t.panels]:
        if floored(tab) and not any(core.FLOOR_NOTE in c.printed for n in tab.notes for c in n):
            tab.notes.append([core.label(core.FLOOR_NOTE + ".")])
            if tab is t and t.main_notes is not None:
                t.main_notes.append([core.label(core.FLOOR_NOTE + ".")])


AS_BUILT = "as built"       # status of an output a copy without the development history cannot rebuild (D-207; Edith's M5)


def _shipped_entry(repo: Path, oid: str) -> Dict[str, Any]:
    """The entry the repository's own data/paper-outputs/MANIFEST.json holds for `oid` ({} if it has none): what an "as built" output keeps
    (its plan fields, sources and file hashes), so the output is checked by SHA-256 against what was built with the history."""
    p = Path(repo) / "data" / "paper-outputs" / "MANIFEST.json"
    if not p.is_file():
        return {}
    return next((dict(e) for e in core.json.loads(p.read_text("utf-8"))["outputs"] if e["id"] == oid), {})


def _as_built(repo: Path, out: Path, before: set, oid: str, doc: Dict[str, Any], exc: Exception) -> Dict[str, Any]:
    """The manifest entry for an output that stops on a file or history this copy does not have: no output files are kept (a half-written one
    is removed). The entry is the shipped one (Edith's P2), with only `status` and `reason` changed: the reason is the error's first line."""
    for f in out.iterdir():
        if f.name not in before and f.name.startswith(oid + "."):
            f.unlink()
    return {**doc, **_shipped_entry(repo, oid), "status": AS_BUILT, "reason": str(exc).splitlines()[0]}


def build_one(S: Store, spec: core.Spec, meta: Meta, out: Path) -> Dict[str, Any]:
    from . import paper_out_style as style
    S.used = set()
    res = spec.build(S)
    cited = S.used - {"plan"}
    if "plan" in S.used and _cites(res, "plan"):
        cited.add("plan")
    used = {n: S.sources[n].ledger() for n in sorted(cited)}
    files: Dict[str, str] = {}
    entry: Dict[str, Any] = {**_meta_doc(meta), "module": spec.module, "sources": used}
    if isinstance(res, Table):
        _floor_note(res)
        style_problems: Dict[str, List[str]] = {}
        _write_table(out, meta.id, meta.id, res, meta, used, files, style_problems)
        entry["status"] = "built"
        from .paper_out_narrow import NARROW
        if res.main_table is not None:
            _write_table(out, meta.id, f"{meta.id}.main", res.main_table, meta, used, files, style_problems)
            entry["main_text_version"] = f"{meta.id}.main.tex"
        elif meta.id in NARROW:
            _write_table(out, meta.id, f"{meta.id}.main", core.narrow(res, NARROW[meta.id]), meta, used, files, style_problems,
                         enforce=False)
            entry["main_text_version"] = f"{meta.id}.main.tex"
        from .paper_out_anon import ANON, anonymous
        if meta.id in ANON:
            before = set(S.used)
            anon = anonymous(S, {meta.id: res})[meta.id]
            used_anon = {**used, **{n: S.sources[n].ledger() for n in sorted(S.used - before)}}
            entry["anonymous_version"] = _write_anon(out, meta.id, anon, meta, used_anon, files)
        if style_problems:
            entry["style_problems"] = style_problems          # the polish standard's table checks, for the supplement pass
    elif isinstance(res, FigureOut):
        for stem, fo in [(meta.id, res)] + [(f"{meta.id}.{suffix}", v) for suffix, v in res.variants]:
            bad = figure_text_problems(fo)
            if bad:
                raise ValueError(f"{stem}: figure text holds digits not read from a source: {bad}")
            barred = figure_barred(fo)
            if barred:
                raise ValueError(f"{stem}: figure text or alt text holds a decision id, item number or internal code: {barred}")
            from matplotlib.text import Text
            from . import paper_out_lint as lint
            looks = style.figure_problems(fo.fig) + lint.vocabulary_texts(
                [" ".join(c.printed for c in fo.alt)] + [t.get_text() for t in fo.fig.findobj(Text) if t.get_visible()])
            if looks and style.FIGURE_CHECKS_ENFORCED:
                raise ValueError(f"{stem}: the figure fails the polish standard's figure checks: {looks}")
            if looks:
                entry.setdefault("figure_problems", {})[stem] = looks      # recorded until the figure pass (batch g) enforces them
            pdf, png = out / f"{stem}.pdf", out / f"{stem}.png"
            style.save(fo.fig, pdf, png)
            for p in (pdf, png):
                files[p.name] = core.sha256(p.read_bytes())
            alt = " ".join(c.printed for c in fo.alt if c.printed).strip()
            _write(out, f"{stem}.alt.txt", (alt + "\n").encode("utf-8"), files)
            doc = {"output": _meta_doc(meta), "sources": used, "points": fo.points, "alt": [c.record() for c in fo.alt],
                   "caption": {k: [c.record() for c in v] for k, v in sorted(fo.caption.items())}}
            _write(out, f"{stem}.data.json", core.dumps(doc), files)
        if res.variants:
            entry["variants"] = [f"{meta.id}.{suffix}.pdf" for suffix, _ in res.variants]
        entry["status"] = "built"
    elif isinstance(res, Stub):
        entry["status"] = "partial" if res.partial is not None else "stub"
        entry["waits_for"] = list(res.waits_for)
        entry["why"] = res.why
        if res.partial is not None:
            _write_table(out, meta.id, f"{meta.id}.partial", res.partial, meta, used, files)
        _write(out, f"{meta.id}.stub.json", core.dumps({"output": _meta_doc(meta), "waits_for": list(res.waits_for), "why": res.why,
                                                        "content": meta.content, "source_keys": meta.source_keys}), files)
    else:
        raise TypeError(f"{meta.id}: builder returned {type(res).__name__}")
    entry["files"] = dict(sorted(files.items()))
    return entry


def figure_text_problems(res: FigureOut) -> List[str]:
    """Every text drawn in the figure except the axis tick labels (which matplotlib writes from the data scale) must pass the label
    check once the printed values of the figure's own recorded cells are blanked out: a typed number in a label, legend, annotation or
    title is refused, a number read from a source (and recorded) is not."""
    import re
    from matplotlib.text import Text
    printed = set()
    for c in _cell_records({"p": res.points, "a": [c.record() for c in res.alt],
                            "c": {k: [c.record() for c in v] for k, v in res.caption.items()}}):
        if c["kind"] == "num" and c["printed"]:
            printed.add(c["printed"])
    ticks = set()
    for ax in res.fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                ticks.update({id(tk.label1), id(tk.label2)})
            ticks.add(id(axis.get_offset_text()))
    problems = []
    for t in res.fig.findobj(Text):
        if id(t) in ticks or not t.get_text():
            continue
        s = core.blank_allowed(t.get_text())
        for p in sorted(printed, key=len, reverse=True):
            s = re.sub(r"(?<![\w.])" + re.escape(p) + r"(?![\w.])", " ", s)
        if re.search(r"\d", s):
            problems.append(t.get_text())
    return sorted(set(problems))


# Text that must never be drawn in a figure or written in its alt text (the converter prints both; it cannot read inside a PDF):
# decision ids, item numbers (Q22: captions and main text use none, and a figure carries no definition of them), plan codes and the
# top-up's internal arm ids.
FIGURE_BARRED = r"\bD-\d|\b[Ii]tems? \d|\bTF-[A-Z]|\bF\d+\b|\bF-[a-z]|\b(?:C13|E2|E3)\b"


def figure_barred(res: FigureOut) -> List[str]:
    import re
    from matplotlib.text import Text
    texts = [t.get_text() for t in res.fig.findobj(Text) if t.get_text()] + [" ".join(c.printed for c in res.alt)]
    return sorted({t for t in texts if re.search(FIGURE_BARRED, t)})


def build(repo: Path, out: Path, only: Optional[Sequence[str]] = None, store: Optional[Store] = None,
          modules: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    from . import paper_out_style as style
    style.check_versions()
    style.apply_rc()
    if modules is not None and only is None:
        raise ValueError("--modules is for development builds with --only (a full build loads every module)")
    reg = load_registry(modules)
    S = store or Store(repo)
    if S.from_disk and Path(out).resolve() == (Path(repo) / "data" / "paper-outputs").resolve():
        raise SystemExit("a build without the history must not write into the shipped data/paper-outputs: it would replace the shipped "
                         "MANIFEST.json (D-207). Give --out an empty folder and compare it with check_outputs.")
    metas = core.plan_meta(S)
    unknown = sorted(set(reg) - set(metas))
    if set(reg) & set(core.DROPPED):
        raise ValueError(f"builders for dropped ids: {sorted(set(reg) & set(core.DROPPED))}")
    if unknown:
        raise ValueError(f"builders for ids not in the plan: {unknown}")
    ids = [i for i in metas if (only is None or i in only)]
    if only is not None and set(only) - set(metas) - set(core.DATA_REGISTRY):
        raise ValueError(f"not in the plan: {sorted(set(only) - set(metas) - set(core.DATA_REGISTRY))}")
    out.mkdir(parents=True, exist_ok=True)
    entries: List[Dict[str, Any]] = []
    for oid in ids:
        if oid not in reg:
            entries.append({**_meta_doc(metas[oid]), "status": "todo", "files": {}})
            continue
        style.apply_rc()
        before = {f.name for f in out.iterdir()}
        try:
            entries.append(build_one(S, reg[oid], metas[oid], out))
        except (core.NotShipped, core.NeedsHistory) as exc:       # disk mode only: a copy without the history carries on (Edith's M5)
            entries.append(_as_built(repo, out, before, oid, {**_meta_doc(metas[oid]), "module": reg[oid].module}, exc))
    for name, spec in sorted(core.DATA_REGISTRY.items()):
        if only is not None and name not in only:
            continue
        S.used = set()
        try:
            body = spec.build(S)
        except (core.NotShipped, core.NeedsHistory) as exc:
            entries.append(_as_built(repo, out, set(), name, {"id": name, "kind": "data", "title": name, "section": "claims ledger",
                                                              "label": "derived values", "module": spec.module}, exc))
            continue
        used = {n: S.sources[n].ledger() for n in sorted(S.used - {"plan"})}
        files: Dict[str, str] = {}
        _write(out, f"{name}.json", core.dumps({"output": name, "sources": used, "values": body}), files)
        entries.append({"id": name, "kind": "data", "title": name, "section": "claims ledger", "label": "derived values",
                        "status": "built", "module": spec.module, "sources": used, "files": files})
    problems = audit(out, S, entries)
    if problems:
        raise RuntimeError(f"provenance audit failed ({len(problems)}):\n  " + "\n  ".join(problems[:40]))
    titles = {e["id"]: e["title"] for e in core.plan_entries(S)}
    manifest = {"generator": GENERATOR, "plan": S.sources["plan"].ledger(), "pins": dict(style.PINNED),
                "python": "3.9", "outputs": entries,
                "dropped": [{"id": k, "title": titles[k], "why": v} for k, v in sorted(core.DROPPED.items())],
                "title_edits": [{"id": k, "plan_title": titles[k], "printed_title": t, "why": w}
                                for k, (t, w) in sorted(core.TITLE_EDITS.items())],
                "counts": {s: sum(1 for e in entries if e["status"] == s) for s in ("built", "partial", "stub", "todo")}}
    if any(e["status"] == AS_BUILT for e in entries):                      # only a disk-mode build in a copy without the history has any
        manifest["counts"][AS_BUILT] = sum(1 for e in entries if e["status"] == AS_BUILT)
    if only is None:
        stale = sorted(p.name for p in out.iterdir() if p.is_file() and p.name not in
                       {f for e in entries for f in e["files"]} | {"MANIFEST.json", "MANIFEST.md"})
        for name in stale:                       # printed, not recorded: the manifest depends only on the sources and the code
            (out / name).unlink()
            print(f"removed stale file {name}")
        (out / "MANIFEST.json").write_bytes(core.dumps(manifest))
        (out / "MANIFEST.md").write_bytes(manifest_md(manifest).encode("utf-8"))
    return manifest


ENTRY_NAME_FORMULAS = ("the name of this dict entry", "the key name (steps)", "the key name")


def _cell_records(doc: Any):
    """Every cell record in a .cells.json or .data.json document (any dict with 'printed' and 'kind')."""
    if isinstance(doc, dict):
        if "printed" in doc and "kind" in doc:
            yield doc
        for v in doc.values():
            yield from _cell_records(v)
    elif isinstance(doc, list):
        for v in doc:
            yield from _cell_records(v)


def audit(out: Path, S: Store, entries: List[Dict[str, Any]]) -> List[str]:
    """Re-reads every recorded source and key: each must resolve in its pinned source; a number cell must name at least one ref; a
    cell with one ref and no formula must hold exactly the stamped value as its raw value; an entry-name cell must print the key's
    last segment. Returns the problems (an empty list is a pass)."""
    problems: List[str] = []
    for e in entries:
        if e["status"] == AS_BUILT:
            continue                                                       # its files are the shipped ones, not in this folder
        for name in e["files"]:
            if not (name.endswith(".cells.json") or name.endswith(".data.json") or e.get("kind") == "data"):
                continue
            doc = core.json.loads((out / name).read_text("utf-8"))
            for c in _cell_records(doc):
                if c["kind"] != "num":
                    continue
                refs = c.get("refs") or []
                if not refs:
                    problems.append(f"{name}: number cell {c['printed']!r} has no source")
                    continue
                for r in refs:
                    try:
                        val = S.get(r["source"], r["key"])
                    except Exception as x:                                   # noqa: BLE001
                        problems.append(f"{name}: {r['source']}:{r['key']} does not resolve ({x})")
                        continue
                    if len(refs) == 1 and not c.get("formula") and c.get("raw") != val:
                        problems.append(f"{name}: {r['source']}:{r['key']} raw {c.get('raw')!r} != stamped {val!r}")
                if c.get("formula") in ENTRY_NAME_FORMULAS and core.parse_key(refs[0]["key"])[-1] != c["printed"]:
                    problems.append(f"{name}: entry-name cell {c['printed']!r} is not the last segment of {refs[0]['key']}")
    return problems


def manifest_md(m: Dict[str, Any]) -> str:
    c = m["counts"]
    lines = [f"# Paper outputs: manifest (generated by `{m['generator']}`; do not edit)", "",
             f"Plan: `{m['plan']['path']}` at {m['plan']['commit']}. Built {c['built']}, partial {c['partial']}, stub {c['stub']}, "
             f"to do {c['todo']}" + (f", as built (not rebuilt in this copy; its reason is in MANIFEST.json) {c[AS_BUILT]}" if c.get(AS_BUILT) else "") + f". Every file's SHA-256 is in MANIFEST.json; every cell's source and key in its `.cells.json` or "
             f"`.data.json`.", "",
             "| Id | Title | Section | Status | Waits for | Sources |", "|---|---|---|---|---|---|"]
    for e in m["outputs"]:
        lines.append(f"| {e['id']} | {e['title']} | {e['section']} | {e['status']} | {', '.join(e.get('waits_for', []))} | "
                     f"{', '.join(sorted(e.get('sources', {})))} |")
    if m.get("dropped"):
        lines += ["", "Dropped from the plan:", ""] + [f"- {d['id']} ({d['title']}): {d['why']}" for d in m["dropped"]]
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--only", default=None, help="comma-separated ids (no manifest is written)")
    ap.add_argument("--modules", default=None, help="development only, with --only: load just these builder modules")
    ap.add_argument("--from-disk", action="store_true", help="read pinned files from their paths, not their commits (SHA-256 checked)")
    a = ap.parse_args(argv)
    if a.from_disk:
        for repo in (a.repo, Path(__file__).resolve().parents[2]):       # the sources' repository and the code's (lint's, anon's pins)
            core.set_from_disk(repo)
    only = [x.strip() for x in a.only.split(",")] if a.only else None
    mods = [x.strip() for x in a.modules.split(",")] if a.modules else None
    m = build(a.repo, a.out, only, modules=mods)
    for e in m["outputs"]:
        print(f"{e['id']}: {e['status']}" + (f" (waits for {', '.join(e['waits_for'])})" if e.get("waits_for") else ""))
    print("counts:", m["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
