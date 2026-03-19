from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any
import importlib
import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from mods.manifest import DEFAULT_GAME_VERSION, DEFAULT_LOADER_VERSION, ModCandidate, build_manifest, is_version_compatible

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
LOADED_MODS = {}
FAILED_MODS = {}
PATCH_REGISTRY = {}
PATCH_REPORT = {}
_ORIGINAL_TARGETS = {}

LOADED_MODS: dict[str, dict[str, Any]] = {}
FAILED_MODS: dict[str, list[dict[str, Any]]] = {}
PATCH_REGISTRY: dict[str, list[dict[str, Any]]] = {}
PATCH_REPORT: dict[str, dict[str, list[dict[str, Any]]]] = {}
HOOKS: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
_ORIGINAL_TARGETS: dict[str, Callable[..., Any]] = {}

PATCH_TYPES = {'before', 'after', 'replace'}
CONFLICT_POLICIES = {'exclusive', 'chain', 'ignore'}


def reset_registry():
    for target, original in _ORIGINAL_TARGETS.items():
        owner, attribute_name = _resolve_owner_and_attribute(target)
        setattr(owner, attribute_name, original)
    LOADED_MODS.clear()
    FAILED_MODS.clear()
    PATCH_REGISTRY.clear()
    PATCH_REPORT.clear()
    HOOKS.clear()
    _ORIGINAL_TARGETS.clear()
    HOOKS.clear()


def register_hook(event_name: str, callback: Callable[[dict[str, Any]], None]):
    HOOKS.setdefault(event_name, []).append(callback)


def trigger_hooks(event_name: str, payload: dict[str, Any] | None = None):
    for hook in HOOKS.get(event_name, []):
        hook(payload or {})


def _resolve_owner_and_attribute(target: str):
    path_parts = target.split('.')
    if len(path_parts) < 2:
        raise ValueError(f'Alvo inválido: {target}')

    for index in range(len(path_parts) - 1, 0, -1):
        module_name = '.'.join(path_parts[:index])
        try:
            owner = __import__(module_name, fromlist=['*'])
            remaining = parts[index:]
            break
        except ModuleNotFoundError:
            continue
    else:
        raise ValueError(f'Não foi possível importar o alvo: {target}')

    for part in remaining[:-1]:
        if not hasattr(owner, part):
            raise ValueError(f'Atributo intermediário não encontrado em {target}: {part}')
        owner = getattr(owner, part)

    attribute_name = remaining[-1]
    if not hasattr(owner, attribute_name):
        raise ValueError(f'Atributo final não encontrado em {target}: {attribute_name}')
    return owner, attribute_name


def _resolve_target(target: str) -> Callable[..., Any]:
    owner, attribute_name = _resolve_owner_and_attribute(target)
    resolved = getattr(owner, attribute_name)
    if not callable(resolved):
        raise ValueError(f'Alvo não é chamável: {target}')
    return resolved


def _register_failure(mod_id: str, target: str, reason: str, **extra):
    FAILED_MODS.setdefault(mod_id, []).append({'target': target, 'reason': reason, **extra})


def register_patch(mod_id: str, patch_type: str, target: str, priority: int, conflict_policy: str, patch_fn: Callable[..., Any]):
    if patch_type not in PATCH_TYPES:
        raise ValueError(f'Tipo de patch inválido: {patch_type}')
    if conflict_policy not in CONFLICT_POLICIES:
        raise ValueError(f'Política de conflito inválida: {conflict_policy}')
    if not isinstance(priority, int):
        raise ValueError('priority deve ser int')
    if not callable(patch_fn):
        raise ValueError('patch_fn deve ser chamável')

    _resolve_target(target)
    patch_entry = {
        'mod_id': mod_id,
        'type': patch_type,
        'target': target,
        'priority': priority,
        'conflict_policy': conflict_policy,
        'fn': patch_fn,
        'active': True,
    }
    PATCH_REGISTRY.setdefault(target, []).append(patch_entry)
    PATCH_REGISTRY[target].sort(key=lambda item: (item['priority'], item['mod_id'], item['type']))
    return patch_entry


def _build_replace_chain(target: str, replace_patches, original_fn):
    if not replace_patches:
        return original_fn

    chainable = [patch for patch in replace_patches if patch['conflict_policy'] == 'chain']
    non_chainable = [patch for patch in replace_patches if patch['conflict_policy'] != 'chain']

    if len(non_chainable) > 1:
        active_patch = non_chainable[0]
        for rejected in non_chainable[1:]:
            rejected['active'] = False
            _register_failure(rejected['mod_id'], target, f"replace conflitante com mod {active_patch['mod_id']}")
        replace_patches = [active_patch, *chainable]
    elif non_chainable:
        replace_patches = [non_chainable[0], *chainable]
    else:
        replace_patches = chainable

    replace_patches.sort(key=lambda item: (item['priority'], item['mod_id']))

    next_fn = original_fn
    for patch in reversed(replace_patches):
        patch_fn = patch['fn']
        current_next = next_fn

        def chained(*args, _patch_fn=patch_fn, _next=current_next, **kwargs):
            return _patch_fn(*args, next_fn=_next, **kwargs)

        next_fn = chained
    return next_fn


