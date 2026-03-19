import unittest

from libs.battle import BattleSystem, ModContext


class BattleModApiTest(unittest.TestCase):
    def setUp(self):
        self.mod_context = ModContext()
        self.battle_system = BattleSystem(mod_context=self.mod_context)

    def test_mod_context_overrides_are_applied_to_new_battle(self):
        self.mod_context.set_attack_value('pl', 25)
        self.mod_context.set_defense_value('en', 9)
        self.mod_context.set_max_hp('pl', 150)
        self.mod_context.set_potion_heal_amount(30)

        self.battle_system.new_battle()

        self.assertEqual(self.battle_system.get_player_stats(), {
            'attack': 25,
            'defense': 5,
            'health': 100,
            'max_hp': 150,
            'potions': 3,
        })
        self.assertEqual(self.battle_system.get_enemy_stats(), {
            'attack': 10,
            'defense': 9,
            'health': 100,
            'max_hp': 100,
            'potions': 3,
        })
        self.assertEqual(self.battle_system.battle.POTION_HEAL_AMOUNT, 30)

    def test_setters_update_active_battle_state_without_internal_names(self):
        self.battle_system.new_battle()

        self.battle_system.set_attack_value('en', 17)
        self.battle_system.set_defense_value('pl', 8)
        self.battle_system.set_max_hp('en', 80)
        self.battle_system.set_potion_heal_amount(22)

        self.assertEqual(self.battle_system.get_enemy_stats()['attack'], 17)
        self.assertEqual(self.battle_system.get_player_stats()['defense'], 8)
        self.assertEqual(self.battle_system.get_enemy_stats()['max_hp'], 80)
        self.assertEqual(self.battle_system.battle.HL_EN, 80)
        self.assertEqual(self.battle_system.battle.POTION_HEAL_AMOUNT, 22)

    def test_registered_battle_rules_run_during_battle_events(self):
        calls = []

        def buff_player_attack(mod_context, **payload):
            calls.append(payload['target'])
            mod_context.set_attack_value('pl', 15)

        self.mod_context.register_battle_rule('before_attack', buff_player_attack)
        self.battle_system.new_battle()

        remaining_health = self.battle_system.attack('en')

        self.assertEqual(calls, ['en'])
        self.assertEqual(remaining_health, 85)
        self.assertEqual(self.battle_system.get_player_stats()['attack'], 15)


if __name__ == '__main__':
    unittest.main()
