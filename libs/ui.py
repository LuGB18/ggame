import subprocess

class UI_Renderer:
    """
    UI_Renderer is a class responsible for rendering the user interface of the game in the console.
    """

    def clean_screen(self):
        # Limpa a tela do console.
        subprocess.run('cls', shell=True)

    def main_menu(self):
        # Exibe o menu principal do jogo.
        print('''
    ----------------------------
    -        Bem Vindo!        -
    ----------------------------
    
        1- Batalhar
        2- Mods
        3- Sair
              ''')
        
    def showmods(self, report):
        # Mostra a lista de mods carregados.
        total = len(report.discovered_mods)
        stats = f'- MODS DESCOBERTOS: {total} -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))

        if not total:
            print('Nenhum mod encontrado.\n')
            return

        valid_names = {mod.name for mod in report.valid_mods}
        loaded_names = {mod.name for mod in report.loaded_mods}
        failed_lookup = {mod.name: mod for mod in report.failed_mods}
        rejected_lookup = {mod.candidate.name: mod for mod in report.rejected_mods}
        priority_lookup = {mod.name: mod.priority for mod in report.valid_mods}
        version_lookup = {mod.name: mod.version for mod in report.valid_mods}

        for i, candidate in enumerate(report.discovered_mods, start=1):
            if candidate.name in loaded_names:
                status = 'carregado'
                reason = '-'
            elif candidate.name in failed_lookup:
                status = 'falhou ao aplicar'
                reason = failed_lookup[candidate.name].failure_reason or '-'
            elif candidate.name in rejected_lookup:
                status = 'rejeitado'
                reason = rejected_lookup[candidate.name].reason
            elif candidate.name in valid_names:
                status = 'válido'
                reason = '-'
            else:
                status = 'desconhecido'
                reason = '-'

            priority = priority_lookup.get(candidate.name, '-')
            version = version_lookup.get(candidate.name, 'desconhecida')
            print(
                f'{i} - {candidate.name} | status: {status} | versão: {version} '
                f'| prioridade: {priority} | motivo: {reason}'
            )
        print(f'\n')

    def menu_battle(self, stats_pl:tuple, stats_en:tuple):
        # Exibe o menu de batalha com os status do jogador e do inimigo.
        stats = f'- STATS: Player(Vida:{stats_pl[0]}, Poções:{stats_pl[1]}), Inimigo(Vida:{stats_en[0]}, Poções:{stats_en[1]}) -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        print('''
    1 - Atacar
    2 - Defender
    3 - Usar Poção (Recupera 50 de Vida)''')
        
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
