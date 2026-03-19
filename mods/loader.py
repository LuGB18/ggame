import importlib.util
from collections import defaultdict
from pathlib import Path

from mods.manifest import (
    DEFAULT_GAME_VERSION,
    DEFAULT_LOADER_VERSION,
    ModCandidate,
    build_manifest,
    is_version_compatible,
)

# Define a pasta onde os mods estão localizados (mesmo diretório deste arquivo)
MODS_FOLDER = Path(__file__).parent
# Dicionário para armazenar mods carregados com sucesso
LOADED_MODS = {}
FAILED_MODS = {}
GAME_VERSION = DEFAULT_GAME_VERSION
LOADER_VERSION = DEFAULT_LOADER_VERSION


def load_mods():
    """
    Carrega, valida e aplica mods encontrados na pasta MODS_FOLDER.
    - Procura por pacotes (diretórios com __init__.py) e arquivos .py individuais.
    - Aceita manifesto explícito via MOD_INFO para pacotes e arquivos simples.
    - Valida manifesto, dependências, conflitos e compatibilidade de versão.
    - Ordena mods por dependências e prioridade antes de aplicar.
    - Armazena mods aplicados em LOADED_MODS e falhas em FAILED_MODS.
    """
    LOADED_MODS.clear()
    FAILED_MODS.clear()

    candidates = []
    seen_paths = set()

    # Varre todos os itens na pasta de mods
    for item in sorted(MODS_FOLDER.iterdir(), key=lambda current: current.name):
        if item.name in {"__pycache__", "manifest.py"}:
            continue

        # Se for um diretório de pacote Python com __init__.py
        if item.is_dir() and (item / "__init__.py").exists():
            mod_name = item.name
            seen_paths.add(item.resolve())
            module = _load_module(mod_name, item / "__init__.py")
            if module is None:
                continue
            candidate = _build_candidate(mod_name, module, item, is_package=True)
            if candidate:
                candidates.append(candidate)

        # Se for um arquivo Python (exceto __init__.py)
        elif item.is_file() and item.suffix == ".py" and item.name not in {"__init__.py", "loader.py", "manifest.py"}:
            mod_name = item.stem
            if item.resolve() in seen_paths:
                continue
            module = _load_module(mod_name, item)
            if module is None:
                continue
            candidate = _build_candidate(mod_name, module, item, is_package=False)
            if candidate:
                candidates.append(candidate)

    valid_candidates = _validate_candidates(candidates)
    ordered_candidates = _sort_candidates(valid_candidates)

    # Aplica os mods na ordem resolvida
    for candidate in ordered_candidates:
        manifest = candidate.manifest
        try:
            getattr(candidate.module, manifest.entrypoint)()
            LOADED_MODS[manifest.id] = {
                "name": manifest.name,
                "version": manifest.version,
                "author": manifest.author,
                "priority": manifest.priority,
                "module": candidate.module,
                "manifest": manifest,
            }
            print(f"Mod carregado: {manifest.name} ({manifest.id}) - prioridade {manifest.priority}")
        except Exception as e:
            _register_failure(manifest.id, manifest.name, candidate.source_path, f"Erro ao aplicar mod: {e}")



def _load_module(mod_name, path):
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if not spec or not spec.loader:
            raise ImportError("Não foi possível criar a especificação do módulo")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        _register_failure(mod_name, mod_name, str(path), f"Erro ao carregar mod: {e}")
        return None



def _build_candidate(mod_name, module, path, is_package):
    try:
        manifest = build_manifest(mod_name, module, is_package=is_package)
        if not manifest.enabled:
            _register_failure(manifest.id, manifest.name, str(path), "Mod desabilitado no manifesto")
            return None
        return ModCandidate(
            manifest=manifest,
            module=module,
            source_path=str(path),
            is_package=is_package,
        )
    except Exception as e:
        _register_failure(mod_name, mod_name, str(path), f"Falha de validação do manifesto: {e}")
        return None



