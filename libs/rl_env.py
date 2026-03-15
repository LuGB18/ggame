import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .battle import BattleSystem
from .variables import BattleState
from .goblin_ai import Goblin  # Certifique-se de que o arquivo goblin.py existe e contém a classe Goblin

class GoblinBattleEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.battle = BattleSystem()
        # 4 observações: [hp_pl_norm, potions_pl, hp_en_norm, potions_en]
        self.observation_space = spaces.Box(low=0, high=1, shape=(4,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)  # 0=attack, 1=defend, 2=potion

    def reset(self, seed=None):
        self.battle.new_battle()
        return self._get_obs(), {}

    def _get_obs(self):
        hp_pl = self.battle.battle.HL_PL / self.battle.battle.PLAYER_MAX_HP
        hp_en = self.battle.battle.HL_EN / self.battle.battle.ENEMY_MAX_HP
        return np.array([
            hp_pl,
            self.battle.battle.POTIONS_PL / 5.0,   # normaliza assumindo max 5 poções
            hp_en,
            self.battle.battle.POTIONS_EN / 5.0
        ], dtype=np.float32)

    def step(self, action):
        # Executa ação do player
        reward = 0
        done = False
        truncated = False

        if action == 0:    # attack
            self.battle.attack('en')
            reward += 0.2   # pequeno incentivo por dano
        elif action == 1:  # defend
            success, new_hp = self.battle.defend('pl')
            reward += 0.1 if success else -0.05
        elif action == 2:  # potion
            if self.battle.battle.POTIONS_PL > 0:
                self.battle.use_potion('pl')
                reward += 0.3 if self.battle.battle.HL_PL < 40 else 0.05
            else:
                reward -= 0.1  # penalidade por tentar poção sem ter

        # Checa se terminou depois da ação do player
        if self.battle.battle.IS_WON:
            reward = 100 if self.battle.battle.WHO_WON == 'pl' else -100
            done = True
            return self._get_obs(), reward, done, truncated, {}

        # Turno do goblin (IA burra por enquanto)
        goblin_choice = Goblin(self.battle.cur_stats('en')).mk_choice()
        if goblin_choice == 'attack':
            self.battle.attack('pl')
        elif goblin_choice == 'defend':
            self.battle.defend('en')
        elif goblin_choice == 'potion':
            self.battle.use_potion('en')

        # Checa novamente depois do goblin
        if self.battle.battle.IS_WON:
            reward = 100 if self.battle.battle.WHO_WON == 'pl' else -100
            done = True

        # Pequena penalidade por tempo (incentiva terminar rápido)
        reward -= 0.01

        return self._get_obs(), reward, done, truncated, {}