import subprocess


class UI_Renderer:
    """
    UI_Renderer is a class responsible for rendering the user interface of the game in the console.
    """

    def clean_screen(self):
        subprocess.run('cls', shell=True)

    def main_menu(self):
        print('''
    ----------------------------
    -        Bem Vindo!        -
    ----------------------------
    
        1- Batalhar
        2- Mods
        3- Sair
              ''')

    def showmods(self, mods, patch_report=None, failed_mods=None):
        i = 1
        stats = f'- MODS CARREGADOS: {len(mods)} -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        for mod_name, mod_info in mods.items():
            print(f'{i} - {mod_name} (prioridade {mod_info["priority"]})')
            i += 1
        print('')

        patch_report = patch_report or {}
        report_title = f'- PATCHES ATIVOS POR ALVO: {len(patch_report)} -'
        print('-' * len(report_title))
        print(report_title)
        print('-' * len(report_title))
        if not patch_report:
            print('Nenhum patch ativo registrado.')
        for target, sections in patch_report.items():
            print(f'* {target}')
            has_any_patch = False
            for patch_type in ('before', 'replace', 'after'):
                patches = sections.get(patch_type, [])
                if not patches:
                    continue
                has_any_patch = True
                print(f'  - {patch_type}:')
                for patch in patches:
                    print(
                        f'    • {patch["mod_id"]} '
                        f'(prioridade {patch["priority"]}, conflito {patch["conflict_policy"]})'
                    )
            if not has_any_patch:
                print('  - sem patches ativos')
        print('')

        failed_mods = failed_mods or {}
        failed_title = f'- FALHAS DE MODS: {len(failed_mods)} -'
        print('-' * len(failed_title))
        print(failed_title)
        print('-' * len(failed_title))
        if not failed_mods:
            print('Nenhuma falha registrada.')
        for mod_name, failures in failed_mods.items():
            print(f'* {mod_name}')
            for failure in failures:
                print(f'  - alvo: {failure["target"]} | motivo: {failure["reason"]}')
        print('\n')

    def menu_battle(self, stats_pl: tuple, stats_en: tuple):
        stats = f'- STATS: Player(Vida:{stats_pl[0]}, Poções:{stats_pl[1]}), Inimigo(Vida:{stats_en[0]}, Poções:{stats_en[1]}) -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats))
        print('''
    1 - Atacar
    2 - Defender
    3 - Usar Poção (Recupera 50 de Vida)''')

    def show_defend(self, who, defended: bool):
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
                        stats = '- Você usou atacar! -'
                    case 'defend':
                        stats = '- Você usou Defender! -'
                    case 'potion':
                        stats = '- Você usou uma Poção! -'
            case 'en':
                match action:
                    case 'attack':
                        stats = '- o Inimigo usou atacar! -'
                    case 'defend':
                        stats = '- o Inimigo usou Defender! -'
                    case 'potion':
                        stats = '- o Inimigo uma Poção! -'
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

    def show_attack(self, who, DMG: int):
        match who:
            case 'pl':
                stats = f'- Você atacou e infrigiu:{DMG} de Dano! -'
            case 'en':
                stats = f'- o Inimigo atacou e infrigiu:{DMG} de Dano! -'
        print('-' * len(stats))
        print(stats)
        print('-' * len(stats) + f'\n')
