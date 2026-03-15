class BattleState:
    """
    Represents the state of a battle, including player and enemy stats, potion counts, health values, and game rules.
    Attributes:
        ATK_PL (int): Player's attack value.
        ATK_EN (int): Enemy's attack value.
        DEF_PL (int): Player's defense value.
        DEF_EN (int): Enemy's defense value.
        HL_PL (int): Player's current health.
        HL_EN (int): Enemy's current health.
        POTIONS_PL (int): Number of potions the player has.
        POTIONS_EN (int): Number of potions the enemy has.
        POTION_HEAL_AMOUNT (int): Amount of health restored by a potion.
        PLAYER_MAX_HP (int): Maximum health for the player.
        ENEMY_MAX_HP (int): Maximum health for the enemy.
        IS_WON (bool): Indicates if the battle has been won.
        WHO_WON (str): Identifier for who won the battle.
        CUR_ROUND (str): Indicates whose turn it is ('pl' for player, 'en' for enemy).
    """
    def __init__(self) -> None:
        # stats base
        self.ATK_PL: int = 10
        self.ATK_EN: int = 10

        self.DEF_PL: int = 5
        self.DEF_EN: int = 5

        self.HL_PL: int = 100
        self.HL_EN: int = 100

        self.POTIONS_PL: int = 3
        self.POTIONS_EN: int = 3

        #regras de vida e cura
        self.POTION_HEAL_AMOUNT: int = 50
        self.PLAYER_MAX_HP: int = 100
        self.ENEMY_MAX_HP: int = 100

        #regras de vitoria e perda, junto a controle de rounds.
        self.IS_WON: bool = False
        self.WHO_WON: str = ''
        self.CUR_ROUND: str = 'pl'