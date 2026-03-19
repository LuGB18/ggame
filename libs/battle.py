from .variables import BattleState
from random import choice
from mods import loader

class BattleSystem:
    """
    BattleSystem gerencia a lógica e transições de estado para uma batalha por turnos entre jogador e inimigo.
    """
    battle : BattleState

    def new_battle(self):
        # Inicializa um novo estado de batalha
        self.battle = BattleState()

    def use_potion(self, who):
        # Usa uma poção para o jogador ('pl') ou inimigo ('en')
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.use_potion.before', event_payload)
        result = None
        match who:
            case 'pl':
                if self.battle.POTIONS_PL >= 1:
                    self.battle.POTIONS_PL -= 1
                    # Cura até o máximo de HP permitido
                    if self.battle.HL_PL+self.battle.POTION_HEAL_AMOUNT > self.battle.PLAYER_MAX_HP:
                        self.battle.HL_PL = self.battle.PLAYER_MAX_HP
                    else:
                        self.battle.HL_PL += self.battle.POTION_HEAL_AMOUNT
                    result = self.battle.HL_PL

            case 'en':
                if self.battle.POTIONS_EN >= 1:
                    self.battle.POTIONS_EN -= 1
                    # Cura até o máximo de HP permitido
                    if self.battle.HL_EN > self.battle.POTION_HEAL_AMOUNT:
                        self.battle.HL_EN = self.battle.ENEMY_MAX_HP
                    else:
                        self.battle.HL_EN += self.battle.POTION_HEAL_AMOUNT
                    result = self.battle.HL_EN
        loader.trigger_hooks('battle.use_potion.after', {**event_payload, 'result': result})
        return result

    def cur_stats(self, who) -> tuple:
        # Retorna HP e poções atuais do jogador ('pl') ou inimigo ('en')
        match who:
            case 'pl':
                return (self.battle.HL_PL, self.battle.POTIONS_PL)
            case 'en':
                return (self.battle.HL_EN, self.battle.POTIONS_EN)
        return (0,1)

    def all_stats(self) -> tuple:
        # Retorna todos os atributos relevantes de ambos os lados
        return (self.battle.ATK_PL, self.battle.DEF_PL, self.battle.HL_PL, self.battle.POTIONS_PL, self.battle.ATK_EN, self.battle.DEF_EN, self.battle.HL_EN, self.battle.POTIONS_EN)

    def defend(self,who): 
        # Simula ação de defesa para jogador ('pl') ou inimigo ('en')
        # Retorna se defesa foi bem-sucedida e HP atualizado
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.defend.before', event_payload)
        f_c = choice([True, False])
        result = (True, 0)
        match who:
            case 'pl':
                if f_c:
                    old = self.battle.ATK_EN
                    self.battle.ATK_EN -= self.battle.DEF_PL  # Reduz ataque do inimigo temporariamente
                    life = self.attack('pl')
                    self.battle.ATK_EN = old
                    result = (True, life)
                else:
                    result = (False, self.attack('pl'))
            case 'en':
                if f_c:
                    old = self.battle.ATK_PL
                    self.battle.ATK_PL -= self.battle.DEF_EN  # Reduz ataque do jogador temporariamente
                    life = self.attack('en')
                    self.battle.ATK_PL = old
                    result = (True, life)
                else:
                    result = (False, self.attack('en'))
        loader.trigger_hooks('battle.defend.after', {**event_payload, 'result': result})
        return result

    def attack(self, who):
        # Aplica ataque ao jogador ('pl') ou inimigo ('en')
        # Atualiza estado de vitória se HP chegar a zero
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.attack.before', event_payload)
        result = None
        match who:
            case 'pl':
                    self.battle.HL_PL -= self.battle.ATK_EN
                    if self.battle.HL_PL <= 0:
                        self.battle.IS_WON = True
                        self.battle.WHO_WON = 'en'
                    result = self.battle.HL_PL
            case 'en':
                    self.battle.HL_EN -= self.battle.ATK_PL
                    if self.battle.HL_EN <= 0:
                        self.battle.IS_WON = True
                        self.battle.WHO_WON = 'pl'
                    result = self.battle.HL_EN
        loader.trigger_hooks('battle.attack.after', {**event_payload, 'result': result})
        return result

    def next_round(self):
        # Alterna o turno entre jogador ('pl') e inimigo ('en')
        if self.battle.CUR_ROUND == 'pl':
            self.battle.CUR_ROUND = 'en'
            return 'en'
        else:
            self.battle.CUR_ROUND = 'pl'
            return 'pl'
