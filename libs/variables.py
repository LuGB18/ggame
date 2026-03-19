from .log import log

class BattleState:
    """
    Represents the state of a battle, including player and enemy stats, potion counts, health values, and game rules.
    """
    def __init__(self, initial_values: dict | None = None) -> None:
        initial_values = initial_values or {}
        # Player's attack value
        self.ATK_PL: int = initial_values.get('ATK_PL', 10)
        # Enemy's attack value
        self.ATK_EN: int = initial_values.get('ATK_EN', 10)

        # Player's defense value
        self.DEF_PL: int = initial_values.get('DEF_PL', 5)
        # Enemy's defense value
        self.DEF_EN: int = initial_values.get('DEF_EN', 5)

        # Player's current health
        self.HL_PL: int = initial_values.get('HL_PL', 100)
        # Enemy's current health
        self.HL_EN: int = initial_values.get('HL_EN', 100)

        # Number of potions the player has
        self.POTIONS_PL: int = initial_values.get('POTIONS_PL', 3)
        # Number of potions the enemy has
        self.POTIONS_EN: int = initial_values.get('POTIONS_EN', 3)

        # Amount of health restored by a potion
        self.POTION_HEAL_AMOUNT: int = initial_values.get('POTION_HEAL_AMOUNT', 50)
        # Maximum health for the player
        self.PLAYER_MAX_HP: int = initial_values.get('PLAYER_MAX_HP', 100)
        # Maximum health for the enemy
        self.ENEMY_MAX_HP: int = initial_values.get('ENEMY_MAX_HP', 100)

        # Indicates if the battle has been won
        self.IS_WON: bool = initial_values.get('IS_WON', False)
        # Identifier for who won the battle
        self.WHO_WON: str = initial_values.get('WHO_WON', '')
        # Indicates whose turn it is ('pl' for player, 'en' for enemy)
        self.CUR_ROUND: str = initial_values.get('CUR_ROUND', 'pl')