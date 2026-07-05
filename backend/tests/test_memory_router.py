import pytest

from backend.services.memory import CogneeCloudMemoryStore, LocalCogneeMemoryStore, MemoryRouter


class FakeCogneeModule:
    def __init__(self):
        self.remember_calls = []
        self.recall_calls = []
        self.forget_calls = []
        self.memify_calls = []

    async def remember(self, content, dataset_name):
        self.remember_calls.append((content, dataset_name))
        return {"status": "ok"}

    async def recall(self, query, datasets=None):
        self.recall_calls.append((query, datasets))
        return [f"local:{query}"]

    async def forget(self, dataset=None, **kwargs):
        self.forget_calls.append((dataset, kwargs))
        return {"deleted": dataset}

    async def memify(self, dataset=None):
        self.memify_calls.append(dataset)
        return {"improved": dataset}


class FakeCloudClient:
    def __init__(self):
        self.remember_calls = []
        self.recall_calls = []
        self.forget_calls = []
        self.improve_calls = []

    async def remember(self, content, dataset_name):
        self.remember_calls.append((content, dataset_name))
        return {"status": "ok"}

    async def recall(self, query, datasets=None):
        self.recall_calls.append((query, datasets))
        return [f"cloud:{query}"]

    async def forget(self, dataset, memory_only=False):
        self.forget_calls.append((dataset, memory_only))
        return {"forgot": dataset}

    async def improve(self, dataset_name):
        self.improve_calls.append(dataset_name)
        return {"improved": dataset_name}


def test_router_routes_patient_memory_to_local_and_protocol_memory_to_cloud():
    local = FakeCogneeModule()
    cloud = FakeCloudClient()
    router = MemoryRouter(
        local_store=LocalCogneeMemoryStore(local, enabled=True),
        cloud_store=CogneeCloudMemoryStore(cloud, enabled=True, configured=True),
    )

    patient_record = router.remember_patient_event("patient-1", "private patient event")
    protocol_record = router.remember_protocol("protocol-1", "shared protocol")

    assert patient_record.scope == "local_patient"
    assert protocol_record.scope == "cloud_protocol"
    assert local.remember_calls == [("private patient event", "patient-1")]
    assert cloud.remember_calls == [("shared protocol", "protocol-1")]


def test_router_status_reports_real_cognee_backends_when_enabled():
    router = MemoryRouter(
        local_store=LocalCogneeMemoryStore(FakeCogneeModule(), enabled=True),
        cloud_store=CogneeCloudMemoryStore(FakeCloudClient(), enabled=True, configured=True),
    )

    status = router.status()

    assert status.local_backend == "cognee_sdk"
    assert status.cloud_backend == "cognee_cloud_sdk"
    assert status.cloud_configured is True
    assert "JSON fallback" not in status.note


def test_router_construction_defers_cognee_import_until_memory_operation(monkeypatch):
    import backend.services.memory as memory_module

    import_calls: list[str] = []

    def fail_if_imported(name: str):
        import_calls.append(name)
        raise AssertionError("Cognee import should be lazy during router construction")

    monkeypatch.setenv("COGNEE_ENABLE_SDK", "true")
    monkeypatch.setenv("COGNEE_ENABLE_CLOUD", "true")
    monkeypatch.setenv("COGNEE_CLOUD_API_KEY", "test-cloud-key")
    monkeypatch.setattr(memory_module.importlib, "import_module", fail_if_imported)

    router = MemoryRouter()

    status = router.status()
    assert import_calls == []
    assert status.local_backend == "cognee_sdk"
    assert status.cloud_backend == "cognee_cloud_sdk"


def test_router_falls_back_when_cognee_store_raises():
    class BrokenCognee(FakeCogneeModule):
        async def remember(self, content, dataset_name):
            raise RuntimeError("sdk failed")

    router = MemoryRouter(
        local_store=LocalCogneeMemoryStore(BrokenCognee(), enabled=True),
        cloud_store=CogneeCloudMemoryStore(FakeCloudClient(), enabled=True, configured=True),
    )

    record = router.remember_patient_event("patient-1", "private patient event")

    assert record.scope == "local_patient"
    assert record.metadata["backend"] == "json_fallback"
    assert "sdk failed" in record.metadata["fallback_reason"]


def test_router_improves_and_forgets_local_patient_memory_without_touching_cloud():
    local = FakeCogneeModule()
    cloud = FakeCloudClient()
    router = MemoryRouter(
        local_store=LocalCogneeMemoryStore(local, enabled=True),
        cloud_store=CogneeCloudMemoryStore(cloud, enabled=True, configured=True),
    )

    router.improve_patient_memory("patient-1")
    router.forget_patient("patient-1")

    assert local.memify_calls == ["patient-1"]
    assert local.forget_calls == [("patient-1", {})]
    assert cloud.forget_calls == []


def test_router_forgets_protocol_memory_from_cloud_without_touching_local():
    local = FakeCogneeModule()
    cloud = FakeCloudClient()
    router = MemoryRouter(
        local_store=LocalCogneeMemoryStore(local, enabled=True),
        cloud_store=CogneeCloudMemoryStore(cloud, enabled=True, configured=True),
    )

    deleted_records = router.forget_protocol("protocol-1")

    assert deleted_records == 1
    assert cloud.forget_calls == [("protocol-1", False)]
    assert local.forget_calls == []
