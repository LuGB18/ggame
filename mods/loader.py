import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable

from mods.manifest import (
    DEFAULT_GAME_VERSION,
    DEFAULT_LOADER_VERSION,
    ModCandidate,
    build_manifest,
    is_version_compatible,
)

MODS_FOLDER = Path(__file__).parent
GAME_VERSION = DEFAULT_GAME_VERSION
LOADER_VERSION = DEFAULT_LOADER_VERSION
LOADED_MODS: dict[str, dict[str, Any]] = {}
FAILED_MODS: dict[str, list[dict[str, str]]] = {}
PATCH_REGISTRY: dict[str, list[dict[str, Any]]] = {}
PATCH_REPORT: dict[str, dict[str, list[dict[str, Any]]]] = {}
_ORIGINAL_TARGETS: dict[str, Callable[..., Any]] = {}
HOOKS: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

PATCH_TYPES = {"before", "after", "replace"}
CONFLICT_POLICIES = {"exclusive", "chain", "ignore"}


def reset_registry():
    for target, original in _ORIGINAL_TARGETS.items():
        owner, attribute_name = _resolve_owner_and_attribute(target)
        setattr(owner, attribute_name, original)
    LOADED_MODS.clear()
    FAILED_MODS.clear()
    PATCH_REGISTRY.clear()
    PATCH_REPORT.clear()
    _ORIGINAL_TARGETS.clear()
    HOOKS.clear()


def _resolve_owner_and_attribute(target: str):
    parts = target.split('.')
    if len(parts) < 2:
        raise ValueError(f'Alvo inválido: {target}')

    for index in range(len(parts) - 1, 0, -1):
        module_name = '.'.join(parts[:index])
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


def _register_failure(mod_id: str, target: str, reason: str):
    FAILED_MODS.setdefault(mod_id, []).append({'target': target, 'reason': reason})


def register_hook(event_name: str, callback: Callable[[dict[str, Any]], None]):
    HOOKS.setdefault(event_name, []).append(callback)


def trigger_hooks(event_name: str, payload: dict[str, Any] | None = None):
    event_payload = payload or {}
    for hook in HOOKS.get(event_name, []):
        hook(event_payload)


def register_patch(mod_id: str, patch_type: str, target: str, priority: int, conflict_policy: str, patch_fn: Callable[..., Any]):
    if not mod_id:
        raise ValueError('mod_id é obrigatório')
    if patch_type not in PATCH_TYPES:
        raise ValueError(f'Tipo de patch inválido: {patch_type}')
    if not target:
        raise ValueError('target é obrigatório')
    if not isinstance(priority, int):
        raise ValueError('priority deve ser int')
    if conflict_policy not in CONFLICT_POLICIES:
        raise ValueError(f'Política de conflito inválida: {conflict_policy}')
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


def _build_candidate(mod_name: str, module: Any, source_path: Path, is_package: bool) -> ModCandidate | None:
    try:
        manifest = build_manifest(mod_name, module, is_package)
    except Exception as error:
        _register_failure(mod_name, str(source_path), str(error))
        return None
    return ModCandidate(
        manifest=manifest,
        module=module,
        source_path=str(source_path),
        is_package=is_package,
    )


