import importlib
import importlib.util
from pathlib import Path
from typing import Any, Callable

MODS_FOLDER = Path(__file__).parent
LOADED_MODS = {}
FAILED_MODS = {}
PATCH_REGISTRY = {}
PATCH_REPORT = {}
_ORIGINAL_TARGETS = {}

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


def _resolve_owner_and_attribute(target: str):
    path_parts = target.split(".")
    if len(path_parts) < 2:
        raise ValueError(f"Alvo inválido: {target}")

    for index in range(len(path_parts) - 1, 0, -1):
        module_name = ".".join(path_parts[:index])
        try:
            owner = importlib.import_module(module_name)
            remaining_parts = path_parts[index:]
            break
        except ModuleNotFoundError:
            continue
    else:
        raise ValueError(f"Não foi possível importar o alvo: {target}")

    for part in remaining_parts[:-1]:
        if not hasattr(owner, part):
            raise ValueError(f"Atributo intermediário não encontrado em {target}: {part}")
        owner = getattr(owner, part)

    attribute_name = remaining_parts[-1]
    if not hasattr(owner, attribute_name):
        raise ValueError(f"Atributo final não encontrado em {target}: {attribute_name}")
    return owner, attribute_name


def _resolve_target(target: str) -> Callable[..., Any]:
    owner, attribute_name = _resolve_owner_and_attribute(target)
    resolved = getattr(owner, attribute_name)
    if not callable(resolved):
        raise ValueError(f"Alvo não é chamável: {target}")
    return resolved


def _register_failure(mod_id: str, target: str, reason: str):
    FAILED_MODS.setdefault(mod_id, []).append({"target": target, "reason": reason})


def register_patch(mod_id: str, patch_type: str, target: str, priority: int, conflict_policy: str, patch_fn: Callable[..., Any]):
    if not mod_id:
        raise ValueError("mod_id é obrigatório")
    if patch_type not in PATCH_TYPES:
        raise ValueError(f"Tipo de patch inválido: {patch_type}")
    if not target:
        raise ValueError("target é obrigatório")
    if not isinstance(priority, int):
        raise ValueError("priority deve ser int")
    if conflict_policy not in CONFLICT_POLICIES:
        raise ValueError(f"Política de conflito inválida: {conflict_policy}")
    if not callable(patch_fn):
        raise ValueError("patch_fn deve ser chamável")

    _resolve_target(target)
    patch_entry = {
        "mod_id": mod_id,
        "type": patch_type,
        "target": target,
        "priority": priority,
        "conflict_policy": conflict_policy,
        "fn": patch_fn,
        "active": True,
    }
    PATCH_REGISTRY.setdefault(target, []).append(patch_entry)
    PATCH_REGISTRY[target].sort(key=lambda item: (item["priority"], item["mod_id"], item["type"]))
    return patch_entry


def _build_replace_chain(target: str, replace_patches, original_fn):
    if not replace_patches:
        return original_fn

    chainable = [patch for patch in replace_patches if patch["conflict_policy"] == "chain"]
    non_chainable = [patch for patch in replace_patches if patch["conflict_policy"] != "chain"]

    if len(non_chainable) > 1:
        active_patch = non_chainable[0]
        for rejected in non_chainable[1:]:
            rejected["active"] = False
            _register_failure(
                rejected["mod_id"],
                target,
                f"replace conflitante com mod {active_patch['mod_id']}",
            )
        replace_patches = [active_patch, *chainable]
    elif non_chainable:
        replace_patches = [non_chainable[0], *chainable]
    else:
        replace_patches = chainable

    replace_patches.sort(key=lambda item: (item["priority"], item["mod_id"]))

    next_fn = original_fn
    for patch in reversed(replace_patches):
        patch_fn = patch["fn"]
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
    before_patches = [patch for patch in patches if patch["type"] == "before" and patch["active"]]
    after_patches = [patch for patch in patches if patch["type"] == "after" and patch["active"]]
    replace_patches = [patch for patch in patches if patch["type"] == "replace" and patch["active"]]

    before_patches.sort(key=lambda item: (item["priority"], item["mod_id"]))
    after_patches.sort(key=lambda item: (item["priority"], item["mod_id"]), reverse=True)
    core_fn = _build_replace_chain(target, replace_patches, original_fn)

    def composed(*args, **kwargs):
        for patch in before_patches:
            patch["fn"](*args, **kwargs)
        result = core_fn(*args, **kwargs)
        for patch in after_patches:
            updated = patch["fn"](result, *args, **kwargs)
            if updated is not None:
                result = updated
        return result

    owner, attribute_name = _resolve_owner_and_attribute(target)
    setattr(owner, attribute_name, composed)
    PATCH_REPORT[target] = {
        "before": [patch for patch in before_patches if patch["active"]],
        "replace": [patch for patch in replace_patches if patch["active"]],
        "after": [patch for patch in after_patches if patch["active"]],
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
                    "mod_id": patch["mod_id"],
                    "priority": patch["priority"],
                    "conflict_policy": patch["conflict_policy"],
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
    raise ValueError(f"Não foi possível criar spec para {mod_name}")


def load_mods():
    mods_to_apply = []
    reset_registry()

    for item in MODS_FOLDER.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            mod_name = item.name
            try:
                module = _load_module_from_path(mod_name, item / "__init__.py")
                if hasattr(module, "MOD_INFO") and hasattr(module, "apply"):
                    priority = module.MOD_INFO.get("PRIORITY", 0)
                    mods_to_apply.append((priority, mod_name, module))
            except Exception as error:
                _register_failure(mod_name, str(item), str(error))
                print(f"Erro ao carregar mod {mod_name}: {error}")
        elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
            mod_name = item.stem
            try:
                module = _load_module_from_path(mod_name, item)
                if hasattr(module, "apply"):
                    priority = getattr(module, "PRIORITY", 0)
                    mods_to_apply.append((priority, mod_name, module))
            except Exception as error:
                _register_failure(mod_name, str(item), str(error))
                print(f"Erro no mod {mod_name}: {error}")

    mods_to_apply.sort(key=lambda item: (item[0], item[1]))

    for priority, mod_name, module in mods_to_apply:
        try:
            module.apply()
            LOADED_MODS[mod_name] = {"module": module, "priority": priority}
            print(f"Mod carregado: {mod_name} - prioridade {priority}")
        except Exception as error:
            _register_failure(mod_name, "apply", str(error))
            print(f"Erro ao aplicar mod {mod_name}: {error}")

    apply_registered_patches()
