import pytest

from qec_cloud.ibm_hardware import run_ibm_hardware_validation, validate_ibm_environment


def test_ibm_environment_returns_optional_credentials(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    monkeypatch.delenv("IBM_QUANTUM_INSTANCE", raising=False)

    token, instance = validate_ibm_environment()
    assert token is None
    assert instance is None


def test_ibm_placeholder_refuses_without_token(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    monkeypatch.delenv("IBM_QUANTUM_INSTANCE", raising=False)

    with pytest.raises(RuntimeError, match="IBM_QUANTUM_TOKEN is required"):
        run_ibm_hardware_validation()
