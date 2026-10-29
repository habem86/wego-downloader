"""GUI behavior tests. Use xvfb-run on a headless Linux host."""
import io
import os
from pathlib import Path
import queue
import stat
import tempfile
import unittest
from unittest.mock import patch

try:
    import tkinter as tk
    from honda_maps_gui import App
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False


@unittest.skipUnless(TK_AVAILABLE and os.environ.get('DISPLAY'), 'Tk and a display are required')
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)

    def tearDown(self):
        self.app.running = False
        self.app.close()

    def test_vin_lookup_without_consent_never_starts_worker(self):
        self.app.url.set('A' * 17)
        with patch('honda_maps_gui.threading.Thread') as worker, patch('honda_maps_gui.messagebox.showerror') as error:
            self.app.start(False)
            worker.assert_not_called()
            error.assert_called_once()
        self.assertFalse(self.app.running)

    def test_link_mode_hides_the_link_and_does_not_submit_a_vin(self):
        self.app.mode.set('link')
        self.app.url.set('heremapdownloaderv2://example.invalid/update')
        self.assertEqual(self.app.source_entry.cget('show'), '•')
        self.assertEqual(str(self.app.preview.cget('state')), 'normal')
        with patch('honda_maps_gui.threading.Thread') as worker:
            self.app.start(False)
        command, flag = worker.call_args.kwargs['args'][1:]
        self.assertEqual(flag, '--link-file')
        self.assertNotIn('--accept-here-terms', command)
        self.assertTrue(self.app.running)
        self.assertEqual(str(self.app.source_entry.cget('state')), 'disabled')
        self.app._finish(0)
        self.assertEqual(str(self.app.source_entry.cget('state')), 'normal')

    def test_switching_modes_never_reveals_or_reuses_a_private_link_as_a_vin(self):
        private = 'heremapdownloaderv2://example.invalid/private-example'
        self.app.mode.set('link')
        self.app.url.set(private)
        self.app.mode.set('vin')
        self.assertEqual(self.app.url.get(), '')
        self.app.url.set('A' * 17)
        self.app.mode.set('link')
        self.assertEqual(self.app.url.get(), private)
        self.assertEqual(self.app.source_entry.cget('show'), '•')
        self.app.mode.set('vin')
        self.assertEqual(self.app.url.get(), 'A' * 17)

    def test_cancelled_confirmation_does_not_start_download(self):
        self.app.url.set('A' * 17)
        self.app.accepted.set(True)
        with tempfile.TemporaryDirectory() as destination:
            self.app.destination.set(destination)
            with patch('honda_maps_gui.messagebox.askyesno', return_value=False), patch('honda_maps_gui.threading.Thread') as worker:
                self.app.start(True)
                worker.assert_not_called()
        self.assertFalse(self.app.running)

    def test_progress_counts_completed_files_not_started_files(self):
        self.app.active_download = True
        self.app._handle_line('Honda bonneville EU | 3 files | 26.47 GB + license\n')
        self.app._handle_line('Map folders: HereMapsV1\n')
        self.app._handle_line('[1/3] HereMapsV1/NavDB.CZE_1109/3DO.NDS\n')
        self.assertEqual(self.app.completed_files, 0)
        self.app._handle_line('  verified\n')
        self.assertEqual(self.app.completed_files, 1)
        self.assertEqual(float(self.app.progress.cget('value')), 1)
        self.assertIn('1 / 3 complete', self.app.files_stat.cget('text'))
        self.assertEqual(self.app.output_label.cget('text'), 'HereMapsV1 /')
        self.assertEqual(self.app.catalog_gb, 26.47)

    def test_changing_source_invalidates_previous_catalog_but_destination_does_not(self):
        self.app.url.set('A' * 17)
        self.app._handle_line('Honda bonneville EU | 3 files | 26.47 GB + license\n')
        with tempfile.TemporaryDirectory() as destination:
            self.app.destination.set(destination)
        self.assertEqual(self.app.catalog_gb, 26.47)
        self.app.url.set('B' * 17)
        self.assertIsNone(self.app.catalog_gb)
        self.assertIsNone(self.app.catalog_source)
        self.assertEqual(self.app.transfer_title.cget('text'), 'Source changed')
        self.assertEqual(self.app.total_files, 0)

    def test_error_is_visible_without_opening_activity(self):
        self.app._handle_line('Error: Link expired. Obtain a new launch link.\n')
        self.app._finish(1)
        self.assertEqual(self.app.transfer_title.cget('text'), 'Needs attention')
        self.assertIn('Link expired', self.app.transfer_detail.cget('text'))
        self.assertFalse(self.app.log_open)

    def test_stop_is_not_reported_as_completion(self):
        self.app.running = True
        self.app.stop()
        self.app._finish(130)
        self.assertEqual(self.app.transfer_title.cget('text'), 'Stopped')
        self.assertIn('resume', self.app.transfer_detail.cget('text'))
        self.assertFalse(self.app.running)

    def test_worker_keeps_source_out_of_arguments_and_removes_private_temp_file(self):
        app = self.app
        captured = {}
        class Process:
            stdout = io.StringIO('Preview only.\n')
            def __init__(self, command, **kwargs):
                path = Path(command[-1])
                captured['path'] = path
                captured['content'] = path.read_text()
                captured['mode'] = stat.S_IMODE(path.stat().st_mode)
                captured['command'] = command
            def wait(self): return 0
        with patch('honda_maps_gui.subprocess.Popen', Process):
            app.worker('private-example-source', ['python', 'honda_maps.py'], '--link-file')
        self.assertEqual(captured['content'], 'private-example-source')
        self.assertEqual(captured['mode'], 0o600)
        self.assertNotIn('private-example-source', captured['command'])
        self.assertFalse(captured['path'].exists())
        self.assertEqual(app.messages.get_nowait(), ('line', 'Preview only.\n'))
        self.assertEqual(app.messages.get_nowait(), ('finished', 0))

    def test_worker_exception_does_not_disclose_source(self):
        with patch('honda_maps_gui.subprocess.Popen', side_effect=RuntimeError('private-example-source')):
            self.app.worker('private-example-source', ['python', 'honda_maps.py'], '--link-file')
        output = []
        while True:
            try: output.append(self.app.messages.get_nowait())
            except queue.Empty: break
        self.assertNotIn('private-example-source', repr(output))
        self.assertEqual(output[-1], ('finished', 1))

    def test_activity_can_be_expanded_without_changing_operation_state(self):
        self.app.toggle_log()
        self.assertTrue(self.app.log_open)
        self.assertTrue(self.app.log_frame.grid_info())
        self.app.toggle_log()
        self.assertFalse(self.app.log_open)
        self.assertFalse(self.app.log_frame.grid_info())
        self.assertFalse(self.app.running)


if __name__ == '__main__':
    unittest.main()
