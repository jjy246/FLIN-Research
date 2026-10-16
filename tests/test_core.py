"""Offline cross-platform tests; no GUI, Ollama, or literature API calls."""
from __future__ import annotations
import collections
import importlib.util
import os
import random
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Force a headless matplotlib backend before importing the monolithic GUI module.
sys.argv = [sys.argv[0], '--cpu-info']
_TEST_STORAGE = tempfile.TemporaryDirectory(prefix='flin-test-data-')
os.environ['BRAIN_DATA_DIR'] = _TEST_STORAGE.name
_APP = Path(__file__).resolve().parents[1] / 'flin_desktop.py'
_spec = importlib.util.spec_from_file_location('flin_desktop_under_test', _APP)
flin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flin)


class FLINCoreTests(unittest.TestCase):
    def test_storage_override(self):
        self.assertEqual(flin.DATA_DIR, Path(_TEST_STORAGE.name).resolve())

    def test_default_data_dirs_on_windows_and_mac(self):
        with tempfile.TemporaryDirectory(prefix='flin-platform-test-') as tmp:
            home = Path(tmp)
            with mock.patch.dict(os.environ, {'BRAIN_DATA_DIR': ''}), \
                    mock.patch.object(Path, 'home', return_value=home), \
                    mock.patch.object(flin.sys, 'platform', 'win32'):
                self.assertEqual(flin.default_data_directory(),
                                 home / 'AppData' / 'Local' / 'FLIN' / 'BrainProject')
            with mock.patch.dict(os.environ, {'BRAIN_DATA_DIR': ''}), \
                    mock.patch.object(Path, 'home', return_value=home), \
                    mock.patch.object(flin.sys, 'platform', 'darwin'):
                self.assertEqual(flin.default_data_directory(),
                                 home / 'Library' / 'Application Support' / 'FLIN' / 'BrainProject')

    def test_data_format_and_topic_parsing(self):
        self.assertEqual(flin.active_domain(), 'mathematics')
        self.assertEqual(flin.parse_research_topics('Topology,Graph theory'),
                         ['Topology', 'Graph theory'])
        # Input compatibility aliases are intentionally not renamed in databases.
        self.assertEqual(flin.USER_TOPIC_ALIASES['\u7dda\u6027\u4ee3\u6578'], 'Linear algebra')

    def test_remote_pdf_url_rejection(self):
        self.assertTrue(flin.safe_pdf_url('https://arxiv.org/pdf/1234.56789'))
        for url in ('http://arxiv.org/a.pdf', 'https://127.0.0.1/file.pdf',
                    'https://localhost/private', 'file:///tmp/paper.pdf'):
            self.assertFalse(flin.safe_pdf_url(url), url)

    def test_redirect_does_not_fetch_localhost(self):
        class FakeResponse:
            status_code = 302
            headers = {'Location': 'http://127.0.0.1/private'}
            def __enter__(self): return self
            def __exit__(self, *_): return False
        class FakeSession:
            def __init__(self): self.calls = []
            def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return FakeResponse()
        session = FakeSession()
        # CI intentionally omits optional PyMuPDF: patch it so the redirect
        # defense is exercised even on the base dependency installation.
        with mock.patch.object(flin, 'fitz', object()):
            self.assertEqual(flin.obtain_pdf_text(session, {
                'best_oa_location': {'pdf_url': 'https://arxiv.org/pdf/1111.2222'}}), '')
        self.assertEqual(len(session.calls), 1)
        self.assertFalse(session.calls[0][1]['allow_redirects'])

    def test_fts5_support(self):
        con = sqlite3.connect(':memory:')
        try:
            con.execute('CREATE VIRTUAL TABLE test USING fts5(body)')
        finally:
            con.close()

    def test_learning_graph_and_single_exit(self):
        with tempfile.TemporaryDirectory(prefix='flin-test-db-') as tmp:
            with flin.database(path=Path(tmp) / 'net.sqlite3') as con:
                flin.abc_enable(con)
                for uid, label in [('unit:a', 'Alpha'), ('unit:b', 'Beta'),
                                   ('unit:c', 'Gamma'), ('unit:p', 'A%')]:
                    con.execute("""INSERT INTO abc_units(id,label,definition,status,quality,evidence_count)
                        VALUES(?,?,?,'active',90,1)""", (uid, label, label))
                con.execute("INSERT INTO abc_edges(src,dst,weight,observations) VALUES('unit:a','unit:b',3.,1)")
                con.execute("INSERT INTO abc_edges(src,dst,weight,observations) VALUES('unit:a','unit:c',1.,1)")
                con.commit()
                self.assertEqual(flin.abc_seed_units(con, 'A%'), [('unit:p', 'A%', 'A%')])
                self.assertEqual(flin.abc_seed_units(con, 'Al'), [('unit:a', 'Alpha', 'Al')])
                self.assertEqual(flin.abc_seed_units(con, '_'), [])
                rng = random.Random(123)
                cache = {}
                outcomes = collections.Counter()
                for _ in range(1000):
                    nxt = flin.flin_weighted_exit(con, 'unit:a', None,
                                                  collections.Counter(), 2, rng, cache)
                    self.assertIsNotNone(nxt)
                    outcomes[nxt[0]] += 1
                self.assertGreater(outcomes['unit:b'], 650)
                self.assertLess(outcomes['unit:b'], 850)
                result = flin.abc_simulate(con, 'Alpha', pulse_hz=8,
                                            input_duration=0.5, save=False,
                                            random_seed=42)
                self.assertEqual(result['input_pulses'], 4)
                self.assertGreaterEqual(result['activated_count'], 2)

    def test_integrated_response_validation(self):
        raw, visible = flin.abc_integrated_response([0.1, 0.3], 1.0, 0.2, 1.0)
        self.assertGreaterEqual(raw, visible)
        self.assertGreaterEqual(visible, 0.0)
        with self.assertRaises(ValueError):
            flin.abc_integrated_response([0.1], 0.0, 0.2, 1.0)

    def test_published_sqlite_roundtrip_retains_usable_flin_graph(self):
        """An exported Release .sqlite3 can be imported and simulated locally."""
        with tempfile.TemporaryDirectory(prefix='flin-release-roundtrip-') as tmp:
            root = Path(tmp)
            original = root / 'original.sqlite3'
            with flin.database(path=original) as con:
                flin.abc_enable(con)
                con.executemany("""INSERT INTO abc_units
                  (id,label,definition,status,quality,evidence_count)
                  VALUES(?,?,?,'active',95,1)""", [
                  ('a', 'Algebra', 'Algebra'), ('b', 'Matrix', 'Matrix')])
                con.execute("INSERT INTO abc_edges(src,dst,weight,observations) VALUES('a','b',2.5,4)")
                con.execute("INSERT INTO units(id,label,kind) VALUES('theory:algebra','Algebra','theory')")
                con.commit()
            with mock.patch.object(flin, 'DB_PATH', original):
                published_dir = flin.export_memory_network(root, mode='sqlite')
            published = published_dir / 'association.sqlite3'
            from scripts.inspect_network_snapshot import inspect
            report = inspect(published, require_flin=True)
            self.assertEqual(report['counts']['abc_edges'], 1)
            network_id = flin.import_network(published, 'Community Algebra Network', activate=False)
            imported_path = flin.network_path_from_id(network_id)
            self.assertNotEqual(imported_path, original)
            self.assertNotEqual(imported_path, published)
            with flin.database(path=imported_path) as con:
                status = flin.abc_status(con)
                self.assertTrue(status['enabled'])
                self.assertEqual(status['active'], 2)
                self.assertEqual(status['edges'], 1)
                self.assertEqual(con.execute('SELECT COUNT(*) FROM units').fetchone()[0], 1)
                result = flin.abc_simulate(con, 'Algebra', pulse_hz=4,
                                            input_duration=1, save=False,
                                            random_seed=1)
                self.assertGreaterEqual(result['activated_count'], 1)
            # The imported copy survives deleting the downloaded original.
            published.unlink()
            self.assertTrue(imported_path.exists())

    def test_inspector_rejects_empty_flin_snapshot(self):
        from scripts.inspect_network_snapshot import inspect
        with tempfile.TemporaryDirectory(prefix='flin-unusable-snapshot-') as tmp:
            source=Path(tmp)/'empty.sqlite3'
            with flin.database(path=source) as con:
                con.execute("INSERT INTO units(id,label,kind) VALUES('theory:x','X','theory')")
                con.commit()
            report=inspect(source)
            self.assertEqual(report['sqlite_quick_check'], 'ok')
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                inspect(source,require_flin=True)

    def test_model_roles_are_configurable(self):
        self.assertEqual(flin.ROLE_MODELS['generator'], flin.DEFAULT_OLLAMA_MODEL)
        self.assertTrue(flin.ROLE_MODELS['critic'])


if __name__ == '__main__':
    unittest.main()
