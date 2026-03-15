class BattleState:
    """
    Represents the state of a battle, including player and enemy stats, potion counts, health values, and game rules.
    """
    def __init__(self) -> None:
        # Player's attack value
        self.ATK_PL: int = 10
        # Enemy's attack value
        self.ATK_EN: int = 10

        # Player's defense value
        self.DEF_PL: int = 5
        # Enemy's defense value
        self.DEF_EN: int = 5

        # Player's current health
        self.HL_PL: int = 100
        # Enemy's current health
        self.HL_EN: int = 100

        # Number of potions the player has
        self.POTIONS_PL: int = 3
        # Number of potions the enemy has
        self.POTIONS_EN: int = 3

        # Amount of health restored by a potion
        self.POTION_HEAL_AMOUNT: int = 50
        # Maximum health for the player
        self.PLAYER_MAX_HP: int = 100
        # Maximum health for the enemy
        self.ENEMY_MAX_HP: int = 100

        # Indicates if the battle has been won
        self.IS_WON: bool = False
        # Identifier for who won the battle
        self.WHO_WON: str = ''
        # Indicates whose turn it is ('pl' for player, 'en' for enemy)
        self.CUR_ROUND: str = 'pl'
