from .variables import BattleState
from random import choice
from os import system

class BattleSystem:
    """
    BattleSystem manages the logic and state transitions for a turn-based battle between a player and an enemy.
    Attributes:
        battle (BattleState): The current state of the battle.
    Methods:
        new_battle():
            Initializes a new battle by creating a new BattleState instance.
        use_potion(who):
            Uses a potion for the specified participant ('pl' for player, 'en' for enemy).
            Decreases the potion count and heals the participant by a fixed amount.
            Returns the updated health value.
        cur_stats(who) -> tuple:
            Returns a tuple containing the current health and potion count for the specified participant.
        all_stats() -> tuple:
            Returns a tuple with all relevant stats for both player and enemy, including attack, defense, health, and potions.
        defend(who):
            Simulates a defend action for the specified participant.
            Randomly determines if the defense is successful, temporarily reduces the opponent's attack, and applies damage.
            Returns a tuple (defense_successful: bool, updated_health: int).
        attack(who):
            Applies an attack to the specified participant, reducing their health by the opponent's attack value.
            Updates the battle state if a participant's health drops to zero or below.
            Returns the updated health value.
        next_round():
            Switches the current round to the other participant.
            Returns the identifier of the participant whose turn is next ('pl' or 'en').
    """
    battle : BattleState

    def new_battle(self):
        self.battle = BattleState()

    def use_potion(self, who):
        match who:
            case 'pl':
                if self.battle.POTIONS_PL >= 1:
                    self.battle.POTIONS_PL -= 1
                    if self.battle.HL_PL+self.battle.POTION_HEAL_AMOUNT > self.battle.PLAYER_MAX_HP:
                        self.battle.HL_PL = self.battle.PLAYER_MAX_HP
                    else:
                        self.battle.HL_PL += self.battle.POTION_HEAL_AMOUNT
                    return self.battle.HL_PL
                    
            case 'en':
                if self.battle.POTIONS_EN >= 1:
                    self.battle.POTIONS_EN -= 1
                    if self.battle.HL_EN > self.battle.POTION_HEAL_AMOUNT:
                        self.battle.HL_EN = self.battle.ENEMY_MAX_HP
                    else:
                        self.battle.HL_EN += self.battle.POTION_HEAL_AMOUNT
                    return self.battle.HL_EN
                    
    def cur_stats(self, who) -> tuple:
        match who:
            case 'pl':
                return (self.battle.HL_PL, self.battle.POTIONS_PL)
            case 'en':
                return (self.battle.HL_EN, self.battle.POTIONS_EN)
        return (0,1)

    def all_stats(self) -> tuple:
        return (self.battle.ATK_PL, self.battle.DEF_PL, self.battle.HL_PL, self.battle.POTIONS_PL, self.battle.ATK_EN, self.battle.DEF_EN, self.battle.HL_EN, self.battle.POTIONS_EN)

    def defend(self,who): 
        f_c = choice([True, False])
        match who:
            case 'pl':
                if f_c:
                    old = self.battle.ATK_EN
                    self.battle.ATK_EN -= self.battle.DEF_PL
                    life = self.attack('pl')
                    self.battle.ATK_EN = old
                    return (True, life)
                else:
                    return (False, self.attack('pl'))
            case 'en':
                if f_c:
                    old = self.battle.ATK_PL
                    self.battle.ATK_PL -= self.battle.DEF_EN
                    life = self.attack('en')
                    self.battle.ATK_PL = old
                    return (True, life)
                else:
                    return (False, self.attack('en'))     
        return (True, 0)      
        
                    
    def attack(self, who):
        match who:
            case 'pl':
                    self.battle.HL_PL -= self.battle.ATK_EN
                    if self.battle.HL_PL <= 0:
                        self.battle.IS_WON = True
                        self.battle.WHO_WON = 'en'
                    return self.battle.HL_PL
            case 'en':
                    self.battle.HL_EN -= self.battle.ATK_PL
                    if self.battle.HL_EN <= 0:
                        self.battle.IS_WON = True
                        self.battle.WHO_WON = 'pl'
                    return self.battle.HL_EN
    
    def next_round(self):
        if self.battle.CUR_ROUND == 'pl':
            self.battle.CUR_ROUND = 'en'
            return 'en'
        else:
            self.battle.CUR_ROUND = 'pl'
            return 'pl'