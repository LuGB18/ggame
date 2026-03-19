import unittest

from libs.battle import BattleSystem
from mods import loader


class ModLoaderTests(unittest.TestCase):
    def setUp(self):
        loader.reset_registry()

    def tearDown(self):
        loader.reset_registry()

    def test_before_and_after_patches_follow_deterministic_order(self):
        battle = BattleSystem()
        battle.new_battle()
        calls = []

        def before_high(*args, **kwargs):
            calls.append('before_high')

        def before_low(*args, **kwargs):
            calls.append('before_low')

        def after_low(result, *args, **kwargs):
            calls.append('after_low')
            return result - 1

        def after_high(result, *args, **kwargs):
            calls.append('after_high')
            return result - 10

        loader.register_patch('mod-before-high', 'before', 'libs.battle.BattleSystem.attack', 20, 'ignore', before_high)
        loader.register_patch('mod-before-low', 'before', 'libs.battle.BattleSystem.attack', 10, 'ignore', before_low)
        loader.register_patch('mod-after-low', 'after', 'libs.battle.BattleSystem.attack', 10, 'ignore', after_low)
        loader.register_patch('mod-after-high', 'after', 'libs.battle.BattleSystem.attack', 20, 'ignore', after_high)
        loader.apply_registered_patches()

        result = battle.attack('en')

        self.assertEqual(['before_low', 'before_high', 'after_high', 'after_low'], calls)
        self.assertEqual(79, result)

    def test_conflicting_replace_patch_is_rejected_and_recorded(self):
        battle = BattleSystem()
        battle.new_battle()

        def replace_one(self, who, next_fn=None):
            self.battle.HL_EN -= 30
            return self.battle.HL_EN

        def replace_two(self, who, next_fn=None):
            self.battle.HL_EN -= 99
            return self.battle.HL_EN

        loader.register_patch('mod-a', 'replace', 'libs.battle.BattleSystem.attack', 10, 'exclusive', replace_one)
        loader.register_patch('mod-b', 'replace', 'libs.battle.BattleSystem.attack', 20, 'exclusive', replace_two)
        loader.apply_registered_patches()

        result = battle.attack('en')
        report = loader.get_patch_report()['libs.battle.BattleSystem.attack']

        self.assertEqual(70, result)
        self.assertEqual('mod-a', report['replace'][0]['mod_id'])
        self.assertIn('mod-b', loader.FAILED_MODS)
        self.assertIn('conflitante', loader.FAILED_MODS['mod-b'][0]['reason'])

    def test_replace_chain_uses_next_fn(self):
        battle = BattleSystem()
        battle.new_battle()

        def replace_outer(self, who, next_fn=None):
            value = next_fn(self, who)
            return value - 5

        def replace_inner(self, who, next_fn=None):
            value = next_fn(self, who)
            return value - 7

        loader.register_patch('mod-outer', 'replace', 'libs.battle.BattleSystem.attack', 5, 'chain', replace_outer)
        loader.register_patch('mod-inner', 'replace', 'libs.battle.BattleSystem.attack', 15, 'chain', replace_inner)
        loader.apply_registered_patches()

        result = battle.attack('en')

        self.assertEqual(78, result)


if __name__ == '__main__':
    unittest.main()