def _validate_candidates(candidates):
    id_map = defaultdict(list)
    for candidate in candidates:
        id_map[candidate.manifest.id].append(candidate)

    valid_candidates = []
    invalid_ids = set()
    for mod_id, grouped_candidates in id_map.items():
        if len(grouped_candidates) > 1:
            invalid_ids.add(mod_id)
            for candidate in grouped_candidates:
                _register_failure(
                    mod_id,
                    candidate.manifest.name,
                    candidate.source_path,
                    "ID duplicado entre mods carregáveis",
                )
        else:
            valid_candidates.append(grouped_candidates[0])

    candidate_by_id = {
        candidate.manifest.id: candidate
        for candidate in valid_candidates
        if candidate.manifest.id not in invalid_ids
    }

    missing_dependency_ids = set()
    for candidate in list(candidate_by_id.values()):
        missing_dependencies = [
            dependency_id
            for dependency_id in candidate.manifest.requires
            if dependency_id not in candidate_by_id
        ]
        if missing_dependencies:
            missing_dependency_ids.add(candidate.manifest.id)
            _register_failure(
                candidate.manifest.id,
                candidate.manifest.name,
                candidate.source_path,
                f"Dependências ausentes: {', '.join(missing_dependencies)}",
            )

    for mod_id in missing_dependency_ids:
        candidate_by_id.pop(mod_id, None)

    conflicting_ids = set()
    for candidate in candidate_by_id.values():
        active_conflicts = [
            conflict_id
            for conflict_id in candidate.manifest.conflicts
            if conflict_id in candidate_by_id
        ]
        if active_conflicts:
            conflicting_ids.add(candidate.manifest.id)
            _register_failure(
                candidate.manifest.id,
                candidate.manifest.name,
                candidate.source_path,
                f"Conflitos declarados com mods ativos: {', '.join(active_conflicts)}",
            )
            for conflict_id in active_conflicts:
                conflicting_ids.add(conflict_id)
                conflicting_candidate = candidate_by_id[conflict_id]
                _register_failure(
                    conflicting_candidate.manifest.id,
                    conflicting_candidate.manifest.name,
                    conflicting_candidate.source_path,
                    f"Conflito com mod ativo: {candidate.manifest.id}",
                )

    for mod_id in conflicting_ids:
        candidate_by_id.pop(mod_id, None)

    incompatible_ids = set()
    for candidate in candidate_by_id.values():
        manifest = candidate.manifest
        if not is_version_compatible(manifest.game_version, GAME_VERSION):
            incompatible_ids.add(manifest.id)
            _register_failure(
                manifest.id,
                manifest.name,
                candidate.source_path,
                f"Versão do jogo incompatível: requer {manifest.game_version}, atual {GAME_VERSION}",
            )
            continue
        if not is_version_compatible(manifest.loader_version, LOADER_VERSION):
            incompatible_ids.add(manifest.id)
            _register_failure(
                manifest.id,
                manifest.name,
                candidate.source_path,
                f"Versão do loader incompatível: requer {manifest.loader_version}, atual {LOADER_VERSION}",
            )

    for mod_id in incompatible_ids:
        candidate_by_id.pop(mod_id, None)

    return list(candidate_by_id.values())



def _sort_candidates(candidates):
    candidate_by_id = {candidate.manifest.id: candidate for candidate in candidates}
    indegree = {mod_id: 0 for mod_id in candidate_by_id}
    dependents = defaultdict(list)

    for candidate in candidates:
        for dependency_id in candidate.manifest.requires:
            if dependency_id in candidate_by_id:
                indegree[candidate.manifest.id] += 1
                dependents[dependency_id].append(candidate.manifest.id)

    ready = [
        candidate
        for candidate in candidates
        if indegree[candidate.manifest.id] == 0
    ]
    ready.sort(key=lambda candidate: (candidate.manifest.priority, candidate.manifest.name.lower()))

    ordered = []
    while ready:
        candidate = ready.pop(0)
        ordered.append(candidate)
        for dependent_id in sorted(dependents[candidate.manifest.id]):
            indegree[dependent_id] -= 1
            if indegree[dependent_id] == 0:
                ready.append(candidate_by_id[dependent_id])
                ready.sort(key=lambda current: (current.manifest.priority, current.manifest.name.lower()))

    if len(ordered) != len(candidates):
        ordered_ids = {candidate.manifest.id for candidate in ordered}
        for candidate in candidates:
            if candidate.manifest.id not in ordered_ids:
                _register_failure(
                    candidate.manifest.id,
                    candidate.manifest.name,
                    candidate.source_path,
                    "Ciclo de dependências detectado",
                )
        return ordered

    return ordered



def _register_failure(mod_id, mod_name, source_path, reason):
    FAILED_MODS.setdefault(mod_id, []).append({
        "name": mod_name,
        "path": source_path,
        "reason": reason,
    })
    print(f"Falha no mod {mod_name} ({mod_id}): {reason}")
