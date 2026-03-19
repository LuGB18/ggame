import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from libs.battle import MOD_CONTEXT

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
    Carrega e aplica mods encontrados na pasta MODS_FOLDER.
    - Procura por pacotes (diretórios com __init__.py) e arquivos .py individuais.
    - Para pacotes: exige 'MOD_INFO' (dict) e função 'apply'.
    - Para arquivos: exige função 'apply'; 'PRIORITY' é opcional.
    - Ordena mods por prioridade e aplica na ordem.
    - Armazena mods aplicados em LOADED_MODS.
    """
    return DEFAULT_LOADER.load_mods()


def unpatch_all(mod_name: str) -> int:
    return DEFAULT_LOADER.unpatch_all(mod_name)
        # Se for um arquivo Python (exceto __init__.py)
        elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
            mod_name = item.stem
            try:
                # Cria especificação de importação para o arquivo
                spec = importlib.util.spec_from_file_location(mod_name, item)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Verifica se possui a função obrigatória
                    if hasattr(module, "apply"):
                        priority = getattr(module, "PRIORITY", 0)  # prioridade padrão 0
                        mods_to_apply.append((priority, mod_name, module))
            except Exception as e:
                print(f"Erro no mod {mod_name}: {e}")

    # Ordena mods pela prioridade (menor valor primeiro)
    mods_to_apply.sort(key=lambda x: x[0])

    # Aplica os mods na ordem de prioridade
    for priority, mod_name, module in mods_to_apply:
        try:
            _apply_mod(module)  # Executa a função principal do mod
            LOADED_MODS[mod_name] = module  # Armazena o mod carregado
            print(f"Mod carregado: {mod_name} - prioridade {priority}")
        except Exception as e:
            print(f"Erro ao aplicar mod {mod_name}: {e}")
