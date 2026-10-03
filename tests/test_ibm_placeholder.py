from qec_cloud.ibm_hardware import validate_ibm_environment


def test_ibm_environment_returns_optional_credentials(monkeypatch):
    monkeypatch.delenv("IBM_QUANTUM_TOKEN", raising=False)
    monkeypatch.delenv("IBM_QUANTUM_INSTANCE", raising=False)

    token, instance = validate_ibm_environment()
    assert token is None
    assert instance is None
