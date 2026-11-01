"""Narrow main-text versions of the wide tables (Vision's ask for a single-column page: about 8 columns or fewer). Each is a choice and
join of the full table's columns by title (paper_out_core.narrow), so every cell keeps its source; the full table stays for the appendix.
Written as <id>.main.csv / .tex / .cells.json beside the full files.
"""

NARROW: dict = {
    # Every former entry is now built by its table's builder at the paper's precision (Table.main_table, D-159/D-160/D-161):
    # TAB-01 (Table 2), TAB-02 (with TAB-03's views), TAB-10 (with TAB-11's per-shape rows), TAB-12 and TAB-16 (batch f).
}