def _compose_target(target: str):
    original_fn = _ORIGINAL_TARGETS.get(target)
    if original_fn is None:
        original_fn = _resolve_target(target)
        _ORIGINAL_TARGETS[target] = original_fn

    patches = PATCH_REGISTRY.get(target, [])
    before_patches = [patch for patch in patches if patch['type'] == 'before' and patch['active']]
    after_patches = [patch for patch in patches if patch['type'] == 'after' and patch['active']]
    replace_patches = [patch for patch in patches if patch['type'] == 'replace' and patch['active']]

    before_patches.sort(key=lambda item: (item['priority'], item['mod_id']))
    after_patches.sort(key=lambda item: (item['priority'], item['mod_id']), reverse=True)
    core_fn = _build_replace_chain(target, replace_patches, original_fn)

    def composed(*args, **kwargs):
        for patch in before_patches:
            patch['fn'](*args, **kwargs)
        result = core_fn(*args, **kwargs)
        for patch in after_patches:
            updated = patch['fn'](result, *args, **kwargs)
            if updated is not None:
                result = updated
        return result

    owner, attribute_name = _resolve_owner_and_attribute(target)
    setattr(owner, attribute_name, composed)
    PATCH_REPORT[target] = {
        'before': [patch for patch in before_patches if patch['active']],
        'replace': [patch for patch in replace_patches if patch['active']],
        'after': [patch for patch in after_patches if patch['active']],
    }


def apply_registered_patches():
    for target in list(PATCH_REGISTRY):
        _compose_target(target)


def get_patch_report():
    report = {}
    for target, sections in PATCH_REPORT.items():
        report[target] = {}
        for patch_type, patches in sections.items():
            report[target][patch_type] = [
                {
                    'mod_id': patch['mod_id'],
                    'priority': patch['priority'],
                    'conflict_policy': patch['conflict_policy'],
                }
                for patch in patches
            ]
    return report


