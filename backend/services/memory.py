from __future__ import annotations

import asyncio
import importlib
import os
import threading
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.models.clinical import MemoryRecord, MemoryStatus


def load_backend_env(env_file: Path | None = None) -> None:
    target = env_file or Path(os.getenv("MEDGRAPH_ENV_FILE", Path(__file__).resolve().parents[1] / ".env"))
    load_dotenv(dotenv_path=target, override=True)


load_backend_env()


def _format_exception(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__


def _run_async(awaitable: Awaitable[Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(awaitable)
        except BaseException as exc:  # pragma: no cover - defensive thread bridge
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


class JsonFallbackMemoryStore:
    backend_name = "json_fallback"

    def __init__(self, scope: str) -> None:
        self.scope = scope
        self.records: list[MemoryRecord] = []

    @property
    def record_count(self) -> int:
        return len(self.records)

    def remember(self, dataset_id: str, content: str, metadata: dict | None = None) -> MemoryRecord:
        record = MemoryRecord(
            scope=self.scope,  # type: ignore[arg-type]
            dataset_id=dataset_id,
            content=content,
            metadata={"backend": self.backend_name, **(metadata or {})},
        )
        self.records.append(record)
        return record

    def recall(self, query: str) -> list[MemoryRecord]:
        terms = query.lower().split()
        if not terms:
            return list(self.records)
        return [
            record
            for record in self.records
            if any(term in record.content.lower() for term in terms)
        ]

    def improve(self, dataset_id: str) -> MemoryRecord:
        return self.remember(
            dataset_id=dataset_id,
            content=f"Improved memory dataset {dataset_id}",
            metadata={"operation": "improve"},
        )

    def forget(self, dataset_id: str) -> int:
        before = len(self.records)
        self.records = [record for record in self.records if record.dataset_id != dataset_id]
        return before - len(self.records)


class LocalCogneeMemoryStore:
    backend_name = "cognee_sdk"

    def __init__(
        self,
        cognee_module: Any | None = None,
        enabled: bool = True,
        module_loader: Callable[[], Any] | None = None,
    ) -> None:
        self.cognee = cognee_module
        self.enabled = enabled
        self._module_loader = module_loader
        self._configured = False
        self.fallback = JsonFallbackMemoryStore("local_patient")
        self._record_count = 0

    @property
    def record_count(self) -> int:
        return self._record_count + self.fallback.record_count

    def remember(self, dataset_id: str, content: str, metadata: dict | None = None) -> MemoryRecord:
        if not self.enabled:
            return self._fallback_remember(dataset_id, content, metadata, "local Cognee SDK disabled")
        try:
            self._ensure_module_loaded()
            _run_async(self._remember(dataset_id, content))
        except Exception as exc:
            return self._fallback_remember(dataset_id, content, metadata, _format_exception(exc))
        self._record_count += 1
        return MemoryRecord(
            scope="local_patient",
            dataset_id=dataset_id,
            content=content,
            metadata={"backend": self.backend_name, **(metadata or {})},
        )

    def recall(self, query: str) -> list[MemoryRecord]:
        if not self.enabled:
            return self.fallback.recall(query)
        try:
            self._ensure_module_loaded()
            raw_results = _run_async(self._recall(query)) or []
        except Exception:
            return self.fallback.recall(query)
        return [
            MemoryRecord(
                scope="local_patient",
                dataset_id="local-cognee-results",
                content=str(result),
                metadata={"backend": self.backend_name},
            )
            for result in raw_results
        ]

    def improve(self, dataset_id: str) -> MemoryRecord:
        if not self.enabled:
            return self.fallback.improve(dataset_id)
        try:
            self._ensure_module_loaded()
            _run_async(self._improve(dataset_id))
        except Exception as exc:
            return self.fallback.remember(
                dataset_id=dataset_id,
                content=f"Fallback improve for {dataset_id}",
                metadata={"operation": "improve", "fallback_reason": _format_exception(exc)},
            )
        return MemoryRecord(
            scope="local_patient",
            dataset_id=dataset_id,
            content=f"Improved local Cognee dataset {dataset_id}",
            metadata={"backend": self.backend_name, "operation": "improve"},
        )

    def forget(self, dataset_id: str) -> int:
        if not self.enabled:
            return self.fallback.forget(dataset_id)
        try:
            self._ensure_module_loaded()
            _run_async(self._forget(dataset_id))
        except Exception:
            return self.fallback.forget(dataset_id)
        return 1

    def _ensure_module_loaded(self) -> None:
        if self.cognee is not None:
            return
        if self._module_loader is None:
            raise RuntimeError("Cognee SDK module loader is not configured")
        self.cognee = self._module_loader()

    async def _remember(self, dataset_id: str, content: str) -> None:
        await asyncio.wait_for(
            self._remember_inner(dataset_id, content),
            timeout=float(os.getenv("COGNEE_LOCAL_OPERATION_TIMEOUT", "12")),
        )

    async def _recall(self, query: str) -> list[Any]:
        return await asyncio.wait_for(
            self._recall_inner(query),
            timeout=float(os.getenv("COGNEE_LOCAL_OPERATION_TIMEOUT", "12")),
        )

    async def _improve(self, dataset_id: str) -> None:
        await asyncio.wait_for(
            self._improve_inner(dataset_id),
            timeout=float(os.getenv("COGNEE_LOCAL_OPERATION_TIMEOUT", "12")),
        )

    async def _forget(self, dataset_id: str) -> None:
        await asyncio.wait_for(
            self._forget_inner(dataset_id),
            timeout=float(os.getenv("COGNEE_LOCAL_OPERATION_TIMEOUT", "12")),
        )

    async def _remember_inner(self, dataset_id: str, content: str) -> None:
        await self._ensure_configured()
        if hasattr(self.cognee, "remember"):
            try:
                await _maybe_await(
                    self.cognee.remember(
                        content,
                        dataset_name=dataset_id,
                        self_improvement=False,
                    )
                )
            except TypeError:
                await _maybe_await(self.cognee.remember(content, dataset_name=dataset_id))
            return
        if hasattr(self.cognee, "add"):
            await _maybe_await(self.cognee.add(content, dataset_name=dataset_id))
            if hasattr(self.cognee, "cognify"):
                await _maybe_await(self.cognee.cognify(datasets=[dataset_id]))
            return
        raise RuntimeError("Cognee SDK does not expose remember or add")

    async def _recall_inner(self, query: str) -> list[Any]:
        await self._ensure_configured()
        if hasattr(self.cognee, "recall"):
            try:
                return await _maybe_await(self.cognee.recall(query_text=query))
            except TypeError:
                return await _maybe_await(self.cognee.recall(query))
        if hasattr(self.cognee, "search"):
            return await _maybe_await(self.cognee.search(query))
        raise RuntimeError("Cognee SDK does not expose recall or search")

    async def _improve_inner(self, dataset_id: str) -> None:
        await self._ensure_configured()
        if hasattr(self.cognee, "improve"):
            await _maybe_await(self.cognee.improve(dataset=dataset_id))
            return
        if hasattr(self.cognee, "memify"):
            await _maybe_await(self.cognee.memify(dataset=dataset_id))
            return
        raise RuntimeError("Cognee SDK does not expose memify or improve")

    async def _forget_inner(self, dataset_id: str) -> None:
        await self._ensure_configured()
        if hasattr(self.cognee, "forget"):
            await _maybe_await(self.cognee.forget(dataset=dataset_id))
            return
        if hasattr(self.cognee, "prune"):
            await _maybe_await(self.cognee.prune(dataset=dataset_id))
            return
        raise RuntimeError("Cognee SDK does not expose forget")

    async def _ensure_configured(self) -> None:
        if self._configured:
            return
        if not hasattr(self.cognee, "config"):
            self._configured = True
            return
        from backend.config import setup_cognee

        await setup_cognee()
        self._configured = True

    def _fallback_remember(
        self,
        dataset_id: str,
        content: str,
        metadata: dict | None,
        reason: str,
    ) -> MemoryRecord:
        return self.fallback.remember(
            dataset_id=dataset_id,
            content=content,
            metadata={**(metadata or {}), "fallback_reason": reason},
        )


class CogneeCloudMemoryStore:
    backend_name = "cognee_cloud_sdk"

    def __init__(
        self,
        cloud_client: Any | None = None,
        enabled: bool = True,
        configured: bool = False,
        client_loader: Callable[[], Any] | None = None,
    ) -> None:
        self.client = cloud_client
        self.enabled = enabled
        self.configured = configured
        self._client_loader = client_loader
        self._served = False
        self.fallback = JsonFallbackMemoryStore("cloud_protocol")
        self._record_count = 0

    @property
    def record_count(self) -> int:
        return self._record_count + self.fallback.record_count

    def remember(self, dataset_id: str, content: str, metadata: dict | None = None) -> MemoryRecord:
        if not self.enabled or not self.configured:
            return self._fallback_remember(dataset_id, content, metadata, "Cognee Cloud not configured")
        try:
            self._ensure_client_loaded()
            _run_async(self._remember(dataset_id, content))
        except Exception as exc:
            return self._fallback_remember(dataset_id, content, metadata, _format_exception(exc))
        self._record_count += 1
        return MemoryRecord(
            scope="cloud_protocol",
            dataset_id=dataset_id,
            content=content,
            metadata={"backend": self.backend_name, **(metadata or {})},
        )

    def recall(self, query: str) -> list[MemoryRecord]:
        if not self.enabled or not self.configured:
            return self.fallback.recall(query)
        try:
            self._ensure_client_loaded()
            raw_results = _run_async(self._recall(query)) or []
        except Exception:
            return self.fallback.recall(query)
        return [
            MemoryRecord(
                scope="cloud_protocol",
                dataset_id="cloud-cognee-results",
                content=str(result),
                metadata={"backend": self.backend_name},
            )
            for result in raw_results
        ]

    def improve(self, dataset_id: str) -> MemoryRecord:
        if not self.enabled or not self.configured:
            return self.fallback.improve(dataset_id)
        try:
            self._ensure_client_loaded()
            _run_async(self._improve(dataset_id))
        except Exception as exc:
            return self.fallback.remember(
                dataset_id=dataset_id,
                content=f"Fallback cloud improve for {dataset_id}",
                metadata={"operation": "improve", "fallback_reason": _format_exception(exc)},
            )
        return MemoryRecord(
            scope="cloud_protocol",
            dataset_id=dataset_id,
            content=f"Improved Cognee Cloud dataset {dataset_id}",
            metadata={"backend": self.backend_name, "operation": "improve"},
        )

    def forget(self, dataset_id: str) -> int:
        if not self.enabled or not self.configured:
            return self.fallback.forget(dataset_id)
        try:
            self._ensure_client_loaded()
            _run_async(self._forget(dataset_id))
        except Exception:
            return self.fallback.forget(dataset_id)
        return 1

    def _ensure_client_loaded(self) -> None:
        if self.client is not None:
            return
        if self._client_loader is None:
            raise RuntimeError("Cognee Cloud client loader is not configured")
        self.client = self._client_loader()

    async def _remember(self, dataset_id: str, content: str) -> None:
        await asyncio.wait_for(
            self._remember_inner(dataset_id, content),
            timeout=float(os.getenv("COGNEE_CLOUD_OPERATION_TIMEOUT", "20")),
        )

    async def _recall(self, query: str) -> list[Any]:
        return await asyncio.wait_for(
            self._recall_inner(query),
            timeout=float(os.getenv("COGNEE_CLOUD_OPERATION_TIMEOUT", "20")),
        )

    async def _improve(self, dataset_id: str) -> None:
        await asyncio.wait_for(
            self._improve_inner(dataset_id),
            timeout=float(os.getenv("COGNEE_CLOUD_OPERATION_TIMEOUT", "20")),
        )

    async def _forget(self, dataset_id: str) -> None:
        await asyncio.wait_for(
            self._forget_inner(dataset_id),
            timeout=float(os.getenv("COGNEE_CLOUD_OPERATION_TIMEOUT", "20")),
        )

    async def _remember_inner(self, dataset_id: str, content: str) -> None:
        await self._ensure_served()
        try:
            await _maybe_await(
                self.client.remember(
                    content,
                    dataset_name=dataset_id,
                    self_improvement=False,
                )
            )
        except TypeError:
            await _maybe_await(self.client.remember(content, dataset_name=dataset_id))

    async def _recall_inner(self, query: str) -> list[Any]:
        await self._ensure_served()
        if hasattr(self.client, "recall"):
            try:
                return await _maybe_await(self.client.recall(query_text=query))
            except TypeError:
                return await _maybe_await(self.client.recall(query))
        if hasattr(self.client, "search"):
            return await _maybe_await(self.client.search(query))
        raise RuntimeError("Cognee Cloud client does not expose recall or search")

    async def _improve_inner(self, dataset_id: str) -> None:
        await self._ensure_served()
        if hasattr(self.client, "improve"):
            try:
                await _maybe_await(self.client.improve(dataset=dataset_id))
            except TypeError:
                await _maybe_await(self.client.improve(dataset_name=dataset_id))
            return
        if hasattr(self.client, "memify"):
            await _maybe_await(self.client.memify(dataset=dataset_id))
            return
        raise RuntimeError("Cognee Cloud client does not expose improve or memify")

    async def _forget_inner(self, dataset_id: str) -> None:
        await self._ensure_served()
        await _maybe_await(self.client.forget(dataset_id, memory_only=False))

    async def _ensure_served(self) -> None:
        if self._served or not hasattr(self.client, "serve"):
            return
        await asyncio.wait_for(
            _maybe_await(
                self.client.serve(
                    url=os.getenv("COGNEE_CLOUD_BASE_URL", "https://api.cognee.ai"),
                    api_key=os.getenv("COGNEE_CLOUD_API_KEY"),
                )
            ),
            timeout=float(os.getenv("COGNEE_CLOUD_CONNECT_TIMEOUT", "20")),
        )
        self._served = True

    def _fallback_remember(
        self,
        dataset_id: str,
        content: str,
        metadata: dict | None,
        reason: str,
    ) -> MemoryRecord:
        return self.fallback.remember(
            dataset_id=dataset_id,
            content=content,
            metadata={**(metadata or {}), "fallback_reason": reason},
        )


class MemoryRouter:
    """Routes sensitive patient memory locally and shared protocol memory to cloud scope."""

    def __init__(
        self,
        local_store: LocalCogneeMemoryStore | JsonFallbackMemoryStore | None = None,
        cloud_store: CogneeCloudMemoryStore | JsonFallbackMemoryStore | None = None,
    ) -> None:
        self.local_store = local_store or self._build_local_store()
        self.cloud_store = cloud_store or self._build_cloud_store()
        self.cloud_configured = bool(
            getattr(self.cloud_store, "configured", False) or os.getenv("COGNEE_CLOUD_API_KEY")
        )

    def remember_patient_event(self, patient_id: str, content: str, metadata: dict | None = None) -> MemoryRecord:
        return self.local_store.remember(
            dataset_id=patient_id,
            content=content,
            metadata={"privacy": "patient_local_only", **(metadata or {})},
        )

    def remember_protocol(self, protocol_id: str, content: str, metadata: dict | None = None) -> MemoryRecord:
        return self.cloud_store.remember(
            dataset_id=protocol_id,
            content=content,
            metadata={"privacy": "non_sensitive_shared", **(metadata or {})},
        )

    def hybrid_recall(self, patient_query: str, protocol_query: str) -> dict[str, list[MemoryRecord]]:
        return {
            "local_patient": self.local_store.recall(patient_query),
            "cloud_protocol": self.cloud_store.recall(protocol_query),
        }

    def improve_patient_memory(self, patient_id: str) -> MemoryRecord:
        return self.local_store.improve(patient_id)

    def improve_protocol_memory(self, protocol_id: str) -> MemoryRecord:
        return self.cloud_store.improve(protocol_id)

    def forget_patient(self, patient_id: str) -> int:
        return self.local_store.forget(patient_id)

    def forget_protocol(self, protocol_id: str) -> int:
        return self.cloud_store.forget(protocol_id)

    def status(self) -> MemoryStatus:
        local_backend = getattr(self.local_store, "backend_name", "json_fallback")
        cloud_backend = getattr(self.cloud_store, "backend_name", "json_fallback")
        using_fallback = local_backend == "json_fallback" or cloud_backend == "json_fallback"
        return MemoryStatus(
            cloud_configured=self.cloud_configured,
            local_backend=local_backend,
            cloud_backend=cloud_backend,
            local_records=self.local_store.record_count,
            cloud_records=self.cloud_store.record_count,
            note=(
                "Patient-identifying synthetic events route to local open-source Cognee scope; "
                "non-sensitive protocols route to Cognee Cloud scope. "
                + (
                    "JSON fallback is active for unavailable adapters."
                    if using_fallback
                    else "Real Cognee adapters are active."
                )
            ),
        )

    def _build_local_store(self) -> LocalCogneeMemoryStore | JsonFallbackMemoryStore:
        enabled = os.getenv("COGNEE_ENABLE_SDK", "false").lower() == "true"
        if not enabled:
            return JsonFallbackMemoryStore("local_patient")
        return LocalCogneeMemoryStore(
            enabled=True,
            module_loader=lambda: importlib.import_module("cognee"),
        )

    def _build_cloud_store(self) -> CogneeCloudMemoryStore | JsonFallbackMemoryStore:
        configured = bool(os.getenv("COGNEE_CLOUD_API_KEY"))
        enabled = os.getenv("COGNEE_ENABLE_CLOUD", "false").lower() == "true"
        if not enabled or not configured:
            return JsonFallbackMemoryStore("cloud_protocol")
        return CogneeCloudMemoryStore(
            enabled=True,
            configured=True,
            client_loader=lambda: importlib.import_module("cognee"),
        )
