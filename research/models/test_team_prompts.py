"""Tests for the E2 plan parser and the H-pick8 pick parser (Edith r1: R1-1, R1-2). Run: python3 -m pytest -q research/models/test_team_prompts.py"""
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import team_prompts as t  # noqa: E402


def plan(*blocks):
    return '\n'.join(blocks)


class PlanParser(unittest.TestCase):
    def ok(self, txt, n, want):
        self.assertEqual(t.parse_plan(txt, n), want, txt)

    def test_colon_period_dash_and_dashes(self):
        for sep in (':', '.', ' -', ' –', ' —', ' :'):
            self.ok(plan(f'Task 1{sep} do A', f'Task 2{sep} do B'), 2, ['do A', 'do B'])

    def test_markdown_heading_text_on_next_lines(self):
        self.ok(plan('## Task 1', 'Apply rule E.', 'Then the house rule.', '', '## Task 2', 'Apply rule C.'), 2,
                ['Apply rule E. Then the house rule.', 'Apply rule C.'])

    def test_heading_levels_bold_bullets(self):
        self.ok(plan('# Task 1', 'x', '### **Task 2**', 'y', '- **Task 3:** z', '> Task 4: w'), 4, ['x', 'y', 'z', 'w'])

    def test_bold_colon_inside_and_outside(self):
        self.ok(plan('**Task 1:** a', '**Task 2**: b'), 2, ['a', 'b'])

    def test_lowercase_and_prose_before(self):
        self.ok(plan('Here is the plan.', 'task 1: a', 'TASK 2: b'), 2, ['a', 'b'])

    def test_label_without_separator_but_with_text_is_not_a_label(self):
        # "Task 2 depends on ..." inside a task is prose, not a new label (only alone, or with : . -)
        self.ok(plan('Task 1: a', 'Task 2 depends on task 1.', 'Task 2: b'), 2, ['a Task 2 depends on task 1.', 'b'])

    def test_failures(self):
        self.assertIsNone(t.parse_plan(plan('Task 1: a', 'Task 3: c'), 2))            # a gap
        self.assertIsNone(t.parse_plan(plan('Task 1: a', 'Task 1: b', 'Task 2: c'), 2))  # a repeat
        self.assertIsNone(t.parse_plan(plan('Task 1: a', 'Task 2: b', 'Task 3: c'), 2))  # too many
        self.assertIsNone(t.parse_plan(plan('## Task 1', '## Task 2', 'b'), 2))          # task 1 has no text
        self.assertIsNone(t.parse_plan('no labels at all', 1))


class PickParser(unittest.TestCase):
    def test_accepted(self):
        for txt, k in (('Pick: 3', 3), ('Pick: 3.', 3), ('Pick: 3,', 3), ('Pick: Reply 3', 3), ('Pick: reply 3.', 3),
                       ('**Pick:** 2', 2), ('Pick: **4**', 4), ('**Pick: Reply 5**', 5), ('pick:8', 8), ('## Pick: 1', 1),
                       ('I compared them.\nPick: 6', 6)):
            self.assertEqual(t.parse_pick(txt), k, txt)

    def test_last_valid_line_wins(self):
        self.assertEqual(t.parse_pick('Pick: 2\nOn reflection:\nPick: 7'), 7)

    def test_rejected(self):
        for txt in ('Pick: 9', 'Pick: 0', 'Pick: 3 and 5', 'Pick: 3, 5', 'Pick: 3..', 'Pick: Reply', 'I pick 3',
                    'Pick: three', 'Pick: Reply 3 because it is right'):
            self.assertIsNone(t.parse_pick(txt), txt)


if __name__ == '__main__':
    unittest.main()
