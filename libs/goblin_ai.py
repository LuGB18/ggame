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
        # Inicializa a vida e poções do goblin a partir de uma tupla de status
        self.LOCAL_HEALTH = stats[0]
        self.LOCAL_POTIONS = stats[1]

    def upd_stats(self, stats:tuple):
        # Atualiza a vida e poções do goblin com novos valores da tupla de status
        self.LOCAL_HEALTH = stats[0]
        self.LOCAL_POTIONS = stats[1]

    def mk_choice(self):
        # Decide a próxima ação do goblin:
        # Usa uma poção se a vida estiver baixa e houver poções disponíveis,
        # caso contrário, escolhe aleatoriamente entre atacar ou defender.
        if self.LOCAL_HEALTH < 25 and self.LOCAL_POTIONS >= 1:
            return 'potion'
        else:
            f_c = choice([True, False])
            if f_c:
                return 'attack'
            else:
                return 'defend'