def _validate_candidates(candidates: list[ModCandidate]) -> list[ModCandidate]:
    grouped_by_id: dict[str, list[ModCandidate]] = {}
    for candidate in candidates:
        grouped_by_id.setdefault(candidate.manifest.id, []).append(candidate)

    valid_candidates: list[ModCandidate] = []
    for mod_id, grouped_candidates in grouped_by_id.items():
        if len(grouped_candidates) > 1:
            for candidate in grouped_candidates:
                _register_failure(mod_id, candidate.source_path, 'ID de mod duplicado')
            continue
        valid_candidates.extend(grouped_candidates)

    id_map = {candidate.manifest.id: candidate for candidate in valid_candidates}
    accepted: list[ModCandidate] = []

    for candidate in valid_candidates:
        manifest = candidate.manifest
        if not manifest.enabled:
            _register_failure(manifest.id, candidate.source_path, 'Mod desabilitado')
            continue
        if not is_version_compatible(manifest.game_version, GAME_VERSION):
            _register_failure(manifest.id, candidate.source_path, 'Versão do jogo incompatível')
            continue
        if not is_version_compatible(manifest.loader_version, LOADER_VERSION):
            _register_failure(manifest.id, candidate.source_path, 'Versão do loader incompatível')
            continue
        missing_requirements = [required for required in manifest.requires if required not in id_map]
        if missing_requirements:
            _register_failure(manifest.id, candidate.source_path, f"Dependências ausentes: {', '.join(missing_requirements)}")
            continue
        conflicting = [
            other_id
            for other_id, other_candidate in id_map.items()
            if other_id != manifest.id and (
                other_id in manifest.conflicts or manifest.id in other_candidate.manifest.conflicts
            )
        ]
        if conflicting:
            _register_failure(manifest.id, candidate.source_path, f"Conflitos detectados: {', '.join(conflicting)}")
            continue
        accepted.append(candidate)

    accepted_ids = {candidate.manifest.id for candidate in accepted}
    filtered: list[ModCandidate] = []
    for candidate in accepted:
        invalid_requirements = [required for required in candidate.manifest.requires if required not in accepted_ids]
        if invalid_requirements:
            _register_failure(candidate.manifest.id, candidate.source_path, f"Dependências rejeitadas: {', '.join(invalid_requirements)}")
            continue
        if any(
            other.manifest.id != candidate.manifest.id
            and (
                other.manifest.id in candidate.manifest.conflicts
                or candidate.manifest.id in other.manifest.conflicts
            )
            for other in accepted
        ):
            _register_failure(candidate.manifest.id, candidate.source_path, 'Conflitos detectados com mods aceitos')
            continue
        filtered.append(candidate)
    return filtered


def _sort_candidates_by_dependency(candidates: list[ModCandidate]) -> list[ModCandidate]:
    sorted_candidates: list[ModCandidate] = []
    remaining = {candidate.manifest.id: candidate for candidate in candidates}

    while remaining:
        ready = [
            candidate
            for candidate in remaining.values()
            if all(required not in remaining for required in candidate.manifest.requires)
        ]
        if not ready:
            for candidate in remaining.values():
                _register_failure(candidate.manifest.id, candidate.source_path, 'Dependências cíclicas ou inválidas')
            break
        ready.sort(key=lambda item: (item.manifest.priority, item.manifest.id))
        for candidate in ready:
            sorted_candidates.append(candidate)
            remaining.pop(candidate.manifest.id, None)
    return sorted_candidates


def _apply_mod(module: Any, mod_context: Any = None):
    apply_signature = inspect.signature(module.apply)
    if len(apply_signature.parameters) == 0:
        module.apply()
        return
    module.apply(mod_context)


def load_mods(game_context: dict[str, Any] | None = None):
    candidates: list[ModCandidate] = []
    reset_registry()

    for item in sorted(MODS_FOLDER.iterdir(), key=lambda current: current.name):
        if item.name in {'__pycache__', '__init__.py', 'loader.py', 'manifest.py'}:
            continue
        if item.is_dir() and (item / '__init__.py').exists():
            module = _load_module_from_path(item.name, item / '__init__.py')
            candidate = _build_candidate(item.name, module, item, is_package=True)
            if candidate:
                candidates.append(candidate)
        elif item.is_file() and item.suffix == '.py':
            module = _load_module_from_path(item.stem, item)
            candidate = _build_candidate(item.stem, module, item, is_package=False)
            if candidate:
                candidates.append(candidate)

    valid_candidates = _sort_candidates_by_dependency(_validate_candidates(candidates))

    for candidate in valid_candidates:
        try:
            _apply_mod(candidate.module, game_context)
            LOADED_MODS[candidate.manifest.id] = {
                'module': candidate.module,
                'priority': candidate.manifest.priority,
                'manifest': candidate.manifest,
            }
        except Exception as error:
            _register_failure(candidate.manifest.id, candidate.source_path, str(error))

    apply_registered_patches()
    return LOADED_MODS


def unpatch_all(mod_name: str) -> int:
    restored = 0
    for target, patches in PATCH_REGISTRY.items():
        if any(patch['mod_id'] == mod_name for patch in patches):
            original = _ORIGINAL_TARGETS.get(target)
            if original is not None:
                owner, attribute_name = _resolve_owner_and_attribute(target)
                setattr(owner, attribute_name, original)
                restored += 1
    return restored
