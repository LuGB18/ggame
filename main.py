from libs.battle import BattleSystem
from libs.ui import UI_Renderer
from libs.goblin_ai import Goblin
from mods import loader

def batalha():
    """
    Executa o loop principal de batalha entre jogador e goblin.
    """
    BS.new_battle()  # Inicia nova batalha
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
                    UI.showmods(loader.LOADED_MODS)  # Mostra mods carregados
                    input('Pressione qualquer tecla para voltar ao menu')
                case 3:
                    exit()  # Sai do jogo
        except ValueError:
            pass
if __name__ == '__main__':
    loader.load_mods()  # Carrega mods
    BS = BattleSystem()  # Instancia sistema de batalha
    UI = UI_Renderer()  # Instancia UI
    render()  # Inicia loop principal
