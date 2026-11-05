"""End to end: a fresh clone of this repo, then only the commands printed in the README quickstart."""
import os, pathlib, re, shutil, subprocess, sys, tempfile, unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BLOCK_RE = re.compile(r"<!-- test: quickstart -->\n```sh\n(.*?)```", re.S)
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.com", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True, text=True)


class CleanCloneTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_readme_quickstart_works_in_a_fresh_clone(self):
        # Publish the current files (tracked and new, not ignored) to a bare "remote", then clone it, as a user would.
        seed = self.tmp / "seed"
        seed.mkdir()
        files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=REPO, capture_output=True, text=True).stdout.split()
        for f in files:
            if (REPO / f).is_file():
                (seed / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO / f, seed / f)
        subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], env=ENV, check=True)
        git("add", "-A", cwd=seed)
        git("commit", "-qm", "seed", cwd=seed)
        remote = self.tmp / "remote.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(remote)], env=ENV, check=True)
        work = self.tmp / "work"
        subprocess.run(["git", "clone", "-q", str(remote), str(work)], env=ENV, check=True)

        block = BLOCK_RE.search((REPO / "README.md").read_text()).group(1)
        lines = [l for l in block.splitlines() if "unittest" not in l]  # the suite is already running; avoid recursion
        script = "set -e\n" + "\n".join(lines) + "\n"
        r = subprocess.run(["sh", "-c", script], cwd=work, env=ENV, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"quickstart failed:\n{r.stdout}\n{r.stderr}")
        self.assertIn("valid", r.stdout)
        self.assertTrue((work / "done" / "WEBAPP-AUDIT.md").exists())
        self.assertEqual(git("status", "--porcelain", cwd=work).stdout, "")  # everything committed
        self.assertEqual(git("rev-parse", "HEAD", cwd=work).stdout, git("rev-parse", "HEAD", cwd=remote).stdout)  # and pushed


if __name__ == "__main__":
    unittest.main()
