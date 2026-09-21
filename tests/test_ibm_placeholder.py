import pytest

from qec_cloud.ibm_hardware import validate_ibm_environment


def test_ibm_placeholder_refuses_without_credentials(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    monkeypatch.delenv("IBM_QUANTUM_INSTANCE", raising=False)

    with pytest.raises(RuntimeError):
        validate_ibm_environment()
