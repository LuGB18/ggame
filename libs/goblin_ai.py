from random import choice

class Goblin:
    """
    Goblin class represents a simple AI for a goblin character with health and potion management.
    Attributes:
        LOCAL_HEALTH (int): The current health of the goblin.
        LOCAL_POTIONS (int): The number of potions the goblin has.
    Methods:
        __init__(stats: tuple) -> None:
            Initializes the goblin's health and potions from the given stats tuple.
        upd_stats(stats: tuple):
            Updates the goblin's health and potions from the given stats tuple.
        mk_choice():
            Determines the goblin's next action based on its current health and potions.
            Returns:
                str: 'potion' if health is low and potions are available,
                     otherwise randomly chooses between 'attack' and 'defend'.
    """
    LOCAL_POTIONS : int
    LOCAL_HEALTH : int

    def __init__(self, stats:tuple) -> None:
        self.LOCAL_HEALTH = stats[0]
        self.LOCAL_POTIONS = stats[1]

    def upd_stats(self, stats:tuple):
        self.LOCAL_HEALTH = stats[0]
        self.LOCAL_POTIONS = stats[1]

    def mk_choice(self):
        if self.LOCAL_HEALTH < 25 and self.LOCAL_POTIONS >= 1:
            return 'potion'
        else:
            f_c = choice([True, False])
            if f_c:
                return 'attack'
            else:
                return 'defend'
