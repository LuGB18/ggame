import tempfile
import textwrap
import unittest
from pathlib import Path

from libs.battle import BattleSystem
from mods import loader


class ModLoaderTests(unittest.TestCase):
    def setUp(self):
        loader.reset_registry()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mods_path = Path(self.temp_dir.name)
        self.original_folder = loader.MODS_FOLDER
        self.original_game_version = loader.GAME_VERSION
        self.original_loader_version = loader.LOADER_VERSION
        loader.MODS_FOLDER = self.mods_path
        loader.GAME_VERSION = '1.0.0'
        loader.LOADER_VERSION = '1.0.0'

    def tearDown(self):
        loader.MODS_FOLDER = self.original_folder
        loader.GAME_VERSION = self.original_game_version
        loader.LOADER_VERSION = self.original_loader_version
        loader.reset_registry()
        self.temp_dir.cleanup()

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

    def test_loads_file_mods_with_manifest_and_dependency_order(self):
        self._write_mod(
            'base_mod.py',
            """
            MOD_INFO = {
                "name": "Base Mod",
                "id": "base",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 50,
                "requires": [],
                "conflicts": [],
                "game_version": ">=1.0.0",
                "loader_version": ">=1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                order = globals().setdefault("APPLY_ORDER", [])
                order.append("base")
            """,
        )
        self._write_mod(
            'dependent_mod.py',
            """
            MOD_INFO = {
                "name": "Dependent Mod",
                "id": "dependent",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 1,
                "requires": ["base"],
                "conflicts": [],
                "game_version": ">=1.0.0",
                "loader_version": ">=1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                order = globals().setdefault("APPLY_ORDER", [])
                order.append("dependent")
            """,
        )

        loader.load_mods()

        self.assertEqual(list(loader.LOADED_MODS.keys()), ['base', 'dependent'])
        self.assertEqual(loader.FAILED_MODS, {})

    def test_rejects_duplicate_missing_dependency_conflict_and_version(self):
        self._write_mod(
            'first_dup.py',
            """
            MOD_INFO = {
                "name": "First Dup",
                "id": "dup",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 0,
                "requires": [],
                "conflicts": [],
                "game_version": "1.0.0",
                "loader_version": "1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                pass
            """,
        )
        self._write_mod(
            'second_dup.py',
            """
            MOD_INFO = {
                "name": "Second Dup",
                "id": "dup",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 1,
                "requires": [],
                "conflicts": [],
                "game_version": "1.0.0",
                "loader_version": "1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                pass
            """,
        )
        self._write_mod(
            'missing_dep.py',
            """
            MOD_INFO = {
                "name": "Missing Dep",
                "id": "missing_dep",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 2,
                "requires": ["unknown"],
                "conflicts": [],
                "game_version": "1.0.0",
                "loader_version": "1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                pass
            """,
        )
        self._write_mod(
            'conflict_a.py',
            """
            MOD_INFO = {
                "name": "Conflict A",
                "id": "conflict_a",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 3,
                "requires": [],
                "conflicts": ["conflict_b"],
                "game_version": "1.0.0",
                "loader_version": "1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                pass
            """,
        )
        self._write_mod(
            'conflict_b.py',
            """
            MOD_INFO = {
                "name": "Conflict B",
                "id": "conflict_b",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 4,
                "requires": [],
                "conflicts": [],
                "game_version": "1.0.0",
                "loader_version": "1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                pass
            """,
        )
        self._write_mod(
            'bad_version.py',
            """
            MOD_INFO = {
                "name": "Bad Version",
                "id": "bad_version",
                "version": "1.0.0",
                "author": "Tester",
                "priority": 5,
                "requires": [],
                "conflicts": [],
                "game_version": ">=2.0.0",
                "loader_version": "1.0.0",
                "entrypoint": "apply",
                "enabled": True,
            }

            def apply():
                pass
            """,
        )

        loader.load_mods()

        self.assertEqual(loader.LOADED_MODS, {})
        self.assertIn('dup', loader.FAILED_MODS)
        self.assertEqual(len(loader.FAILED_MODS['dup']), 2)
        self.assertIn('missing_dep', loader.FAILED_MODS)
        self.assertIn('conflict_a', loader.FAILED_MODS)
        self.assertIn('bad_version', loader.FAILED_MODS)

    def test_accepts_priority_fallback_for_simple_file_mod(self):
        self._write_mod(
            'legacy_mod.py',
            """
            PRIORITY = 7

            def apply():
                pass
            """,
        )

        loader.load_mods()

        self.assertIn('legacy_mod', loader.LOADED_MODS)
        self.assertEqual(loader.LOADED_MODS['legacy_mod']['priority'], 7)

    def _write_mod(self, relative_path, content):
        path = self.mods_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + '\n')


if __name__ == '__main__':
    unittest.main()
