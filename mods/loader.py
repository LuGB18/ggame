import importlib.util
from pathlib import Path

MODS_FOLDER = Path(__file__).parent
LOADED_MODS = {}

def load_mods():
    """
    Loads and applies mods from the MODS_FOLDER directory.
    This function scans the MODS_FOLDER for both package and single-file Python mods.
    For each valid mod, it attempts to import the module and checks for the presence of
    required attributes:
      - For package mods (directories with __init__.py): must have 'MOD_INFO' dict and 'apply' function.
      - For single-file mods: must have 'apply' function; may have 'PRIORITY' attribute.
    Mods are collected along with their priority (default 0 if not specified), sorted by priority,
    and then applied in order. Successfully loaded mods are stored in the LOADED_MODS dictionary.
    Any errors during loading or applying mods are caught and printed.
    Returns:
        None
    """
    mods_to_apply = []

    # Primeiro, varre todos os mods
    for item in MODS_FOLDER.iterdir():
        if item.is_dir() and (item / "__init__.py").exists():
            mod_name = item.name
            try:
                spec = importlib.util.spec_from_file_location(mod_name, item / "__init__.py")
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "MOD_INFO") and hasattr(module, "apply"):
                        priority = module.MOD_INFO.get("PRIORITY", 0)  # padrão 0
                        mods_to_apply.append((priority, mod_name, module))
            except Exception as e:
                print(f"Erro ao carregar mod {mod_name}: {e}")

        elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
            mod_name = item.stem
            try:
                spec = importlib.util.spec_from_file_location(mod_name, item)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "apply"):
                        priority = getattr(module, "PRIORITY", 0)  # mods simples podem ter variável PRIORITY
                        mods_to_apply.append((priority, mod_name, module))
            except Exception as e:
                print(f"Erro no mod {mod_name}: {e}")

    # Ordena pelos números de prioridade (maior depois)
    mods_to_apply.sort(key=lambda x: x[0])

    # Aplica os mods na ordem
    for priority, mod_name, module in mods_to_apply:
        try:
            module.apply()
            LOADED_MODS[mod_name] = module
            print(f"Mod carregado: {mod_name} - prioridade {priority}")
        except Exception as e:
            print(f"Erro ao aplicar mod {mod_name}: {e}")