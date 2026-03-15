"""
Mod: rl_player
Faz patch no builtin `input` durante o turno do player,
interceptando o momento em que main.py pede '-> ' e retornando
a ação escolhida pelo modelo PPO no lugar do humano.

O modelo deve estar no root do projeto com o nome: ppo_goblin_battle.zip
"""

from pathlib import Path
import builtins
import numpy as np

MOD_INFO = {
    "name": "rl_player",
    "version": "1.0.0",
    "description": "Substitui o input do jogador por um agente PPO treinado com RL.",
    "author": "mod",
    "PRIORITY": 10,
}

MODEL_PATH = Path(__file__).parent.parent.parent / "ppo_goblin_battle.zip"

_model = None
_original_input = builtins.input

# Referência ao BattleSystem — preenchida no apply() via patch em main
_get_bs = None


def _predict_action() -> str:
    """Pede as stats ao BS e retorna a ação do modelo como string '1', '2' ou '3'."""
    bs = _get_bs()
    stats_pl = bs.cur_stats('pl')
    stats_en = bs.cur_stats('en')

    obs = np.array([
        stats_pl[0] / 100.0,
        stats_pl[1] / 5.0,
        stats_en[0] / 100.0,
        stats_en[1] / 5.0,
    ], dtype=np.float32)

    action, _ = _model.predict(obs, deterministic=True)

    # Converte índice do modelo (0,1,2) para o número que main.py espera (1,2,3)
    action_map = {0: '1', 1: '2', 2: '3'}
    choice = action_map.get(int(action), '1')
    print(f'[RL] -> {choice}')
    return choice


def _patched_input(prompt=''):
    """
    Substitui builtins.input.
    Quando o prompt for '-> ' (turno do player), o modelo responde.
    Qualquer outro input (pausas com input()) passa para o original.
    """
    if prompt == '-> ':
        return _predict_action()
    return _original_input(prompt)


def apply():
    global _model, _get_bs

    try:
        from stable_baselines3 import PPO
    except ImportError:
        raise ImportError(
            "stable-baselines3 não encontrado. "
            "Instale com: pip install stable-baselines3"
        )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado em: {MODEL_PATH}\n"
            "Certifique-se de que 'ppo_goblin_battle.zip' está na raiz do projeto."
        )

    _model = PPO.load(str(MODEL_PATH))

    # Registra o getter do BS — main.py cria BS no __main__, buscamos via sys.modules
    import sys
    def _get_bs_from_main():
        return sys.modules['__main__'].BS

    _get_bs = _get_bs_from_main

    # Faz o patch no builtin input — afeta todo o processo, inclusive main.py
    builtins.input = _patched_input

    print(f"[rl_player] Modelo PPO carregado de: {MODEL_PATH}")
    print("[rl_player] builtins.input patcheado — agente RL joga no lugar do player.")

