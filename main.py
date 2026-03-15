from libs.battle import BattleSystem
from libs.ui import UI_Renderer
from libs.goblin_ai import Goblin
from mods import loader


def batalha():
    """
    Executes the main battle loop between the player and a goblin enemy.

    The function initializes a new battle, creates a Goblin instance with current enemy stats,
    and alternates turns between the player and the goblin until the battle is won.
    On the player's turn, presents a menu for actions: attack, defend, or use potion.
    On the goblin's turn, the goblin chooses an action automatically.
    After each action, updates stats, displays relevant UI feedback, and advances the round.
    At the end, displays the winner of the battle.

    Dependencies:
        - BS: Battle system module/object for managing battle state and actions.
        - Goblin: Class representing the enemy with methods for updating stats and making choices.
        - UI: User interface module/object for displaying menus, actions, and results.

    Side Effects:
        - Reads user input from the console.
        - Prints output to the console.
        - Waits for user input to proceed at various stages.
    """
    BS.new_battle()
    goblin = Goblin(BS.cur_stats('en'))
    while not BS.battle.IS_WON:
        UI.clean_screen()
        if BS.battle.CUR_ROUND == 'pl':
            UI.menu_battle(BS.cur_stats('pl'), BS.cur_stats('en'))
            try:
                uin = int(input('-> '))
                UI.clean_screen()
                match uin:
                    case 1:
                        BS.attack('en')
                        goblin.upd_stats(BS.cur_stats('en'))
                        UI.show_action('pl', 'attack')
                        input()
                        UI.clean_screen()
                        UI.show_attack('pl', BS.battle.ATK_PL)
                        input()
                        BS.next_round()
                    case 2:
                        res= BS.defend('pl')[0]
                        goblin.upd_stats(BS.cur_stats('en'))
                        UI.show_action('pl', 'defend')
                        input()
                        UI.clean_screen()
                        UI.show_defend('pl', res)
                        input()
                        BS.next_round()
                    case 3:
                        BS.use_potion('pl')
                        UI.show_action('pl', 'potion')
                        input()
                        UI.clean_screen()
                        UI.used_potion('pl')
                        input()
                        BS.next_round()
            except ValueError:
                pass
        else:
            UI.clean_screen()
            match goblin.mk_choice():
                case 'attack':
                    BS.attack('pl')
                    goblin.upd_stats(BS.cur_stats('en'))
                    UI.show_action('en', 'attack')
                    input()
                    UI.clean_screen()
                    UI.show_attack('en', BS.battle.ATK_EN)
                    input()
                    BS.next_round()
                case 'defend':
                    res = BS.defend('en')[0]
                    goblin.upd_stats(BS.cur_stats('en'))
                    UI.show_action('en', 'defend')
                    input()
                    UI.clean_screen()
                    UI.show_defend('en', res)
                    input()
                    BS.next_round()
                case 'potion':
                    BS.use_potion('en')
                    goblin.upd_stats(BS.cur_stats('en'))
                    UI.show_action('en', 'potion')
                    input()
                    UI.clean_screen()
                    UI.used_potion('en')
                    input()
                    BS.next_round()
    UI.clean_screen()
    UI.show_win(BS.battle.WHO_WON)
    input()

def render():
    while True:
        UI.clean_screen()
        UI.main_menu()
        uin = int(input())
        match uin:
            case 1:
                batalha()
            case 2:
                UI.showmods(loader.LOADED_MODS)
                input('Pressione qualquer tecla para voltar ao menu')
            case 3:
                exit()


if __name__ == '__main__':
    loader.load_mods()
    BS = BattleSystem()
    UI = UI_Renderer()
    render()
