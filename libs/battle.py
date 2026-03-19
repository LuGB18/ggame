from random import choice

from mods import loader

from .variables import BattleState

_PLAYER = 'pl'
_ENEMY = 'en'
_ATTACK_FIELDS = {_PLAYER: 'ATK_PL', _ENEMY: 'ATK_EN'}
_DEFENSE_FIELDS = {_PLAYER: 'DEF_PL', _ENEMY: 'DEF_EN'}
_HP_FIELDS = {_PLAYER: 'HL_PL', _ENEMY: 'HL_EN'}
_MAX_HP_FIELDS = {_PLAYER: 'PLAYER_MAX_HP', _ENEMY: 'ENEMY_MAX_HP'}
_POTION_FIELDS = {_PLAYER: 'POTIONS_PL', _ENEMY: 'POTIONS_EN'}
_WINNER_BY_TARGET = {_PLAYER: _ENEMY, _ENEMY: _PLAYER}


class ModContext:
    """
    Expõe uma API estável para mods alterarem regras e atributos de batalha.
    """

    def __init__(self) -> None:
        self._battle_state: BattleState | None = None
        self._base_values = {
            'ATK_PL': 10,
            'ATK_EN': 10,
            'DEF_PL': 5,
            'DEF_EN': 5,
            'HL_PL': 100,
            'HL_EN': 100,
            'POTIONS_PL': 3,
            'POTIONS_EN': 3,
            'POTION_HEAL_AMOUNT': 50,
            'PLAYER_MAX_HP': 100,
            'ENEMY_MAX_HP': 100,
            'IS_WON': False,
            'WHO_WON': '',
            'CUR_ROUND': _PLAYER,
        }
        self._battle_rules: dict[str, list] = {}

    def attach_battle_state(self, battle_state: BattleState) -> None:
        self._battle_state = battle_state

    def build_battle_state(self) -> BattleState:
        battle_state = BattleState(self._base_values)
        self.attach_battle_state(battle_state)
        return battle_state

    def _validate_side(self, side: str) -> None:
        if side not in (_PLAYER, _ENEMY):
            raise ValueError("side must be 'pl' or 'en'")

    def _current_or_base_value(self, field_name: str):
        if self._battle_state is not None:
            return getattr(self._battle_state, field_name)
        return self._base_values[field_name]

    def _set_current_and_base_value(self, field_name: str, value) -> None:
        self._base_values[field_name] = value
        if self._battle_state is not None:
            setattr(self._battle_state, field_name, value)

    def _stats_for_side(self, side: str) -> dict:
        self._validate_side(side)
        return {
            'attack': self._current_or_base_value(_ATTACK_FIELDS[side]),
            'defense': self._current_or_base_value(_DEFENSE_FIELDS[side]),
            'health': self._current_or_base_value(_HP_FIELDS[side]),
            'max_hp': self._current_or_base_value(_MAX_HP_FIELDS[side]),
            'potions': self._current_or_base_value(_POTION_FIELDS[side]),
        }

    def get_player_stats(self) -> dict:
        return self._stats_for_side(_PLAYER)

    def get_enemy_stats(self) -> dict:
        return self._stats_for_side(_ENEMY)

    def set_attack_value(self, side: str, value: int) -> None:
        self._validate_side(side)
        self._set_current_and_base_value(_ATTACK_FIELDS[side], value)

    def set_defense_value(self, side: str, value: int) -> None:
        self._validate_side(side)
        self._set_current_and_base_value(_DEFENSE_FIELDS[side], value)

    def set_max_hp(self, side: str, value: int) -> None:
        self._validate_side(side)
        self._set_current_and_base_value(_MAX_HP_FIELDS[side], value)
        hp_field = _HP_FIELDS[side]
        current_hp = self._current_or_base_value(hp_field)
        if current_hp > value:
            self._set_current_and_base_value(hp_field, value)

    def set_potion_heal_amount(self, value: int) -> None:
        self._set_current_and_base_value('POTION_HEAL_AMOUNT', value)

    def register_battle_rule(self, name: str, callback) -> None:
        self._battle_rules.setdefault(name, []).append(callback)

    def run_battle_rules(self, name: str, **payload) -> None:
        for callback in self._battle_rules.get(name, []):
            callback(self, **payload)


MOD_CONTEXT = ModContext()


