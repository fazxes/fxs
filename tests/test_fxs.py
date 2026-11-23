import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


def load_fxs():
    repo_root = Path(__file__).resolve().parent.parent
    loader = importlib.machinery.SourceFileLoader("fxs_mod", str(repo_root / "fxs"))
    spec = importlib.util.spec_from_loader("fxs_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


fxs = load_fxs()


class TestFxs(unittest.TestCase):
    def test_builtin_shims_exist(self):
        shims = fxs.builtin_shims({"fx_channel": "stable"})
        self.assertEqual(set(shims.keys()), {"fx", "claude", "codex", "opencode"})
        self.assertEqual(shims["fx"].launch_command([], resume_id="abc123"), "$HOME/.local/bin/fx -r abc123")
        self.assertEqual(shims["claude"].launch_command([], continue_last=True), "claude --continue")
        self.assertEqual(shims["codex"].launch_command([], resume_id="sess_1"), "codex resume sess_1")
        self.assertEqual(shims["codex"].launch_command([], continue_last=True), "codex resume --last")
        self.assertEqual(shims["opencode"].launch_command([], continue_last=True), "$HOME/.opencode/bin/opencode --continue")

    def test_sanitize_fx_settings_strips_workspaces(self):
        raw = json.dumps({
            "theme": "cursor-dark",
            "sandbox": "os",
            "workspaces": {"/tmp/project": {"permission": {}}},
            "effort": "high",
        })
        out = json.loads(fxs.sanitize_fx_settings(raw))
        self.assertNotIn("workspaces", out)
        self.assertEqual(out["sandbox"], "none")
        self.assertEqual(out["theme"], "cursor-dark")
        self.assertEqual(out["effort"], "high")

    def test_filter_mcp_json_keeps_only_http_and_allowed(self):
        raw = json.dumps({
            "mcp": {
                "local_app": {"command": ["/usr/bin/app"], "type": "local"},
                "slack": {"type": "http", "url": "https://mcp.slack.com/mcp"},
                "linear": {"type": "http", "url": "https://mcp.linear.app/mcp"},
            }
        })
        out_all = json.loads(fxs.filter_mcp_json(raw))
        self.assertEqual(set(out_all["mcp"].keys()), {"slack", "linear"})
        out_one = json.loads(fxs.filter_mcp_json(raw, ["slack"]))
        self.assertEqual(set(out_one["mcp"].keys()), {"slack"})

    def test_parse_timeout_left_s(self):
        self.assertEqual(fxs.parse_timeout_left_s("sbx running 1h iad1 16GB 8 img in 45 minutes"), 2700)
        self.assertEqual(fxs.parse_timeout_left_s("sbx running 1h iad1 16GB 8 img in 2 hours"), 7200)
        self.assertEqual(fxs.parse_timeout_left_s("sbx running 1h iad1 16GB 8 img in 1 hour"), 3600)
        self.assertIsNone(fxs.parse_timeout_left_s("sbx stopped"))

    def test_session_member_regex(self):
        self.assertTrue(fxs.SESSION_MEMBER_RE.fullmatch("abc12345/log.jsonl"))
        self.assertTrue(fxs.SESSION_MEMBER_RE.fullmatch("abc12345/blobs/deadbeef01"))
        self.assertFalse(fxs.SESSION_MEMBER_RE.fullmatch("index.jsonl"))
        self.assertFalse(fxs.SESSION_MEMBER_RE.fullmatch("../etc/passwd"))
        self.assertFalse(fxs.SESSION_MEMBER_RE.fullmatch("abc12345/lock"))

    def test_custom_shim_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = fxs.CUSTOM_AGENTS_DIR
            try:
                fxs.CUSTOM_AGENTS_DIR = Path(tmp)
                (Path(tmp) / "mybot.json").write_text(json.dumps({
                    "name": "mybot",
                    "bin_path": "/usr/local/bin/mybot",
                    "resume_flag": "--session",
                }))
                shims = fxs.all_shims()
                self.assertIn("mybot", shims)
                self.assertEqual(shims["mybot"].launch_command(["--fast"], resume_id="s1"), "/usr/local/bin/mybot --session s1 --fast")
            finally:
                fxs.CUSTOM_AGENTS_DIR = old_dir

    def test_base_setup_script_generation(self):
        cfg = {
            "team": "acme",
            "project": "sandboxes",
            "tools": ["gh", "zig", "bun"],
            "fx_channel": "stable",
            "skill_repos": [],
            "warm_repos": [],
        }
        script = fxs.build_base_setup_script(cfg, ["fx", "claude"])
        self.assertIn("dtach", script)
        self.assertIn("openssh-client", script)
        self.assertIn("tailscaled", script)
        self.assertIn("fxs-attach", script)
        self.assertIn("zig", script)
        self.assertIn("bun", script)
        self.assertIn("https://fx.sh/setup.sh", script)
        self.assertIn("@anthropic-ai/claude-code", script)

    def test_extract_local_image_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            img1 = Path(tmp) / "clip-123.png"
            img1.write_bytes(b"png")
            img2 = Path(tmp) / "my shot.jpg"
            img2.write_bytes(b"jpg")
            missing = Path(tmp) / "nope.png"

            raw = f"\x1b[200~{img1}\n{missing}\x1b[201~".encode()
            self.assertEqual(fxs.extract_local_image_paths(raw), [str(img1)])

            escaped = str(img2).replace(" ", "\\ ").encode()
            self.assertEqual(fxs.extract_local_image_paths(escaped), [str(img2)])

    def test_signing_setup_script_has_ssh_config(self):
        self.assertIn("gpg.format ssh", fxs.SIGNING_SETUP_SCRIPT)
        self.assertIn("commit.gpgsign true", fxs.SIGNING_SETUP_SCRIPT)
        self.assertIn("fxs_signing", fxs.SIGNING_SETUP_SCRIPT)

    def test_parse_teams_output_handles_stderr_table_and_vercel_slug(self):
        sample = (
            "Vercel CLI 66.6.0\n"
            "\x1b[90mid                         Team name          Plan\x1b[0m\n"
            "acme-personal              acme-personal      pro\n"
            "vercel                     Vercel             enterprise\n"
            "my-team_1                  My Team            enterprise\n"
        )
        self.assertEqual(fxs.parse_teams_output(sample), ["acme-personal", "vercel", "my-team_1"])

    def test_resolve_default_project(self):
        self.assertEqual(fxs.resolve_default_project(None), "vercel-sandbox-default-project")
        self.assertEqual(fxs.resolve_default_project(""), "vercel-sandbox-default-project")
        self.assertEqual(fxs.resolve_default_project("custom-proj"), "custom-proj")


if __name__ == "__main__":
    unittest.main()
