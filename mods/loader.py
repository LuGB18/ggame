import importlib.util
from pathlib import Path

# Define a pasta onde os mods estão localizados (mesmo diretório deste arquivo)
MODS_FOLDER = Path(__file__).parent
# Dicionário para armazenar mods carregados com sucesso
LOADED_MODS = {}

def load_mods():
    """
    Carrega e aplica mods encontrados na pasta MODS_FOLDER.
    - Procura por pacotes (diretórios com __init__.py) e arquivos .py individuais.
    - Para pacotes: exige 'MOD_INFO' (dict) e função 'apply'.
    - Para arquivos: exige função 'apply'; 'PRIORITY' é opcional.
    - Ordena mods por prioridade e aplica na ordem.
    - Armazena mods aplicados em LOADED_MODS.
    """
    mods_to_apply = []

    # Varre todos os itens na pasta de mods
    for item in MODS_FOLDER.iterdir():
        # Se for um diretório de pacote Python com __init__.py
        if item.is_dir() and (item / "__init__.py").exists():
            mod_name = item.name
            try:
                # Cria especificação de importação para o pacote
                spec = importlib.util.spec_from_file_location(mod_name, item / "__init__.py")
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Verifica se possui os atributos obrigatórios
                    if hasattr(module, "MOD_INFO") and hasattr(module, "apply"):
                        priority = module.MOD_INFO.get("PRIORITY", 0)  # prioridade padrão 0
                        mods_to_apply.append((priority, mod_name, module))
            except Exception as e:
                print(f"Erro ao carregar mod {mod_name}: {e}")

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
            module.apply()  # Executa a função principal do mod
            LOADED_MODS[mod_name] = module  # Armazena o mod carregado
            print(f"Mod carregado: {mod_name} - prioridade {priority}")
        except Exception as e:
            print(f"Erro ao aplicar mod {mod_name}: {e}")