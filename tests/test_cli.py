from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import imgtagplus.cli as cli


def test_start_server_daemon_does_not_restart_when_mode_matches(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "imgtagplus.pid"
    state_file = tmp_path / "imgtagplus.json"
    pid_file.write_text("123")
    state_file.write_text('{"ffsa": false, "sandbox_dir": null}')

    monkeypatch.setattr(cli, "PID_FILE", pid_file)
    monkeypatch.setattr(cli, "STATE_FILE", state_file)
    monkeypatch.setattr(cli, "_is_process_running", lambda pid: True)
    monkeypatch.setattr(cli, "stop_server_daemon", lambda: (_ for _ in ()).throw(AssertionError("should not stop")))
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not spawn")),
    )

    cli.start_server_daemon(ffsa=False)

    assert pid_file.read_text() == "123"
    assert state_file.read_text() == '{"ffsa": false, "sandbox_dir": null}'


def test_start_server_daemon_restarts_when_selected_mode_differs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "imgtagplus.pid"
    state_file = tmp_path / "imgtagplus.json"
    pid_file.write_text("123")
    state_file.write_text('{"ffsa": false, "sandbox_dir": null}')

    stop_calls: list[str] = []
    popen_calls: list[dict[str, object]] = []

    monkeypatch.setattr(cli, "PID_FILE", pid_file)
    monkeypatch.setattr(cli, "STATE_FILE", state_file)
    monkeypatch.setattr(cli, "_is_process_running", lambda pid: True)
    monkeypatch.setattr(cli, "_wait_for_server_ready", lambda url: True)
    monkeypatch.setattr(cli, "stop_server_daemon", lambda: stop_calls.append("stop"))
    monkeypatch.setattr(cli.time, "sleep", lambda *_args, **_kwargs: None)

    def fake_popen(command, stdout, stderr, env, start_new_session):
        popen_calls.append(
            {
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "env": env,
                "start_new_session": start_new_session,
            }
        )
        return SimpleNamespace(pid=456)

    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    cli.start_server_daemon(ffsa=True)

    assert stop_calls == ["stop"]
    assert len(popen_calls) == 1
    assert popen_calls[0]["env"]["IMGTAGPLUS_FFSA"] == "1"
    assert pid_file.read_text() == "456"
    assert cli._load_server_config() == {"ffsa": True, "sandbox_dir": None}


def test_restart_server_daemon_preserves_saved_mode(monkeypatch, tmp_path: Path) -> None:
    state_file = tmp_path / "imgtagplus.json"
    monkeypatch.setattr(cli, "STATE_FILE", state_file)
    cli._save_server_config(ffsa=True, sandbox_dir=None)

    calls: list[tuple[str, object, object]] = []
    monkeypatch.setattr(cli, "stop_server_daemon", lambda: calls.append(("stop", None, None)))
    monkeypatch.setattr(
        cli,
        "start_server_daemon",
        lambda ffsa=False, sandbox_dir=None: calls.append(("start", ffsa, sandbox_dir)),
    )
    monkeypatch.setattr(cli.time, "sleep", lambda *_args, **_kwargs: None)

    cli.restart_server_daemon()

    assert calls == [("stop", None, None), ("start", True, None)]


def test_restart_server_daemon_uses_explicit_target_mode(
    monkeypatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "imgtagplus.json"
    monkeypatch.setattr(cli, "STATE_FILE", state_file)
    cli._save_server_config(ffsa=True, sandbox_dir=None)

    calls: list[tuple[str, object, object]] = []
    monkeypatch.setattr(cli, "stop_server_daemon", lambda: calls.append(("stop", None, None)))
    monkeypatch.setattr(
        cli,
        "start_server_daemon",
        lambda ffsa=False, sandbox_dir=None: calls.append(("start", ffsa, sandbox_dir)),
    )
    monkeypatch.setattr(cli.time, "sleep", lambda *_args, **_kwargs: None)

    cli.restart_server_daemon(ffsa=False, sandbox_dir="/tmp/custom-sandbox")

    assert calls == [("stop", None, None), ("start", False, "/tmp/custom-sandbox")]
