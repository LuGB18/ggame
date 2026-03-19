import importlib.util
from collections import defaultdict
import inspect
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from libs.battle import MOD_CONTEXT

from mods.manifest import (
    DEFAULT_GAME_VERSION,
    DEFAULT_LOADER_VERSION,
    ModCandidate,
    build_manifest,
    is_version_compatible,
)

# Define a pasta onde os mods estão localizados (mesmo diretório deste arquivo)
MODS_FOLDER = Path(__file__).parent


@dataclass
class AppliedPatch:
    mod_name: str
    patch_type: str
    target: Any
    attribute_name: str | None
    original: Callable[..., Any]
    wrapper: Callable[..., Any]


class ModContext:
    def __init__(self, loader: "ModLoader", mod_name: str) -> None:
        self._loader = loader
        self.mod_name = mod_name

    def register_hook(self, event_name: str, callback: Callable[..., Any]) -> None:
        self._loader.registered_hooks.setdefault(event_name, []).append({
            "mod_name": self.mod_name,
            "callback": callback,
        })

    def patch_function(
        self,
        target: Callable[..., Any],
        replacement: Callable[..., Any] | None = None,
        before: Callable[..., Any] | None = None,
        after: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        return self._loader.patch_callable(
            mod_name=self.mod_name,
            target=target,
            replacement=replacement,
            before=before,
            after=after,
        )

    def patch_method(
        self,
        cls: type,
        method_name: str,
        replacement: Callable[..., Any] | None = None,
        before: Callable[..., Any] | None = None,
        after: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        return self._loader.patch_method(
            mod_name=self.mod_name,
            cls=cls,
            method_name=method_name,
            replacement=replacement,
            before=before,
            after=after,
        )

    def set_stat(self, name: str, value: Any) -> None:
        self._loader.stats[name] = value

    def get_stat(self, name: str) -> Any:
        return self._loader.stats.get(name)

    def register_api(self, name: str, fn: Callable[..., Any]) -> None:
        self._loader.exported_apis[name] = {
            "mod_name": self.mod_name,
            "function": fn,
        }

    def log(self, level: str, message: str) -> None:
        print(f"[{level.upper()}] [{self.mod_name}] {message}")

    def get_loaded_mods(self) -> dict[str, ModuleType]:
        return dict(self._loader.loaded_mods)

    def unpatch_all(self, mod_name: str | None = None) -> int:
        return self._loader.unpatch_all(mod_name or self.mod_name)


class ModLoader:
    def __init__(self, mods_folder: Path | None = None) -> None:
        self.mods_folder = mods_folder or MODS_FOLDER
        self.loaded_mods: dict[str, ModuleType] = {}
        self.failed_mods: dict[str, str] = {}
        self.registered_hooks: dict[str, list[dict[str, Any]]] = {}
        self.applied_patches: list[AppliedPatch] = []
        self.exported_apis: dict[str, dict[str, Any]] = {}
        self.stats: dict[str, Any] = {}

    def _load_module(self, mod_name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if not spec or not spec.loader:
            raise ImportError(f"Não foi possível criar spec para {mod_name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _collect_mods(self) -> list[tuple[int, str, ModuleType]]:
        mods_to_apply: list[tuple[int, str, ModuleType]] = []

        for item in self.mods_folder.iterdir():
            if item.name == "__pycache__":
                continue

            if item.is_dir() and (item / "__init__.py").exists():
                mod_name = item.name
                try:
                    module = self._load_module(mod_name, item / "__init__.py")
                    if hasattr(module, "MOD_INFO") and hasattr(module, "apply"):
                        priority = module.MOD_INFO.get("PRIORITY", 0)
                        mods_to_apply.append((priority, mod_name, module))
                except Exception as exc:
                    self.failed_mods[mod_name] = str(exc)
                    print(f"Erro ao carregar mod {mod_name}: {exc}")
            elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                mod_name = item.stem
                try:
                    module = self._load_module(mod_name, item)
                    if hasattr(module, "apply"):
                        priority = getattr(module, "PRIORITY", 0)
                        mods_to_apply.append((priority, mod_name, module))
                except Exception as exc:
                    self.failed_mods[mod_name] = str(exc)
                    print(f"Erro no mod {mod_name}: {exc}")

        mods_to_apply.sort(key=lambda mod: mod[0])
        return mods_to_apply

    def _apply_mod(self, mod_name: str, module: ModuleType) -> None:
        ctx = ModContext(self, mod_name)
        apply_fn = getattr(module, "apply")
        signature = inspect.signature(apply_fn)
        positional_params = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        accepts_varargs = any(
            parameter.kind == inspect.Parameter.VAR_POSITIONAL
            for parameter in signature.parameters.values()
        )

        if len(positional_params) == 0 and not accepts_varargs:
            apply_fn()
        else:
            apply_fn(ctx)

        self.loaded_mods[mod_name] = module

    def patch_callable(
        self,
        mod_name: str,
        target: Callable[..., Any],
        replacement: Callable[..., Any] | None = None,
        before: Callable[..., Any] | None = None,
        after: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        module_name = getattr(target, "__module__", None)
        function_name = getattr(target, "__name__", None)
        if not module_name or not function_name:
            raise ValueError("O alvo precisa ser uma função nomeada com módulo acessível")

        module = inspect.getmodule(target)
        if module is None:
            raise ValueError("Não foi possível resolver o módulo da função alvo")

        wrapped = self._build_wrapper(target, replacement=replacement, before=before, after=after)
        setattr(module, function_name, wrapped)
        self.applied_patches.append(
            AppliedPatch(
                mod_name=mod_name,
                patch_type="function",
                target=module,
                attribute_name=function_name,
                original=target,
                wrapper=wrapped,
            )
        )
        return wrapped

    def patch_method(
        self,
        mod_name: str,
        cls: type,
        method_name: str,
        replacement: Callable[..., Any] | None = None,
        before: Callable[..., Any] | None = None,
        after: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        if not hasattr(cls, method_name):
            raise AttributeError(f"{cls.__name__} não possui o método {method_name}")

        original = getattr(cls, method_name)
        wrapped = self._build_wrapper(original, replacement=replacement, before=before, after=after)
        setattr(cls, method_name, wrapped)
        self.applied_patches.append(
            AppliedPatch(
                mod_name=mod_name,
                patch_type="method",
                target=cls,
                attribute_name=method_name,
                original=original,
                wrapper=wrapped,
            )
        )
        return wrapped

    def _build_wrapper(
        self,
        original: Callable[..., Any],
        replacement: Callable[..., Any] | None = None,
        before: Callable[..., Any] | None = None,
        after: Callable[..., Any] | None = None,
    ) -> Callable[..., Any]:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if before is not None:
                before(*args, **kwargs)

            if replacement is not None:
                result = replacement(original, *args, **kwargs)
            else:
                result = original(*args, **kwargs)

            if after is not None:
                after_result = after(result, *args, **kwargs)
                if after_result is not None:
                    result = after_result

            return result

        wrapped.__name__ = getattr(original, "__name__", "wrapped_mod_callable")
        wrapped.__doc__ = getattr(original, "__doc__")
        wrapped.__module__ = getattr(original, "__module__")
        wrapped.__wrapped__ = original
        return wrapped

    def unpatch_all(self, mod_name: str) -> int:
        restored = 0
        remaining_patches: list[AppliedPatch] = []

        for patch in reversed(self.applied_patches):
            if patch.mod_name != mod_name:
                remaining_patches.append(patch)
                continue

            setattr(patch.target, patch.attribute_name, patch.original)
            restored += 1

        remaining_patches.reverse()
        self.applied_patches[:] = remaining_patches
        return restored

    def load_mods(self) -> dict[str, ModuleType]:
        for mod_name in {patch.mod_name for patch in list(self.applied_patches)}:
            self.unpatch_all(mod_name)

        self.loaded_mods.clear()
        self.failed_mods.clear()
        self.registered_hooks.clear()
        self.applied_patches.clear()
        self.exported_apis.clear()
        self.stats.clear()

        for priority, mod_name, module in self._collect_mods():
            try:
                self._apply_mod(mod_name, module)
                print(f"Mod carregado: {mod_name} - prioridade {priority}")
            except Exception as exc:
                self.failed_mods[mod_name] = str(exc)
                print(f"Erro ao aplicar mod {mod_name}: {exc}")

        return self.loaded_mods


DEFAULT_LOADER = ModLoader()
# Dicionário para armazenar mods carregados com sucesso
LOADED_MODS = {}
FAILED_MODS = {}
GAME_VERSION = DEFAULT_GAME_VERSION
LOADER_VERSION = DEFAULT_LOADER_VERSION
LOADED_MODS = DEFAULT_LOADER.loaded_mods
FAILED_MODS = DEFAULT_LOADER.failed_mods
REGISTERED_HOOKS = DEFAULT_LOADER.registered_hooks
APPLIED_PATCHES = DEFAULT_LOADER.applied_patches
EXPORTED_APIS = DEFAULT_LOADER.exported_apis


def load_mods() -> dict[str, ModuleType]:

def _apply_mod(module):
    apply_signature = inspect.signature(module.apply)
    if len(apply_signature.parameters) == 0:
        module.apply()
        return
    module.apply(MOD_CONTEXT)


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
    return DEFAULT_LOADER.load_mods()


def unpatch_all(mod_name: str) -> int:
    return DEFAULT_LOADER.unpatch_all(mod_name)
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
            _apply_mod(module)  # Executa a função principal do mod
            LOADED_MODS[mod_name] = module  # Armazena o mod carregado
            print(f"Mod carregado: {mod_name} - prioridade {priority}")
        except Exception as e:
            print(f"Erro ao aplicar mod {mod_name}: {e}")
