import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).with_name("studio-tool")
CLAUDE_FPR = "31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE"

# gpg --dearmor copies the key; gpgv reports a good signature by $FAKE_SIGNER.
FAKE_GPG = """#!/bin/sh
cat
"""
FAKE_GPGV = """#!/bin/sh
echo "[GNUPG:] VALIDSIG AAAA 2026-11-05 0 0 4 0 1 10 00 $FAKE_SIGNER"
"""
FAKE_CODESIGN = """#!/bin/sh
[ "$1" = -dv ] && echo "TeamIdentifier=$FAKE_TEAM" >&2
exit 0
"""
# npm ci "installs" the pi package the lock names and records how it was called.
FAKE_NPM = """#!/bin/sh
echo "npm $*" >> "$FAKE_LOG"
cp package-lock.json "$FAKE_LOG.lock"
pkg=node_modules/@earendil-works/pi-coding-agent
mkdir -p "$pkg/dist"
echo '{"bin": {"pi": "dist/cli.js"}}' > "$pkg/package.json"
echo 'console.log("pi")' > "$pkg/dist/cli.js"
"""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def tarball(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def loadout_wheel(version):
    buffer = io.BytesIO()
    info = f"loadout-{version}.dist-info"
    with zipfile.ZipFile(buffer, "w") as wheel:
        wheel.writestr("loadout/__init__.py", f"def main():\n    print('loadout {version}')\n")
        wheel.writestr(f"{info}/METADATA", f"Metadata-Version: 2.1\nName: loadout\nVersion: {version}\n")
        wheel.writestr(f"{info}/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        wheel.writestr(f"{info}/entry_points.txt", "[console_scripts]\nloadout = loadout:main\n")
        wheel.writestr(f"{info}/RECORD", "")
    return buffer.getvalue()


class StudioToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.opt = root / "opt"
        (self.opt / "tools").mkdir(parents=True)
        (self.opt / "bin").mkdir()
        self.sources = root / "sources"
        self.log = root / "npm.log"
        stubs = root / "stubs"
        stubs.mkdir()
        for name, body in [("gpg", FAKE_GPG), ("gpgv", FAKE_GPGV), ("codesign", FAKE_CODESIGN),
                           ("npm", FAKE_NPM), ("node", "#!/bin/sh\n")]:
            (stubs / name).write_text(body)
            (stubs / name).chmod(0o755)
        self.env = {
            "PATH": "/usr/bin:/bin",
            "RC_DEPLOY_ROOT": str(self.opt),
            "STUDIO_TOOL_GITHUB": f"file://{self.sources}/github",
            "STUDIO_TOOL_GITHUB_API": f"file://{self.sources}/api",
            "STUDIO_TOOL_CLAUDE_BASE": f"file://{self.sources}/claude",
            "STUDIO_TOOL_PI_BASE": f"file://{self.sources}/pi",
            "STUDIO_TOOL_PI_RECORDS": f"file://{self.sources}/pi-records",
            "STUDIO_TOOL_PYTHON": sys.executable,
            "STUDIO_TOOL_NODE_BIN": str(stubs),
            "STUDIO_TOOL_GPG": str(stubs / "gpg"),
            "STUDIO_TOOL_GPGV": str(stubs / "gpgv"),
            "STUDIO_TOOL_CODESIGN": str(stubs / "codesign"),
            "FAKE_SIGNER": CLAUDE_FPR,
            "FAKE_TEAM": "Q6L2SF6YDW",
            "FAKE_LOG": str(self.log),
        }

    def write(self, relative, data):
        path = self.sources / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())

    def release(self, repo, tag, assets):
        digests = [{"name": name, "digest": f"sha256:{sha256(data)}"} for name, data in assets.items()]
        self.write(f"api/repos/{repo}/releases/tags/{tag}", json.dumps({"assets": digests}))
        for name, data in assets.items():
            self.write(f"github/{repo}/releases/download/{tag}/{name}", data)

    def publish_claude(self, version, binary=b"claude binary", checksum=None):
        base = f"claude/claude-code-releases/{version}"
        manifest = {"version": version, "platforms": {"darwin-arm64": {"checksum": checksum or sha256(binary)}}}
        self.write(f"{base}/manifest.json", json.dumps(manifest))
        self.write(f"{base}/manifest.json.sig", "sig")
        self.write(f"{base}/darwin-arm64/claude", binary)
        self.write("claude/keys/claude-code.asc", "key")

    def publish_codex(self, version, package_version=None):
        self.env["FAKE_TEAM"] = "2DC432GLL2"
        package = {"version": package_version or version, "target": "aarch64-apple-darwin", "entrypoint": "bin/codex"}
        archive = tarball({"codex-package.json": json.dumps(package).encode(), "bin/codex": b"#!/bin/sh\n"})
        self.release("openai/codex", f"rust-v{version}", {"codex-package-aarch64-apple-darwin.tar.gz": archive})

    def publish_loadout(self, version, dependencies=()):
        lock = f'version = 1\n\n[[package]]\nname = "loadout"\nversion = "{version}"\n'
        lock += f'source = {{ editable = "." }}\ndependencies = [{", ".join(dependencies)}]\n'
        sdist = tarball({f"loadout-{version}/uv.lock": lock.encode()})
        self.release("nielsmadan/loadout", f"v{version}", {
            f"loadout-{version}-py3-none-any.whl": loadout_wheel(version),
            f"loadout-{version}.tar.gz": sdist,
        })

    def publish_pi(self, version, resolved="https://registry.npmjs.org/@earendil-works/pi-coding-agent/-/x.tgz"):
        pi = "@earendil-works/pi-coding-agent"
        self.write(f"pi-records/{version}", json.dumps({
            "version": version, "packages": [{"name": pi, "version": version, "integrity": "sha512-pi"}],
        }))
        self.write(f"pi/{version}/package.json", json.dumps({"version": version, "dependencies": {pi: version}}))
        self.write(f"pi/{version}/package-lock.json", json.dumps({
            "lockfileVersion": 3, "version": version,
            "packages": {
                "": {"version": version, "dependencies": {pi: version}},
                f"node_modules/{pi}": {"version": version, "resolved": resolved},
                "node_modules/chalk": {"version": "6.0.0", "integrity": "sha512-chalk",
                                       "resolved": "https://registry.npmjs.org/chalk/-/chalk-6.0.0.tgz"},
            },
        }))

    def run_tool(self, *args):
        return subprocess.run(["/bin/bash", str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True, timeout=120)

    def current(self, tool):
        link = self.opt / "tools" / tool / "current"
        return os.readlink(link) if link.is_symlink() else None

    def test_refuses_anything_but_an_exact_version_of_a_known_tool(self):
        for args, message in [
            (("install", "claude", "latest"), "'latest' is not an exact version"),
            (("install", "claude", "../../etc"), "'../../etc' is not an exact version"),
            (("install", "claude", "1.2.3/../x"), "'1.2.3/../x' is not an exact version"),
            (("install", "notes", "1.2.3"), "unknown repo or tool 'notes'"),
            (("install", "claude"), "an exact version"),
        ]:
            with self.subTest(args=args):
                result = self.run_tool(*args)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_installs_claude_and_links_its_command(self):
        self.publish_claude("2.1.0")
        result = self.run_tool("install", "claude", "2.1.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.current("claude"), "2.1.0")
        self.assertEqual((self.opt / "bin/claude").read_bytes(), b"claude binary")

    def test_refuses_claude_whose_binary_misses_the_manifest_checksum(self):
        self.publish_claude("2.1.0", checksum="0" * 64)
        result = self.run_tool("install", "claude", "2.1.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected " + "0" * 64, result.stderr)
        self.assertEqual(sorted(p.name for p in (self.opt / "tools/claude").iterdir()), [])

    def test_refuses_a_claude_manifest_signed_by_another_key(self):
        self.publish_claude("2.1.0")
        self.env["FAKE_SIGNER"] = "B" * 40
        result = self.run_tool("install", "claude", "2.1.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"not signed by {CLAUDE_FPR}", result.stderr)

    def test_refuses_a_binary_from_another_apple_team(self):
        self.publish_claude("2.1.0")
        self.env["FAKE_TEAM"] = "OTHERTEAM1"
        result = self.run_tool("install", "claude", "2.1.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("signed by team 'OTHERTEAM1', expected Q6L2SF6YDW", result.stderr)

    def test_a_failed_install_keeps_the_running_version(self):
        self.publish_claude("2.1.0")
        self.run_tool("install", "claude", "2.1.0")
        self.publish_claude("2.2.0", checksum="0" * 64)
        result = self.run_tool("install", "claude", "2.2.0")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.current("claude"), "2.1.0")
        self.assertEqual(sorted(p.name for p in (self.opt / "tools/claude").iterdir()),
                         ["2.1.0", "current", "deploy.log"])

    def test_rollback_switches_back_and_forth(self):
        for version in ("2.1.0", "2.2.0"):
            self.publish_claude(version, binary=version.encode())
            self.run_tool("install", "claude", version)
        result = self.run_tool("rollback", "claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.opt / "bin/claude").read_bytes(), b"2.1.0")
        self.assertEqual(self.run_tool("status", "claude").stdout, "claude: 2.1.0 (rollback to 2.2.0)\n")

    def test_keeps_three_versions(self):
        for version in ("2.1.0", "2.2.0", "2.3.0", "2.4.0"):
            self.publish_claude(version)
            self.assertEqual(self.run_tool("install", "claude", version).returncode, 0)
        self.assertEqual(sorted(p.name for p in (self.opt / "tools/claude").iterdir()),
                         ["2.2.0", "2.3.0", "2.4.0", "current", "deploy.log", "previous"])

    def test_redeploying_an_installed_version_downloads_nothing(self):
        for version in ("2.1.0", "2.2.0"):
            self.publish_claude(version)
            self.run_tool("install", "claude", version)
        (self.sources / "claude").rename(self.sources / "gone")
        result = self.run_tool("install", "claude", "2.1.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.current("claude"), "2.1.0")

    def test_installs_the_codex_package(self):
        self.publish_codex("0.166.0")
        result = self.run_tool("install", "codex", "0.166.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.opt / "bin/codex").read_bytes(), b"#!/bin/sh\n")

    def test_refuses_a_codex_package_for_another_version(self):
        self.publish_codex("0.166.0", package_version="0.165.0")
        result = self.run_tool("install", "codex", "0.166.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("codex-package.json says {'version': '0.165.0'}", result.stderr)

    def test_refuses_an_asset_whose_digest_does_not_match(self):
        self.publish_codex("0.166.0")
        self.write("github/openai/codex/releases/download/rust-v0.166.0/codex-package-aarch64-apple-darwin.tar.gz",
                   b"tampered")
        result = self.run_tool("install", "codex", "0.166.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"sha256 {sha256(b'tampered')}", result.stderr)

    def test_installs_the_loadout_wheel_into_its_own_venv(self):
        self.publish_loadout("1.0.0")
        result = self.run_tool("install", "loadout", "1.0.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        run = subprocess.run([str(self.opt / "bin/loadout")], capture_output=True, text=True)
        self.assertEqual(run.stdout, "loadout 1.0.0\n")

    def test_refuses_a_loadout_lock_it_cannot_read_fully(self):
        self.publish_loadout("1.0.0", dependencies=['{ name = "colorama", marker = "sys_platform == \'win32\'" }'])
        result = self.run_tool("install", "loadout", "1.0.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("gives colorama a marker", result.stderr)

    def test_installs_pi_from_its_lock_with_pis_own_integrity_filled_in(self):
        self.publish_pi("1.4.0")
        result = self.run_tool("install", "pi", "1.4.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("npm ci --ignore-scripts --omit=dev", self.log.read_text())
        lock = json.loads(Path(f"{self.log}.lock").read_text())
        self.assertEqual(lock["packages"]["node_modules/@earendil-works/pi-coding-agent"]["integrity"], "sha512-pi")
        launcher = (self.opt / "bin/pi").read_text()
        self.assertIn(f"/node'", launcher)
        self.assertIn("tools/pi/1.4.0/node_modules/@earendil-works/pi-coding-agent/dist/cli.js", launcher)

    def test_refuses_a_pi_lock_that_resolves_outside_npm(self):
        self.publish_pi("1.4.0", resolved="https://example.com/pi.tgz")
        result = self.run_tool("install", "pi", "1.4.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("comes from outside npm's registry", result.stderr)
        self.assertFalse(self.log.exists())

    def test_status_lists_every_tool(self):
        self.assertEqual(self.run_tool("status").stdout,
                         "loadout: not deployed\nclaude: not deployed\ncodex: not deployed\npi: not deployed\n")


if __name__ == "__main__":
    unittest.main()
