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
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.use_potion.before', event_payload)

        result = None
        if who == _PLAYER and self.battle.POTIONS_PL >= 1:
            self.battle.POTIONS_PL -= 1
            self.battle.HL_PL = min(
                self.battle.HL_PL + self.battle.POTION_HEAL_AMOUNT,
                self.battle.PLAYER_MAX_HP,
            )
            result = self.battle.HL_PL
        elif who == _ENEMY and self.battle.POTIONS_EN >= 1:
            self.battle.POTIONS_EN -= 1
            self.battle.HL_EN = min(
                self.battle.HL_EN + self.battle.POTION_HEAL_AMOUNT,
                self.battle.ENEMY_MAX_HP,
            )
            result = self.battle.HL_EN

        if result is not None:
            self.mod_context.run_battle_rules('after_use_potion', battle_system=self, side=who)

        loader.trigger_hooks('battle.use_potion.after', {**event_payload, 'result': result})
        return result

    def cur_stats(self, who) -> tuple:
        if who == _PLAYER:
            return (self.battle.HL_PL, self.battle.POTIONS_PL)
        if who == _ENEMY:
            return (self.battle.HL_EN, self.battle.POTIONS_EN)
        return (0, 1)

    def all_stats(self) -> tuple:
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
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.defend.before', event_payload)

        defended = choice([True, False])
        if who == _PLAYER:
            attacker_field = 'ATK_EN'
            defense_value = self.battle.DEF_PL
        elif who == _ENEMY:
            attacker_field = 'ATK_PL'
            defense_value = self.battle.DEF_EN
        else:
            result = (False, 0)
            loader.trigger_hooks('battle.defend.after', {**event_payload, 'result': result})
            return result

        original_attack = getattr(self.battle, attacker_field)
        if defended:
            setattr(self.battle, attacker_field, max(0, original_attack - defense_value))

        life = self.attack(who)
        setattr(self.battle, attacker_field, original_attack)

        result = (defended, life)
        self.mod_context.run_battle_rules(
            'after_defend',
            battle_system=self,
            side=who,
            success=defended,
            remaining_health=life,
        )
        loader.trigger_hooks('battle.defend.after', {**event_payload, 'result': result})
        return result

    def attack(self, who):
        event_payload = {'battle_system': self, 'who': who}
        loader.trigger_hooks('battle.attack.before', event_payload)
        self.mod_context.run_battle_rules('before_attack', battle_system=self, target=who)

        if who == _PLAYER:
            self.battle.HL_PL -= self.battle.ATK_EN
            result = self.battle.HL_PL
        elif who == _ENEMY:
            self.battle.HL_EN -= self.battle.ATK_PL
            result = self.battle.HL_EN
        else:
            result = None

        if result is not None and result <= 0:
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
        if self.battle.CUR_ROUND == _PLAYER:
            self.battle.CUR_ROUND = _ENEMY
        else:
            self.battle.CUR_ROUND = _PLAYER
        self.mod_context.run_battle_rules(
            'after_round_change',
            battle_system=self,
            current_round=self.battle.CUR_ROUND,
        )
        return self.battle.CUR_ROUND
