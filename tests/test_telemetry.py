from app.telemetry import _nvidia_metrics


def test_nvidia_metrics_parses_valid_output(monkeypatch):
    class Result:
        returncode = 0
        stdout = "NVIDIA GeForce RTX 3060 Ti, 42, 61\n"
    monkeypatch.setattr("app.telemetry.shutil.which", lambda _: "nvidia-smi")
    monkeypatch.setattr("app.telemetry.subprocess.run", lambda *args, **kwargs: Result())
    assert _nvidia_metrics() == ("NVIDIA GeForce RTX 3060 Ti", 42.0, 61.0)


def test_nvidia_metrics_handles_missing_utility(monkeypatch):
    monkeypatch.setattr("app.telemetry.shutil.which", lambda _: None)
    assert _nvidia_metrics() == (None, None, None)
