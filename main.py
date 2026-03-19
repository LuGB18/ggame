from libs.battle import BattleSystem
from libs.ui import UI_Renderer
from libs.goblin_ai import Goblin
from mods import loader
import libs.battle as battle_module
import libs.ui as ui_module
import sys

BS = None
UI = None
GAME_CONTEXT = {}

def batalha():
    """
    Executa o loop principal de batalha entre jogador e goblin.
    """
    BS.new_battle()  # Inicia nova batalha
    loader.trigger_hooks('battle.lifecycle.start', {'battle_system': BS, 'ui_renderer': UI, 'game_context': GAME_CONTEXT})
    goblin = Goblin(BS.cur_stats('en'))  # Cria instância do goblin com stats atuais
    while not BS.battle.IS_WON:  # Continua até alguém vencer
        UI.clean_screen()  # Limpa tela
        if BS.battle.CUR_ROUND == 'pl':  # Turno do jogador
            UI.menu_battle(BS.cur_stats('pl'), BS.cur_stats('en'))  # Mostra menu de batalha
            try:
                uin = int(input('-> '))  # Lê ação do jogador
                UI.clean_screen()
                match uin:
                    case 1:  # Atacar
                        BS.attack('en')  # Jogador ataca inimigo
                        goblin.upd_stats(BS.cur_stats('en'))  # Atualiza stats do goblin
                        UI.show_action('pl', 'attack')  # Mostra ação
                        input()
                        UI.clean_screen()
                        UI.show_attack('pl', BS.battle.ATK_PL)  # Mostra resultado do ataque
                        input()
                        BS.next_round()  # Passa turno
                    case 2:  # Defender
                        res= BS.defend('pl')[0]  # Jogador defende
                        goblin.upd_stats(BS.cur_stats('en'))
                        UI.show_action('pl', 'defend')
                        input()
                        UI.clean_screen()
                        UI.show_defend('pl', res)  # Mostra resultado da defesa
                        input()
                        BS.next_round()
                    case 3:  # Usar poção
                        BS.use_potion('pl')  # Jogador usa poção
                        UI.show_action('pl', 'potion')
                        input()
                        UI.clean_screen()
                        UI.used_potion('pl')  # Mostra uso da poção
                        input()
                        BS.next_round()
            except ValueError:
                pass  # Ignora entradas inválidas
        else:  # Turno do goblin
            UI.clean_screen()
            match goblin.mk_choice():  # Goblin escolhe ação
                case 'attack':
                    BS.attack('pl')  # Goblin ataca jogador
                    goblin.upd_stats(BS.cur_stats('en'))
                    UI.show_action('en', 'attack')
                    input()
                    UI.clean_screen()
                    UI.show_attack('en', BS.battle.ATK_EN)
                    input()
                    BS.next_round()
                case 'defend':
                    res = BS.defend('en')[0]  # Goblin defende
                    goblin.upd_stats(BS.cur_stats('en'))
                    UI.show_action('en', 'defend')
                    input()
                    UI.clean_screen()
                    UI.show_defend('en', res)
                    input()
                    BS.next_round()
                case 'potion':
                    BS.use_potion('en')  # Goblin usa poção
                    goblin.upd_stats(BS.cur_stats('en'))
                    UI.show_action('en', 'potion')
                    input()
                    UI.clean_screen()
                    UI.used_potion('en')
                    input()
                    BS.next_round()
    UI.clean_screen()
    UI.show_win(BS.battle.WHO_WON)  # Mostra vencedor
    loader.trigger_hooks('battle.lifecycle.end', {'battle_system': BS, 'ui_renderer': UI, 'game_context': GAME_CONTEXT, 'winner': BS.battle.WHO_WON})
    input()

def render():
    while True:
        UI.clean_screen()  # Limpa tela
        UI.main_menu()  # Mostra menu principal
        try:
            uin = int(input())  # Lê opção do usuário
            match uin:
                case 1:
                    batalha()  # Inicia batalha
                case 2:
                    UI.showmods(loader.LOAD_REPORT)  # Mostra mods carregados
                    UI.showmods(loader.LOADED_MODS, loader.get_patch_report(), loader.FAILED_MODS)  # Mostra mods carregados
                    input('Pressione qualquer tecla para voltar ao menu')
                case 3:
                    exit()  # Sai do jogo
        except ValueError:
            pass
if __name__ == '__main__':
    BS = BattleSystem()  # Instancia sistema de batalha
    UI = UI_Renderer()  # Instancia UI
    GAME_CONTEXT = {
        'battle_system': BS,
        'ui_renderer': UI,
        'goblin_class': Goblin,
        'shared_state': {},
        'modules': {
            'battle': battle_module,
            'ui': ui_module,
            'loader': loader,
            'main': sys.modules[__name__],
        },
        'main_module': sys.modules[__name__],
        'battle_module': battle_module,
        'ui_module': ui_module,
        'loader_module': loader,
    }
    loader.load_mods(GAME_CONTEXT)  # Carrega mods
    render()  # Inicia loop principal
