from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

# Define a pasta onde os mods estão localizados (mesmo diretório deste arquivo)
MODS_FOLDER = Path(__file__).parent
# Dicionário para armazenar mods carregados com sucesso
LOADED_MODS: dict[str, ModuleType] = {}


@dataclass(slots=True)
class ModCandidate:
    name: str
    path: Path
    is_package: bool


@dataclass(slots=True)
class ValidatedMod:
    candidate: ModCandidate
    module: ModuleType
    priority: int
    version: str

    @property
    def name(self) -> str:
        return self.candidate.name


@dataclass(slots=True)
class RejectedMod:
    candidate: ModCandidate
    reason: str


@dataclass(slots=True)
class AppliedModResult:
    mod: ValidatedMod
    success: bool
    failure_reason: str | None = None

    @property
    def name(self) -> str:
        return self.mod.name

    @property
    def version(self) -> str:
        return self.mod.version

    @property
    def priority(self) -> int:
        return self.mod.priority


@dataclass(slots=True)
class ModLoadReport:
    discovered_mods: list[ModCandidate] = field(default_factory=list)
    valid_mods: list[ValidatedMod] = field(default_factory=list)
    loaded_mods: list[AppliedModResult] = field(default_factory=list)
    rejected_mods: list[RejectedMod] = field(default_factory=list)
    failed_mods: list[AppliedModResult] = field(default_factory=list)


LOAD_REPORT = ModLoadReport()


def discover_mods(mods_folder: Path) -> list[ModCandidate]:
    candidates: list[ModCandidate] = []

    for item in sorted(mods_folder.iterdir(), key=lambda current: current.name):
        # Varre todos os itens na pasta de mods
        if item.is_dir() and (item / "__init__.py").exists():
            candidates.append(ModCandidate(name=item.name, path=item / "__init__.py", is_package=True))
        elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
            candidates.append(ModCandidate(name=item.stem, path=item, is_package=False))

    return candidates


def import_mod(candidate: ModCandidate) -> ModuleType:
    spec = importlib.util.spec_from_file_location(candidate.name, candidate.path)
    if not spec or not spec.loader:
        raise ImportError(f"Não foi possível criar a especificação do mod em {candidate.path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_mod(module: ModuleType, candidate: ModCandidate) -> ValidatedMod:
    if not hasattr(module, "apply"):
        raise ValueError("mod sem função 'apply'")

    priority = 0
    version = "desconhecida"

    if candidate.is_package:
        if not hasattr(module, "MOD_INFO") or not isinstance(module.MOD_INFO, dict):
            raise ValueError("pacote sem dicionário 'MOD_INFO'")
        priority = int(module.MOD_INFO.get("PRIORITY", 0))
        version = str(module.MOD_INFO.get("VERSION", module.MOD_INFO.get("version", version)))
    else:
        priority = int(getattr(module, "PRIORITY", 0))
        version = str(getattr(module, "VERSION", getattr(module, "version", version)))

    return ValidatedMod(candidate=candidate, module=module, priority=priority, version=version)


def resolve_load_order(mods: list[ValidatedMod]) -> list[ValidatedMod]:
    return sorted(mods, key=lambda mod: (mod.priority, mod.name))


def apply_mod(mod: ValidatedMod, ctx: Any = None) -> AppliedModResult:
    try:
        if ctx is None:
            mod.module.apply()
        else:
            try:
                mod.module.apply(ctx)
            except TypeError:
                mod.module.apply()
        return AppliedModResult(mod=mod, success=True)
    except Exception as exc:
        return AppliedModResult(mod=mod, success=False, failure_reason=str(exc))


def build_report() -> ModLoadReport:
    return ModLoadReport()


def load_mods(mods_folder: Path | None = None, ctx: Any = None) -> ModLoadReport:
    """
    Carrega e aplica mods encontrados na pasta MODS_FOLDER.
    - Procura por pacotes (diretórios com __init__.py) e arquivos .py individuais.
    - Para pacotes: exige 'MOD_INFO' (dict) e função 'apply'.
    - Para arquivos: exige função 'apply'; 'PRIORITY' é opcional.
    - Ordena mods por prioridade e aplica na ordem.
    - Armazena mods aplicados em LOADED_MODS.
    """
    global LOAD_REPORT

    LOADED_MODS.clear()
    LOAD_REPORT = build_report()
    target_folder = mods_folder or MODS_FOLDER

    discovered_mods = discover_mods(target_folder)
    LOAD_REPORT.discovered_mods.extend(discovered_mods)

    for candidate in discovered_mods:
        try:
            module = import_mod(candidate)
            validated_mod = validate_mod(module, candidate)
            LOAD_REPORT.valid_mods.append(validated_mod)
        except Exception as exc:
            LOAD_REPORT.rejected_mods.append(RejectedMod(candidate=candidate, reason=str(exc)))

    for mod in resolve_load_order(LOAD_REPORT.valid_mods):
        result = apply_mod(mod, ctx)
        if result.success:
            LOADED_MODS[mod.name] = mod.module
            LOAD_REPORT.loaded_mods.append(result)
            print(f"Mod carregado: {mod.name} - prioridade {mod.priority}")
        else:
            LOAD_REPORT.failed_mods.append(result)
            print(f"Erro ao aplicar mod {mod.name}: {result.failure_reason}")

    return LOAD_REPORT
