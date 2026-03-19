from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DEFAULT_GAME_VERSION = "1.0.0"
DEFAULT_LOADER_VERSION = "1.0.0"
REQUIRED_STRING_FIELDS = ("name", "id", "version", "author", "entrypoint")


class ManifestError(ValueError):
    """Erro de validação de manifesto."""


@dataclass(slots=True)
class ModManifest:
    name: str
    id: str
    version: str
    author: str
    entrypoint: str
    priority: int = 0
    requires: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    game_version: str = DEFAULT_GAME_VERSION
    loader_version: str = DEFAULT_LOADER_VERSION
    enabled: bool = True


@dataclass(slots=True)
class ModCandidate:
    manifest: ModManifest
    module: Any
    source_path: str
    is_package: bool



def build_manifest(mod_name: str, module: Any, is_package: bool) -> ModManifest:
    raw_manifest = getattr(module, "MOD_INFO", None)
    if raw_manifest is None:
        raw_manifest = {}
    if not isinstance(raw_manifest, dict):
        raise ManifestError("MOD_INFO precisa ser um dicionário")

    manifest_data = dict(raw_manifest)
    manifest_data.setdefault("name", mod_name)
    manifest_data.setdefault("id", mod_name)
    manifest_data.setdefault("version", "1.0.0")
    manifest_data.setdefault("author", "Desconhecido")
    manifest_data.setdefault("entrypoint", "apply")

    if "priority" not in manifest_data:
        manifest_data["priority"] = manifest_data.pop("PRIORITY", getattr(module, "PRIORITY", 0))
    else:
        manifest_data.pop("PRIORITY", None)

    manifest_data.setdefault("requires", [])
    manifest_data.setdefault("conflicts", [])
    manifest_data.setdefault("game_version", DEFAULT_GAME_VERSION)
    manifest_data.setdefault("loader_version", DEFAULT_LOADER_VERSION)
    manifest_data.setdefault("enabled", True)

    for field_name in REQUIRED_STRING_FIELDS:
        value = manifest_data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ManifestError(f"Campo obrigatório inválido: {field_name}")
        manifest_data[field_name] = value.strip()

    priority = manifest_data.get("priority")
    if not isinstance(priority, int):
        raise ManifestError("Campo obrigatório inválido: priority")

    requires = _normalize_string_list(manifest_data.get("requires"), "requires")
    conflicts = _normalize_string_list(manifest_data.get("conflicts"), "conflicts")

    game_version = manifest_data.get("game_version")
    if not isinstance(game_version, str) or not game_version.strip():
        raise ManifestError("Campo obrigatório inválido: game_version")

    loader_version = manifest_data.get("loader_version")
    if not isinstance(loader_version, str) or not loader_version.strip():
        raise ManifestError("Campo obrigatório inválido: loader_version")

    enabled = manifest_data.get("enabled")
    if not isinstance(enabled, bool):
        raise ManifestError("Campo obrigatório inválido: enabled")

    entrypoint = manifest_data["entrypoint"]
    if not hasattr(module, entrypoint) or not callable(getattr(module, entrypoint)):
        raise ManifestError(f"Entrypoint inválido ou ausente: {entrypoint}")

    return ModManifest(
        name=manifest_data["name"],
        id=manifest_data["id"],
        version=manifest_data["version"],
        author=manifest_data["author"],
        entrypoint=entrypoint,
        priority=priority,
        requires=requires,
        conflicts=conflicts,
        game_version=game_version.strip(),
        loader_version=loader_version.strip(),
        enabled=enabled,
    )



def is_version_compatible(version_spec: str, current_version: str) -> bool:
    spec = version_spec.strip()
    if spec in {"*", "any"}:
        return True

    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith(">="):
            if _compare_versions(current_version, part[2:].strip()) < 0:
                return False
        elif part.startswith("<="):
            if _compare_versions(current_version, part[2:].strip()) > 0:
                return False
        elif part.startswith(">"):
            if _compare_versions(current_version, part[1:].strip()) <= 0:
                return False
        elif part.startswith("<"):
            if _compare_versions(current_version, part[1:].strip()) >= 0:
                return False
        elif part.startswith("=="):
            if _compare_versions(current_version, part[2:].strip()) != 0:
                return False
        else:
            if _compare_versions(current_version, part) != 0:
                return False
    return True



def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ManifestError(f"Campo obrigatório inválido: {field_name}")

    normalized = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ManifestError(f"Campo obrigatório inválido: {field_name}")
        normalized.append(item.strip())
    return normalized



def _compare_versions(left: str, right: str) -> int:
    left_parts = _parse_version(left)
    right_parts = _parse_version(right)
    size = max(len(left_parts), len(right_parts))
    left_parts.extend([0] * (size - len(left_parts)))
    right_parts.extend([0] * (size - len(right_parts)))

    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0



def _parse_version(version: str) -> list[int]:
    cleaned = version.strip()
    if not cleaned:
        raise ManifestError("Versão vazia não é suportada")

    parts = []
    for token in cleaned.split("."):
        if not token.isdigit():
            raise ManifestError(f"Versão inválida: {version}")
        parts.append(int(token))
    return parts
