from __future__ import annotations

from types import SimpleNamespace

from imgtagplus import profiler


def _vm(total_gb: float, available_gb: float) -> SimpleNamespace:
    gib = 1024 ** 3
    return SimpleNamespace(total=total_gb * gib, available=available_gb * gib)


def test_get_system_specs_reports_cpu_memory(monkeypatch) -> None:
    monkeypatch.setattr(profiler.psutil, "virtual_memory", lambda: _vm(16, 12))
    monkeypatch.setattr(profiler.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(profiler.platform, "system", lambda: "Linux")
    monkeypatch.setattr(profiler.platform, "machine", lambda: "x86_64")

    specs = profiler.get_system_specs()

    assert specs == {
        "os": "Linux",
        "arch": "x86_64",
        "total_ram_gb": 16.0,
        "available_ram_gb": 12.0,
        "vram_gb": 0.0,
        "accelerator": "cpu",
    }


def test_get_system_specs_reports_mps_on_apple_silicon(monkeypatch) -> None:
    monkeypatch.setattr(profiler.psutil, "virtual_memory", lambda: _vm(24, 18))
    monkeypatch.setattr(profiler.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(profiler.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(profiler.platform, "machine", lambda: "arm64")

    specs = profiler.get_system_specs()

    assert specs["accelerator"] == "mps"
    assert specs["vram_gb"] == 24.0


def test_get_model_recommendations_warn_for_unsupported_cpu(monkeypatch) -> None:
    monkeypatch.setattr(
        profiler,
        "get_system_specs",
        lambda: {
            "os": "Linux",
            "arch": "x86_64",
            "total_ram_gb": 8.0,
            "available_ram_gb": 2.0,
            "vram_gb": 0.0,
            "accelerator": "cpu",
        },
    )

    recommendations = profiler.get_model_recommendations()
    recommendations_by_key = {item["key"]: item for item in recommendations}

    assert recommendations_by_key["clip"]["supported"] is True
    assert recommendations_by_key["florence-2-base"]["supported"] is False
    assert recommendations_by_key["florence-2-base"]["warning"] == (
        "Requires at least 3.0GB free RAM."
    )


def test_get_profiler_summary_rates_accelerated_system_as_excellent(monkeypatch) -> None:
    monkeypatch.setattr(
        profiler,
        "get_system_specs",
        lambda: {
            "os": "Darwin",
            "arch": "arm64",
            "total_ram_gb": 32.0,
            "available_ram_gb": 20.0,
            "vram_gb": 32.0,
            "accelerator": "mps",
        },
    )
    monkeypatch.setattr(profiler, "get_model_recommendations", lambda: [{"key": "clip"}])

    summary = profiler.get_profiler_summary()

    assert summary["performance_rating"] == "Excellent"
    assert summary["models"] == [{"key": "clip"}]
