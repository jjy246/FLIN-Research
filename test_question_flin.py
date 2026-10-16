#!/usr/bin/env python3
"""Offline regression tests for the original question.py plus FLIN cost extensions.

Does not contact external websites or require Ollama. Uses disposable SQLite DBs.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('MPLBACKEND', 'Agg')
if '--flin-info' not in sys.argv:
    sys.argv.append('--flin-info')  # Select the original program's headless backend.
FILE = Path(__file__).resolve().with_name('question.py')
spec = importlib.util.spec_from_file_location('flin_question_tests', FILE)
flin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flin)

MATH_CONCEPTS = ('matrix', 'eigenvalue', 'linear operator', 'vector space')
QUOTE = ('The matrix eigenvalue can be represented by a linear operator on a '
         'vector space under suitable mathematical conditions.')


class EfficiencyMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = flin.database(Path(self.tmp.name) / 'test.sqlite3')
        flin.abc_enable(self.con)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def ingest(self, source_id, cluster_id=None, labels=MATH_CONCEPTS):
        cluster_id = cluster_id or ('online:' + source_id)
        features = [{'label': label, 'explanation': QUOTE,
                     'url': 'https://example.org/' + source_id,
                     'position': i} for i, label in enumerate(labels)]
        return flin.abc_ingest_cluster(
            self.con, features, cluster_id,
            paper_id=source_id, evidence_source_id='paper:' + source_id,
            cluster_quote=QUOTE, cluster_url='https://example.org/' + source_id)

    def test_first_input_is_immediately_triggerable(self):
        result = self.ingest('paper1')
        self.assertEqual(result['promoted'], 4)
        self.assertEqual(flin.abc_status(self.con)['active'], 4)
        self.assertEqual(flin.abc_status(self.con)['shortcuts'], 0)
        primitive = self.con.execute("SELECT COUNT(*) FROM flin_cost_decisions "
                                     "WHERE kind='primitive'").fetchone()[0]
        self.assertEqual(primitive, 4)

    def test_shortcuts_need_cost_and_independent_sources(self):
        self.ingest('paper1')
        self.ingest('paper2')
        self.assertEqual(flin.abc_status(self.con)['shortcuts'], 0)
        self.assertLess(flin.flin_estimate_association_cost(4, 1)['net_savings'], 0)
        self.ingest('paper3')
        self.assertEqual(flin.abc_status(self.con)['shortcuts'], 1)
        members = self.con.execute('SELECT COUNT(*) FROM flin_shortcut_members').fetchone()[0]
        self.assertEqual(members, 4)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM units').fetchone()[0], 0)
        self.assertEqual(self.con.execute('SELECT COUNT(*) FROM edges').fetchone()[0], 0)
        distribution = flin.abc_simulate(self.con, 'matrix', save=False, random_seed=123)
        self.assertGreater(distribution['activated_count'], 0)

    def test_multiple_clusters_from_same_document_do_not_inflate_support(self):
        self.ingest('paper1')
        self.ingest('paper1', cluster_id='online:second-passage-same-document')
        count = self.con.execute('SELECT MAX(distinct_sources) FROM flin_patterns').fetchone()[0]
        self.assertEqual(count, 1)
        self.assertEqual(flin.abc_status(self.con)['shortcuts'], 0)

    def test_short_paths_do_not_create_zero_saving_shortcuts(self):
        for source in ('paper1','paper2','paper3','paper4'):
            self.ingest(source, labels=MATH_CONCEPTS[:3])
        self.assertEqual(flin.abc_status(self.con)['shortcuts'], 0)

    def test_retrofit_existing_ssrs_cluster_history(self):
        for source in ('paper1','paper2','paper3'):
            self.ingest(source)
        with self.con:
            self.con.execute("DELETE FROM flin_pattern_evidence")
            self.con.execute("DELETE FROM flin_patterns")
            self.con.execute("DELETE FROM flin_shortcut_members")
            self.con.execute("DELETE FROM flin_cost_decisions")
            self.con.execute("DELETE FROM abc_edges WHERE src LIKE 'flin:shortcut:%' "
                             "OR dst LIKE 'flin:shortcut:%'")
            self.con.execute("DELETE FROM abc_evidence WHERE unit_id LIKE 'flin:shortcut:%'")
            self.con.execute("DELETE FROM abc_ssrs WHERE unit_id LIKE 'flin:shortcut:%'")
            self.con.execute("DELETE FROM abc_units WHERE id LIKE 'flin:shortcut:%'")
        self.assertEqual(flin.abc_status(self.con)['shortcuts'], 0)
        result = flin.flin_retrofit_history(self.con, limit=10)
        self.assertEqual(result['processed'], 3)
        self.assertEqual(result['created_shortcuts'], 1)
        self.assertEqual(result['remaining'], 0)
        repeat = flin.flin_retrofit_history(self.con, limit=10)
        self.assertEqual(repeat['processed'], 0)

    def test_additional_evidence_reinforces_existing_shortcut(self):
        for source in ('paper1','paper2','paper3'):
            self.ingest(source)
        sid = self.con.execute("SELECT id FROM abc_units WHERE id LIKE 'flin:shortcut:%'").fetchone()[0]
        initial = self.con.execute('SELECT weight FROM abc_edges WHERE dst=?',(sid,)).fetchone()[0]
        self.ingest('paper4')
        later = self.con.execute('SELECT weight FROM abc_edges WHERE dst=?',(sid,)).fetchone()[0]
        self.assertGreater(later, initial)
        self.assertEqual(self.con.execute('SELECT evidence_count FROM abc_units WHERE id=?',
                                          (sid,)).fetchone()[0], 4)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