class BattleSystem:
    """
    BattleSystem gerencia a lógica e transições de estado para uma batalha por turnos entre jogador e inimigo.
    """

    battle: BattleState

    def __init__(self, mod_context: ModContext | None = None) -> None:
        self.mod_context = mod_context or MOD_CONTEXT

    def new_battle(self):
        # Inicializa um novo estado de batalha
        self.battle = self.mod_context.build_battle_state()
        self.mod_context.run_battle_rules('new_battle', battle_system=self)

    def get_player_stats(self) -> dict:
        return self.mod_context.get_player_stats()

    def get_enemy_stats(self) -> dict:
        return self.mod_context.get_enemy_stats()

    def set_attack_value(self, side: str, value: int) -> None:
        self.mod_context.set_attack_value(side, value)

    def set_defense_value(self, side: str, value: int) -> None:
        self.mod_context.set_defense_value(side, value)

    def set_max_hp(self, side: str, value: int) -> None:
        self.mod_context.set_max_hp(side, value)

    def set_potion_heal_amount(self, value: int) -> None:
        self.mod_context.set_potion_heal_amount(value)

    def register_battle_rule(self, name: str, callback) -> None:
        self.mod_context.register_battle_rule(name, callback)

    def use_potion(self, who):
        # Usa uma poção para o jogador ('pl') ou inimigo ('en')
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.use_potion.before', event_payload)
        result = None
        match who:
            case 'pl':
                if self.battle.POTIONS_PL >= 1:
                    self.battle.POTIONS_PL -= 1
                    # Cura até o máximo de HP permitido
                    self.battle.HL_PL = min(
                        self.battle.PLAYER_MAX_HP,
                        self.battle.HL_PL + self.battle.POTION_HEAL_AMOUNT,
                    )
                    result = self.battle.HL_PL
            case 'en':
                if self.battle.POTIONS_EN >= 1:
                    self.battle.POTIONS_EN -= 1
                    # Cura até o máximo de HP permitido
                    self.battle.HL_EN = min(
                        self.battle.ENEMY_MAX_HP,
                        self.battle.HL_EN + self.battle.POTION_HEAL_AMOUNT,
                    )
                    result = self.battle.HL_EN

        if result is not None:
            self.mod_context.run_battle_rules('after_use_potion', battle_system=self, side=who)
        loader.trigger_hooks('battle.use_potion.after', {**event_payload, 'result': result})
        return result

    def cur_stats(self, who) -> tuple:
        # Retorna HP e poções atuais do jogador ('pl') ou inimigo ('en')
        match who:
            case 'pl':
                return (self.battle.HL_PL, self.battle.POTIONS_PL)
            case 'en':
                return (self.battle.HL_EN, self.battle.POTIONS_EN)
        return (0, 1)

    def all_stats(self) -> tuple:
        # Retorna todos os atributos relevantes de ambos os lados
        return (
            self.battle.ATK_PL,
            self.battle.DEF_PL,
            self.battle.HL_PL,
            self.battle.POTIONS_PL,
            self.battle.ATK_EN,
            self.battle.DEF_EN,
            self.battle.HL_EN,
            self.battle.POTIONS_EN,
        )

    def defend(self, who):
        # Simula ação de defesa para jogador ('pl') ou inimigo ('en')
        # Retorna se defesa foi bem-sucedida e HP atualizado
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.defend.before', event_payload)
        defended = choice([True, False])

        if who == 'pl':
            attack_field = 'ATK_EN'
            defense_value = self.battle.DEF_PL
        elif who == 'en':
            attack_field = 'ATK_PL'
            defense_value = self.battle.DEF_EN
        else:
            result = (True, 0)
            loader.trigger_hooks('battle.defend.after', {**event_payload, 'result': result})
            return result

        if defended:
            original_attack = getattr(self.battle, attack_field)
            setattr(self.battle, attack_field, max(0, original_attack - defense_value))
            remaining_health = self.attack(who)
            setattr(self.battle, attack_field, original_attack)
        else:
            remaining_health = self.attack(who)

        result = (defended, remaining_health)
        self.mod_context.run_battle_rules(
            'after_defend',
            battle_system=self,
            side=who,
            success=defended,
            remaining_health=remaining_health,
        )
        loader.trigger_hooks('battle.defend.after', {**event_payload, 'result': result})
        return result

    def attack(self, who):
        # Aplica ataque ao jogador ('pl') ou inimigo ('en')
        # Atualiza estado de vitória se HP chegar a zero
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.attack.before', event_payload)
        self.mod_context.run_battle_rules('before_attack', battle_system=self, target=who)

        if who == 'pl':
            self.battle.HL_PL -= self.battle.ATK_EN
            result = self.battle.HL_PL
        elif who == 'en':
            self.battle.HL_EN -= self.battle.ATK_PL
            result = self.battle.HL_EN
        else:
            result = None

        if who in _WINNER_BY_TARGET and result is not None and result <= 0:
            self.battle.IS_WON = True
            self.battle.WHO_WON = _WINNER_BY_TARGET[who]

        if result is not None:
            self.mod_context.run_battle_rules(
                'after_attack',
                battle_system=self,
                target=who,
                remaining_health=result,
            )
        loader.trigger_hooks('battle.attack.after', {**event_payload, 'result': result})
        return result

    def next_round(self):
        # Alterna o turno entre jogador ('pl') e inimigo ('en')
        if self.battle.CUR_ROUND == 'pl':
            self.battle.CUR_ROUND = 'en'
            self.mod_context.run_battle_rules('after_round_change', battle_system=self, current_round='en')
            return 'en'
        self.battle.CUR_ROUND = 'pl'
        self.mod_context.run_battle_rules('after_round_change', battle_system=self, current_round='pl')
        return 'pl'
