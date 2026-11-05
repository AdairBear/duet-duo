"""Canary for the safety model: tools/bridge.py has no execution path. If a change adds one, this fails."""
import ast, pathlib, unittest

SRC = pathlib.Path(__file__).resolve().parent.parent / "tools" / "bridge.py"
BANNED_NAMES = {"eval", "exec", "compile", "__import__"}  # bare calls; re.compile() is an attribute and is fine
BANNED_ATTRS = {"system", "popen", "spawn", "execv", "execl", "startfile"}
BANNED_IMPORTS = {"socket", "http", "urllib", "requests", "ftplib", "smtplib", "telnetlib", "ctypes", "pickle", "marshal"}


class NoExecTest(unittest.TestCase):
    def setUp(self):
        self.tree = ast.parse(SRC.read_text())

    def test_no_banned_calls(self):
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Name):
                    self.assertNotIn(f.id, BANNED_NAMES, f"line {n.lineno}: {f.id}() is not allowed in bridge.py")
                elif isinstance(f, ast.Attribute):
                    self.assertNotIn(f.attr, BANNED_ATTRS, f"line {n.lineno}: .{f.attr}() is not allowed in bridge.py")

    def test_no_network_or_unsafe_imports(self):
        for n in ast.walk(self.tree):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""] if isinstance(n, ast.ImportFrom) else []
            for m in mods:
                self.assertNotIn(m.split(".")[0], BANNED_IMPORTS, f"line {n.lineno}: import {m}")

    def test_only_git_is_ever_run_and_never_through_a_shell(self):
        runs = 0
        for n in ast.walk(self.tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {"run", "Popen", "call", "check_output", "check_call"}:
                runs += 1
                self.assertTrue(n.args and isinstance(n.args[0], ast.List) and isinstance(n.args[0].elts[0], ast.Constant)
                                and n.args[0].elts[0].value == "git", f"line {n.lineno}: only a literal git command may run")
                for kw in n.keywords:
                    self.assertNotEqual(kw.arg, "shell", f"line {n.lineno}: shell= is not allowed")
        self.assertGreaterEqual(runs, 1)  # the canary itself still sees the git calls

    def test_no_file_removal(self):
        # The only unlink is our own temp file inside write_atomic.
        unlinks = [n for n in ast.walk(self.tree) if isinstance(n, ast.Attribute) and n.attr in {"unlink", "remove", "rmtree", "rmdir"}]
        self.assertLessEqual(len(unlinks), 1)
        text = SRC.read_text()
        self.assertIn("pathlib.Path(tmp).unlink(missing_ok=True)", text)


if __name__ == "__main__":
    unittest.main()
