import asyncio
import base64
import binascii
import fcntl
import hashlib
import hmac
import json
import os
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

RESUME_VAR = "user.rcAgentResume"
DISABLED_VAR = "user.rcAgentDisabled"
RECIPES = {
    "claude": "claude",
    "claude-raw": "claude",
    "clor": "claude",
    "codex": "codex",
    "codex-raw": "codex",
}
MARKER = "rc-agent-restore-v1"
STARTUP_KEYS = ("Command", "Custom Command")
LAUNCH_SCRIPT = (
    'if [[ -x $1 && -f $2 ]]; then "$1" "$2" --restore "$3"; '
    'else print -u2 "Agent resume helper unavailable; opening a shell."; fi; '
    "exec /bin/zsh -l"
)


def pane_id(value):
    if not isinstance(value, str):
        raise TypeError("missing pane ID")
    return str(UUID(value.rsplit(":", 1)[-1])).upper()


def object_value(value):
    if value in (None, ""):
        return None
    data = json.loads(value) if isinstance(value, str) else value
    if not isinstance(data, dict):
        raise TypeError("expected an object")
    return data


def validate_record(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise TypeError("unsupported resume record version")
    if data.get("agent") not in ("claude", "codex"):
        raise ValueError("unsupported agent")
    identity = data.get("session")
    if (
        not isinstance(identity, str)
        or not identity
        or len(identity) > 256
        or identity.startswith("-")
    ):
        raise ValueError("invalid agent session ID")
    UUID(identity)
    pane_id(data.get("pane"))
    if not isinstance(data.get("process"), str):
        raise TypeError("invalid process identity")
    if (
        not isinstance(data.get("cwd"), str)
        or not os.path.isabs(data["cwd"])
        or "\0" in data["cwd"]
    ):
        raise ValueError("invalid working directory")
    recipe = data.get("recipe")
    if recipe is not None and RECIPES.get(recipe) != data["agent"]:
        raise ValueError("invalid launch recipe")
    if type(data.get("forceSandbox")) is not bool:
        raise ValueError("invalid sandbox preference")
    original = data.get("original")
    if not isinstance(original, dict) or set(original) != set(STARTUP_KEYS):
        raise ValueError("missing original startup settings")
    if not isinstance(original["Command"], str) or original["Custom Command"] not in (
        "Yes",
        "No",
    ):
        raise ValueError("invalid original startup settings")
    if MARKER in original["Command"]:
        raise ValueError("original startup command still contains a resume wrapper")
    return data


def encode_record(record):
    return base64.urlsafe_b64encode(
        json.dumps(validate_record(record), separators=(",", ":")).encode()
    ).decode()


def decode_record(token):
    if not isinstance(token, str) or len(token) > 65536:
        raise ValueError("resume record too large")
    try:
        return validate_record(
            json.loads(base64.b64decode(token, altchars=b"-_", validate=True))
        )
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid resume record") from exc


def resume_command(record, python, helper):
    return shlex.join(
        [
            "/bin/zsh",
            "-c",
            LAUNCH_SCRIPT,
            MARKER,
            str(python),
            str(helper),
            encode_record(record),
        ]
    )


def command_record(command):
    if MARKER not in command:
        return None
    parts = shlex.split(command)
    if len(parts) != 7 or parts[:2] != ["/bin/zsh", "-c"] or parts[3] != MARKER:
        raise ValueError("unrecognized resume command; keeping profile unchanged")
    return decode_record(parts[6])


def presence_sessions(text):
    data = json.loads(text)
    if (
        not isinstance(data, dict)
        or data.get("protocol") != 1
        or not isinstance(data.get("sessions"), list)
    ):
        raise TypeError("unsupported HooklineSinker response")
    problems = data.get("problems", [])
    if not isinstance(problems, list):
        raise TypeError("invalid HooklineSinker problems")
    for problem in problems:
        kind = problem.get("kind") if isinstance(problem, dict) else None
        if not isinstance(kind, dict) or kind.get("type") != "sink":
            raise ValueError("HooklineSinker cannot establish reliable presence")
    for row in data["sessions"]:
        if not isinstance(row, dict) or type(row.get("running")) is not bool:
            raise TypeError("invalid HooklineSinker session")
        if not isinstance(row.get("session"), dict) or not isinstance(
            row["session"].get("id"), str
        ):
            raise TypeError("invalid HooklineSinker identity")
    return [row for row in data["sessions"] if row["running"]]


def local_bindings(rows):
    candidates = {}
    for row in rows:
        terminal = row.get("terminal") or {}
        if not isinstance(terminal, dict):
            continue
        if (
            row.get("remoteHost")
            or row.get("tmux")
            or terminal.get("terminalType") != "iterm2"
        ):
            continue
        try:
            key = pane_id(terminal.get("sessionId"))
        except (TypeError, ValueError):
            continue
        candidates.setdefault(key, []).append(row)
    return {key: values[0] for key, values in candidates.items() if len(values) == 1}


def process_table(text):
    return {
        int(pid): {"parent": int(parent), "startedAt": started.strip()}
        for pid, parent, started in (line.split(None, 2) for line in text.splitlines())
    }


def is_descendant(pid, ancestor, processes):
    seen = set()
    while pid and pid not in seen:
        if pid == ancestor:
            return True
        seen.add(pid)
        pid = processes.get(pid, {}).get("parent")
    return False


def binding_record(row, launch, original, processes, pane):
    recipe = None
    generation = None
    forced = False
    cwd = row["session"].get("cwd")
    pid = (row.get("process") or {}).get("pid")
    process = processes.get(pid, {})
    if (
        launch
        and not launch.get("finished")
        and isinstance(launch.get("token"), str)
        and isinstance(launch.get("priorProcesses"), list)
        and process
        and f"{pid}:{process.get('startedAt', '')}" not in launch["priorProcesses"]
        and launch.get("version") == 1
        and RECIPES.get(launch.get("recipe")) == row.get("agent")
        and type(launch.get("pid")) is int
        and launch.get("startedAt") == processes.get(launch["pid"], {}).get("startedAt")
        and is_descendant(pid, launch["pid"], processes)
    ):
        generation = str(UUID(launch["token"]))
        recipe = launch["recipe"]
        forced = launch.get("forceSandbox") is True
        cwd = launch["cwd"]
    return validate_record(
        {
            "version": 1,
            "agent": row["agent"],
            "session": row["session"]["id"],
            "cwd": cwd,
            "recipe": recipe,
            "generation": generation,
            "forceSandbox": forced,
            "original": original,
            "pane": pane_id(pane),
            "process": f"{pid}:{process.get('startedAt', '')}" if process else "",
        }
    )


def private_directory(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("agent resume state directory must be private")
    directory.chmod(0o700)


def private_read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("agent resume state file must be private")
        data = handle.read(65537)
        if len(data) > 65536:
            raise ValueError("agent resume state file too large")
        return data


def signing_key(directory):
    private_directory(directory)
    path = directory / "signing-key"
    if not path.exists():
        fd, temporary = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(os.urandom(32))
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass
        finally:
            Path(temporary).unlink()
    key = private_read(path)
    if len(key) != 32:
        raise ValueError("invalid resume signing key")
    return key


def sign_record(record, key):
    payload = {
        name: value
        for name, value in validate_record(record).items()
        if name != "signature"
    }
    signature = hmac.new(
        key,
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
        hashlib.sha256,
    ).hexdigest()
    return {**payload, "signature": signature}


def verify_record(record, key, pane=None):
    expected = sign_record(record, key)
    signature = record.get("signature")
    if not isinstance(signature, str) or not hmac.compare_digest(
        signature, expected["signature"]
    ):
        raise ValueError("resume record is unsigned or was modified")
    if pane is not None and record["pane"] != pane_id(pane):
        raise ValueError("resume record belongs to a different pane")
    return record


def launch_record(directory, pane):
    path = directory / "launches" / (pane_id(pane) + ".json")
    try:
        return object_value(json.loads(private_read(path)))
    except FileNotFoundError:
        return None


def launch_ended(directory, record):
    token = record.get("generation")
    if not token:
        return False
    path = directory / "outcomes" / (str(UUID(token)) + ".json")
    try:
        outcome = json.loads(private_read(path))
    except FileNotFoundError:
        return False
    return outcome.get("ended") is True and outcome.get("pane") == record["pane"]


async def command_output(argv, timeout=3):
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "LC_ALL": "C"},
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except (TimeoutError, asyncio.CancelledError):
        if proc.returncode is None:
            proc.kill()
        await proc.communicate()
        raise
    if proc.returncode:
        raise RuntimeError(
            f"{Path(argv[0]).name} failed ({proc.returncode}): {err.decode(errors='replace').strip()}"
        )
    return out.decode()


def presence_binary(home):
    return home / ".local/share/hooklinesinker/bin/hooklinesinker"


class SessionLock:
    def __init__(self, directory, agent, identity):
        self.path = directory / (
            hashlib.sha256((agent + ":" + identity).encode()).hexdigest() + ".lock"
        )
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise
        return self

    def __exit__(self, *_):
        os.close(self.fd)
        self.fd = None


def agent_argv(record):
    validate_record(record)
    recipe = record["recipe"]
    if recipe is None:
        raise ValueError(
            "launch mode unknown; resume manually once through an updated wrapper"
        )
    args = (
        ["--resume", record["session"]]
        if record["agent"] == "claude"
        else ["resume", record["session"]]
    )
    script = '(( $+functions[$1] )) || { print -u2 "Agent wrapper unavailable: $1"; exit 78; }; "$@"'
    return ["/bin/zsh", "-lic", script, "rc-agent", recipe, *args]


def run_agent(record, home, env, runner=subprocess.run):
    verify_record(record, signing_key(home / ".local/state/iterm-agent-resume"))
    argv = agent_argv(record)
    if not Path(record["cwd"]).is_dir():
        raise ValueError(f"working directory is missing: {record['cwd']}")
    with SessionLock(
        home / ".local/state/iterm-agent-resume/locks",
        record["agent"],
        record["session"],
    ):
        result = runner(
            [str(presence_binary(home)), "sessions", "--json"],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
        rows = presence_sessions(result.stdout)
        if any(
            row.get("agent") == record["agent"]
            and row["session"]["id"] == record["session"]
            for row in rows
        ):
            raise ValueError(
                "this agent conversation is already running; opening a shell"
            )
        launch_env = {
            key: value
            for key, value in env.items()
            if key != "AGENT_ITERM_LAUNCH_ACTIVE"
        }
        launch_env["AGENT_REQUIRE_SECRETS"] = "1"
        if record["forceSandbox"]:
            launch_env["AGENT_FORCE_SANDBOX"] = "1"
            launch_env["AGENT_REQUIRE_SANDBOX"] = "1"
        return runner(argv, cwd=record["cwd"], env=launch_env).returncode
