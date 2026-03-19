import subprocess
from mods import loader

class UI_Renderer:
    """
    UI_Renderer is a class responsible for rendering the user interface of the game in the console.
    """

    def clean_screen(self):
        # Limpa a tela do console.
        subprocess.run('cls', shell=True)

    def main_menu(self):
        # Exibe o menu principal do jogo.
        loader.trigger_hooks('ui.main_menu.before', {'ui_renderer': self})
        print('''
    ----------------------------
    -        Bem Vindo!        -
    ----------------------------
    
        1- Batalhar
        2- Mods
        3- Sair
              ''')
        loader.trigger_hooks('ui.main_menu.after', {'ui_renderer': self})
        
    def showmods(self, mods):
        # Mostra a lista de mods carregados.
        loader.trigger_hooks('ui.showmods.before', {'ui_renderer': self, 'mods': mods})
        i = 1
        stats = f'- MODS CARREGADOS: {len(mods)} -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        for mod in mods:
            print(f'{i} - {mod}')
        print(f'\n')
        loader.trigger_hooks('ui.showmods.after', {'ui_renderer': self, 'mods': mods})

    def menu_battle(self, stats_pl:tuple, stats_en:tuple):
        # Exibe o menu de batalha com os status do jogador e do inimigo.
        loader.trigger_hooks('ui.menu_battle.before', {'ui_renderer': self, 'stats_pl': stats_pl, 'stats_en': stats_en})
        stats = f'- STATS: Player(Vida:{stats_pl[0]}, Poções:{stats_pl[1]}), Inimigo(Vida:{stats_en[0]}, Poções:{stats_en[1]}) -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        print('''
    1 - Atacar
    2 - Defender
    3 - Usar Poção (Recupera 50 de Vida)''')
        loader.trigger_hooks('ui.menu_battle.after', {'ui_renderer': self, 'stats_pl': stats_pl, 'stats_en': stats_en})
        
    def show_defend(self, who, defended:bool):
        # Mostra o resultado da ação de defesa do jogador ou inimigo.
        match who:
            case 'pl':
                stats = '- Você conseguiu se defender, e sofreu menos dano! -' if defended else '- Aw.. Não conseguiu defender, sofreu dano normal. -'
            case 'en':
                stats = '- Aw.. o Inimigo conseguiu se defender e sofreu menos dano. -' if defended else '- O Inimigo Não conseguiu defender e sofreu dano normal! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')
    
    def used_potion(self, who):
        # Mostra mensagem quando uma poção é usada.
        match who:
            case 'pl':
                stats = '- Você usou uma poção e recuperou vida. -'
            case 'en':
                stats = '- o Inimigo usou uma poção e recuperou vida. -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')

    def show_action(self, who, action):
        # Mostra qual ação foi realizada pelo jogador ou inimigo.
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
        # Mostra quem venceu a batalha.
        match who:
            case 'pl':
                stats = '- Você Ganhou! -'
            case 'en':
                stats = '- o Inimigo Ganhou! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')

    def show_attack(self, who, DMG:int):
        # Mostra o dano causado por um ataque do jogador ou inimigo.
        match who:
            case 'pl':
                stats = f'- Você atacou e infrigiu:{DMG} de Dano! -'
            case 'en':
                stats =  f'- o Inimigo atacou e infrigiu:{DMG} de Dano! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')
