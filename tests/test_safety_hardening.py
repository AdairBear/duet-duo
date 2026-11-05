"""Kill switch, atomic writes, and never-overwrite behaviour."""
import contextlib, io, os, pathlib, shutil, sys, tempfile, unittest
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import bridge  # noqa: E402
from test_bridge import BOARD  # noqa: E402


class HardeningTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        for d in ("claims", "inbox-duet", "inbox-dispatch", "done"):
            (self.tmp / d).mkdir()
        shutil.copytree(REPO / "schema", self.tmp / "schema")
        (self.tmp / "BOARD.md").write_text(BOARD)
        self._root, bridge.ROOT = bridge.ROOT, self.tmp

    def tearDown(self):
        bridge.ROOT = self._root
        shutil.rmtree(self.tmp)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            bridge.main(list(argv))
        return out.getvalue()

    def code(self, *argv):
        out = io.StringIO()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(out):
            bridge.main(list(argv))
        return cm.exception.code, out.getvalue()

    def approve(self):
        return self.run_cli("approve", "--scope", "read the docs", "--expires", "1h", "--quote", "ok", "--agent", "Dispatch").strip()

    # ---- kill switch
    def test_status_reports_running_then_paused(self):
        self.assertEqual(self.run_cli("status").strip(), "running")
        (self.tmp / "bridge.OFF").write_text("")
        self.assertIn("PAUSED", self.run_cli("status"))

    def test_pause_blocks_claim_approve_check_and_consume_but_not_reading(self):
        aid = self.approve()
        (self.tmp / "bridge.OFF").write_text("")
        for argv in (["claim", "ALPHA-1", "--owner", "Duet", "--repo", "x", "--eta", "1h"],
                     ["approve", "--scope", "read x", "--expires", "1h", "--quote", "ok", "--agent", "Dispatch"],
                     ["approval", "consume", aid, "--scope", "read the docs", "--agent", "Dispatch"]):
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
                self.run_cli(*argv)
            self.assertIn("paused", str(cm.exception.code))
        self.assertEqual(self.code("approval", "check", aid, "--scope", "read the docs")[0], 1)
        self.assertEqual(self.code("validate")[0], 0)
        self.run_cli("log", "said", "still can log", "--agent", "Dispatch")
        self.assertFalse(list((self.tmp / "claims").glob("*.claim")))

    def test_resume_after_the_file_is_removed(self):
        off = self.tmp / "bridge.OFF"
        off.write_text("")
        off.unlink()
        self.run_cli("claim", "ALPHA-1", "--owner", "Duet", "--repo", "x", "--eta", "1h")

    # ---- atomic and non-overwriting writes
    def test_atomic_write_keeps_the_old_file_when_the_write_fails(self):
        target = self.tmp / "BOARD.md"
        before = target.read_text()
        with mock.patch("os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                bridge.write_atomic(target, "new")
        self.assertEqual(target.read_text(), before)
        self.assertEqual([p.name for p in self.tmp.glob(".*.tmp")], [])  # no stray temp file

    def test_write_new_never_overwrites(self):
        p = self.tmp / "done" / "X.md"
        bridge.write_new(p, "first")
        with self.assertRaises(FileExistsError):
            bridge.write_new(p, "second")
        self.assertEqual(p.read_text(), "first")

    def test_second_note_same_day_gets_a_suffix_and_first_survives(self):
        args = ("note", "ALPHA-1", "--from", "Dispatch", "--to", "Duet", "--status", "open", "--next", "n")
        a = self.run_cli(*args, "--body", "one").strip()
        b = self.run_cli(*args, "--body", "two").strip()
        self.assertNotEqual(a, b)
        self.assertIn("one", (self.tmp / a).read_text())
        self.assertIn("two", (self.tmp / b).read_text())

    def test_done_refuses_to_overwrite_a_report(self):
        self.run_cli("done", "ALPHA-1", "--owner", "Duet", "--summary", "s", "--status-line", "STATUS: done, next")
        before = (self.tmp / "done" / "ALPHA-1.md").read_text()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_cli("done", "ALPHA-1", "--owner", "Duet", "--summary", "other", "--status-line", "STATUS: done, next")
        self.assertEqual((self.tmp / "done" / "ALPHA-1.md").read_text(), before)

    def test_gitkeep_placeholders_are_not_validation_errors(self):
        for d in ("approvals", "heartbeat", "log"):
            (self.tmp / d).mkdir()
            (self.tmp / d / ".gitkeep").write_text("")
        self.assertEqual(bridge.validate(), [])

    def test_bridge_root_env_points_the_tool_elsewhere(self):
        env = dict(os.environ, BRIDGE_ROOT=str(self.tmp))
        import subprocess
        r = subprocess.run([sys.executable, "-I", str(REPO / "tools" / "bridge.py"), "board"], env=env, capture_output=True, text=True)
        self.assertIn("ALPHA-1", r.stdout)


if __name__ == "__main__":
    unittest.main()