def _load_module_from_path(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    raise ValueError(f'Não foi possível criar spec para {mod_name}')


def _build_candidate(mod_name: str, module: ModuleType, path: Path, is_package: bool) -> ModCandidate | None:
    try:
        manifest = build_manifest(mod_name, module, is_package=is_package)
    except Exception as error:
        _register_failure(mod_name, str(path), f'Falha de validação do manifesto: {error}', path=str(path))
        return None

    if not manifest.enabled:
        _register_failure(manifest.id, str(path), 'Mod desabilitado no manifesto', path=str(path))
        return None

def trigger_hooks(event_name: str, payload: dict[str, Any] | None = None):
    event_payload = payload or {}
    for hook in HOOKS.get(event_name, []):
        hook(event_payload)

def load_mods(game_context: dict[str, Any] | None = None):
    candidates: list[ModCandidate] = []
    reset_registry()

def load_mods(game_context: dict[str, Any]):
    """
    Carrega, valida e aplica mods encontrados na pasta MODS_FOLDER.
    - Procura por pacotes (diretórios com __init__.py) e arquivos .py individuais.
    - Aceita manifesto explícito via MOD_INFO para pacotes e arquivos simples.
    - Valida manifesto, dependências, conflitos e compatibilidade de versão.
    - Ordena mods por dependências e prioridade antes de aplicar.
    - Armazena mods aplicados em LOADED_MODS e falhas em FAILED_MODS.
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
    mods_to_apply = []
    mod_context = build_mod_context(game_context)
    LOADED_MODS.clear()
    FAILED_MODS.clear()


def _collect_candidates() -> list[ModCandidate]:
    candidates: list[ModCandidate] = []
    for item in sorted(MODS_FOLDER.iterdir(), key=lambda current: current.name):
        if item.name in {'__pycache__', '__init__.py', 'loader.py', 'manifest.py'}:
            continue

        if item.is_dir() and (item / '__init__.py').exists():
            mod_name = item.name
            try:
                module = _load_module_from_path(mod_name, item / '__init__.py')
            except Exception as error:
                _register_failure(mod_name, str(item), str(error), path=str(item))
                continue
            candidate = _build_candidate(mod_name, module, item, True)
            if candidate is not None:
                candidates.append(candidate)
        elif item.is_file() and item.suffix == '.py':
            mod_name = item.stem
            try:
                module = _load_module_from_path(mod_name, item)
            except Exception as error:
                _register_failure(mod_name, str(item), str(error), path=str(item))
                continue
            candidate = _build_candidate(mod_name, module, item, False)
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _validate_candidates(candidates: list[ModCandidate]) -> list[ModCandidate]:
    id_map = defaultdict(list)
    for candidate in candidates:
        id_map[candidate.manifest.id].append(candidate)

    valid_candidates: list[ModCandidate] = []
    for mod_id, grouped in id_map.items():
        if len(grouped) > 1:
            for candidate in grouped:
                _register_failure(mod_id, candidate.source_path, 'ID duplicado entre mods carregáveis', path=candidate.source_path)
            continue
        valid_candidates.append(grouped[0])

    candidate_by_id = {candidate.manifest.id: candidate for candidate in valid_candidates}

    for candidate in list(candidate_by_id.values()):
        missing = [dependency_id for dependency_id in candidate.manifest.requires if dependency_id not in candidate_by_id]
        if missing:
            _register_failure(candidate.manifest.id, candidate.source_path, f"Dependências ausentes: {', '.join(missing)}", path=candidate.source_path)
            candidate_by_id.pop(candidate.manifest.id, None)

    conflicting_ids: set[str] = set()
    for candidate in list(candidate_by_id.values()):
        active_conflicts = [conflict_id for conflict_id in candidate.manifest.conflicts if conflict_id in candidate_by_id]
        if active_conflicts:
            conflicting_ids.add(candidate.manifest.id)
            _register_failure(candidate.manifest.id, candidate.source_path, f"Conflitos declarados com mods ativos: {', '.join(active_conflicts)}", path=candidate.source_path)
            for conflict_id in active_conflicts:
                conflicting_ids.add(conflict_id)
                conflict_candidate = candidate_by_id.get(conflict_id)
                if conflict_candidate is not None:
                    _register_failure(conflict_candidate.manifest.id, conflict_candidate.source_path, f"Conflito com mod ativo: {candidate.manifest.id}", path=conflict_candidate.source_path)

    for mod_id in conflicting_ids:
        candidate_by_id.pop(mod_id, None)

    for candidate in list(candidate_by_id.values()):
        manifest = candidate.manifest
        if not is_version_compatible(manifest.game_version, GAME_VERSION):
            _register_failure(manifest.id, candidate.source_path, f'Versão do jogo incompatível: requer {manifest.game_version}, atual {GAME_VERSION}', path=candidate.source_path)
            candidate_by_id.pop(manifest.id, None)
            continue
        if not is_version_compatible(manifest.loader_version, LOADER_VERSION):
            _register_failure(manifest.id, candidate.source_path, f'Versão do loader incompatível: requer {manifest.loader_version}, atual {LOADER_VERSION}', path=candidate.source_path)
            candidate_by_id.pop(manifest.id, None)

    return list(candidate_by_id.values())


def _sort_candidates(candidates: list[ModCandidate]) -> list[ModCandidate]:
    ordered: list[ModCandidate] = []
    remaining = {candidate.manifest.id: candidate for candidate in candidates}

    while remaining:
        ready = [
            candidate for candidate in remaining.values()
            if all(dependency in {current.manifest.id for current in ordered} for dependency in candidate.manifest.requires)
        ]
        if not ready:
            for candidate in remaining.values():
                _register_failure(candidate.manifest.id, candidate.source_path, 'Ciclo de dependências detectado', path=candidate.source_path)
            break

        ready.sort(key=lambda candidate: (candidate.manifest.priority, candidate.manifest.name.lower()))
        current = ready[0]
        ordered.append(current)
        remaining.pop(current.manifest.id, None)

    return ordered


def _apply_mod(module: ModuleType):
    from libs.battle import MOD_CONTEXT

    apply_fn = getattr(module, 'apply')
    try:
        apply_fn(MOD_CONTEXT)
    except TypeError:
        apply_fn()


def load_mods(game_context: dict[str, Any] | None = None):
    del game_context
    reset_registry()

    candidates = _collect_candidates()
    valid_candidates = _validate_candidates(candidates)
    ordered_candidates = _sort_candidates(valid_candidates)

    for candidate in ordered_candidates:
        manifest = candidate.manifest
        try:
            _apply_mod(candidate.module)
            LOADED_MODS[manifest.id] = {
                'name': manifest.name,
                'version': manifest.version,
                'author': manifest.author,
                'priority': manifest.priority,
                'module': candidate.module,
                'manifest': manifest,
            }
        except Exception as error:
            _register_failure(manifest.id, candidate.source_path, f'Erro ao aplicar mod: {error}', path=candidate.source_path)

    apply_registered_patches()
    return LOADED_MODS
