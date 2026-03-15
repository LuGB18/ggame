from os import system

class UI_Renderer:
    """
    UI_Renderer is a class responsible for rendering the user interface of the game in the console.
    Methods
    -------
    clean_screen():
        Clears the console screen.
    main_menu():
        Displays the main menu options to the player.
    showmods(mods):
        Displays the list of loaded mods.
    menu_battle(stats_pl: tuple, stats_en: tuple):
        Shows the battle menu with player and enemy stats.
    show_defend(who, defended: bool):
        Displays the result of a defend action for the player or enemy.
    used_potion(who):
        Shows a message indicating that a potion was used by the player or enemy.
    show_action(who, action):
        Displays the action taken by the player or enemy.
    show_win(who):
        Shows a message indicating the winner of the battle.
    show_attack(who, DMG: int):
        Displays the damage dealt by the player or enemy during an attack.
    """

    def clean_screen(self):
        system('cls')

    def main_menu(self):
        print('''
    ----------------------------
    -        Bem Vindo!        -
    ----------------------------
    
        1- Batalhar
        2- Mods
        3- Sair
              ''')
        
    def showmods(self, mods):
        i = 1
        stats = f'- MODS CARREGADOS: {len(mods)} -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        for mod in mods:
            print(f'{i} - {mod}')
        print(f'\n')

    def menu_battle(self, stats_pl:tuple, stats_en:tuple):
        stats = f'- STATS: Player(Vida:{stats_pl[0]}, Poções:{stats_pl[1]}), Inimigo(Vida:{stats_en[0]}, Poções:{stats_en[1]}) -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        print('''
    1 - Atacar
    2 - Defender
    3 - Usar Poção (Recupera 50 de Vida)''')
        
    def show_defend(self, who, defended:bool):
        match who:
            case 'pl':
                stats = '- Você conseguiu se defender, e sofreu menos dano! -' if defended else '- Aw.. Não conseguiu defender, sofreu dano normal. -'
            case 'en':
                stats = '- Aw.. o Inimigo conseguiu se defender e sofreu menos dano. -' if defended else '- O Inimigo Não conseguiu defender e sofreu dano normal! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')
    
    def used_potion(self, who):
        match who:
            case 'pl':
                stats = '- Você usou uma poção e recuperou vida. -'
            case 'en':
                stats = '- o Inimigo usou uma poção e recuperou vida. -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')

    def show_action(self, who, action):
        match who:
            case 'pl':
                match action:
                    case 'attack':
                        stats='- Você usou atacar! -'
                    case 'defend':
                        stats='- Você usou Defender! -'
                    case 'potion':
                        stats='- Você usou uma Poção! -'
            case 'en':
                match action:
                    case 'attack':
                        stats='- o Inimigo usou atacar! -'
                    case 'defend':
                        stats='- o Inimigo usou Defender! -'
                    case 'potion':
                        stats='- o Inimigo uma Poção! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')
    
    def show_win(self, who):
        match who:
            case 'pl':
                stats = '- Você Ganhou! -'
            case 'en':
                stats = '- o Inimigo Ganhou! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')

    def show_attack(self, who, DMG:int):
        match who:
            case 'pl':
                stats = f'- Você atacou e infrigiu:{DMG} de Dano! -'
            case 'en':
                stats =  f'- o Inimigo atacou e infrigiu:{DMG} de Dano! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')