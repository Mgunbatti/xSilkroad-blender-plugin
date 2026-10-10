"""Run PK2 background loader with mocked Blender runtime and PK2 engine."""
import ast
from pathlib import Path
from types import SimpleNamespace
import threading
import time
import unittest

BASE = Path(__file__).resolve().parents[1] / 'silkroad_pk2_bridge'

class Props:
    def __init__(self, archive):
        self.archive = str(archive)
        self.key = '169841'
        self.entries = []
        self.selected_index = -1
        self.loading = False
        self.current_folder = ''
        self.search_mode = False
        self.message = ''
        self.scan_state = 'IDLE'
        self.scan_archive = ''
        self.scan_visual = 0.0
        self.scan_blocks = 0
        self.scan_has_counter = True

class FakeEngine:
    thread_ids = []
    def __init__(self, path, key, progress=None):
        self.primary = Path(path).resolve()
        self.key = key
        self.streams = {self.primary: object()}
        self.errors = []
        self.closed = False
        self.thread_ids.append(threading.get_ident())
        if progress:
            for n in (64,128,192):
                progress(self.primary, n, 0)
    def close(self):
        self.closed = True

class Timers:
    def __init__(self): self.fn = None
    def is_registered(self, fn): return self.fn is fn
    def register(self, fn, first_interval): self.fn = fn
    def unregister(self, fn): self.fn = None


def make_namespace(tmp_path):
    tree = ast.parse((BASE/'__init__.py').read_text())
    needed = {'_close_session','_stop_archive_load','_start_archive_load',
              '_poll_archive_load','_session_or_reopen', '_scan_visual_tick', '_redraw_pk2_panels'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed]
    m = ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]))
    props = Props(tmp_path)
    timers = Timers()
    fake_bpy = SimpleNamespace(path=SimpleNamespace(abspath=lambda v:v),
        context=SimpleNamespace(scene=SimpleNamespace(silkroad_editor=props)),
        app=SimpleNamespace(timers=timers), data=SimpleNamespace(window_managers=[]))
    FakeEngine.thread_ids.clear()
    status = lambda obj, msg, **kw: setattr(obj,'message', msg.format(**kw))
    ns = dict(Path=Path, bpy=fake_bpy, threading=threading, ArchiveSession=FakeEngine,
              _session=None, _load_job=None, _activate_engine=lambda:True,
              _status=status, _browse=lambda p,f: status(p,'HAZIR'),
              RuntimeError=RuntimeError)
    exec(compile(m,'<addon loader>','exec'),ns)
    return ns, props, timers

class AsyncScanTests(unittest.TestCase):
    def test_scanning_runs_off_main_thread_and_finishes_on_main_thread(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'Data.pk2'
            path.write_bytes(b'PK2 test file')
            ns, props, timers = make_namespace(path)
            main_tid=threading.get_ident()
            ns['_start_archive_load'](props)
            self.assertTrue(props.loading)
            self.assertIsNone(ns['_session'])
            job = ns['_load_job']
            job['thread'].join(timeout=2)
            self.assertFalse(job['thread'].is_alive())
            self.assertNotEqual(FakeEngine.thread_ids[-1],main_tid)
            self.assertEqual(job['blocks'],192)
            self.assertIsNone(ns['_poll_archive_load']())
            self.assertFalse(props.loading)
            self.assertEqual(props.message,'HAZIR')
            self.assertEqual(props.scan_state, 'READY')
            self.assertEqual(props.scan_visual, 1.0)
            self.assertIsNotNone(ns['_session'])
            self.assertEqual(ns['_session_or_reopen'](props),ns['_session'])
            # reopening the same file reuses index (no new background worker)
            ns['_start_archive_load'](props)
            self.assertEqual(len(FakeEngine.thread_ids),1)
            self.assertFalse(props.loading)
            ns['_close_session']()

    def test_pulse_represents_busy_not_a_fake_percentage(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/'Media.pk2'
            path.write_bytes(b'PK2 test file')
            ns, props, timers = make_namespace(path)
            ns['_start_archive_load'](props)
            self.assertEqual(props.scan_state, 'LOADING')
            self.assertGreater(props.scan_visual, 0)
            self.assertLess(props.scan_visual, 1)
            vals = [ns['_scan_visual_tick'](i) for i in range(30)]
            self.assertTrue(all(0 < v < 1 for v in vals))
            self.assertTrue(max(vals) > min(vals))
            ns['_load_job']['thread'].join(timeout=2)
            ns['_poll_archive_load']()
            self.assertEqual(props.scan_state, 'READY')
            self.assertEqual(props.scan_visual, 1)

    def test_cancel_detaches_job_and_worker_owns_session(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'Data.pk2'
            path.write_bytes(b'PK2 test file')
            ns, props, timers=make_namespace(path)
            ns['_start_archive_load'](props)
            job=ns['_load_job']
            ns['_stop_archive_load']()
            self.assertTrue(job['cancel'].is_set())
            job['thread'].join(timeout=2)
            self.assertIsNone(ns['_load_job'])
            self.assertIsNone(ns['_session'])
            self.assertIsNone(ns['_poll_archive_load']())

if __name__=='__main__': unittest.main()
