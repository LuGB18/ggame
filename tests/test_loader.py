import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mods import loader
from libs.ui import UI_Renderer


class LoaderTests(unittest.TestCase):
    def create_mod_file(self, folder: Path, name: str, body: str) -> None:
        (folder / f"{name}.py").write_text(body)

    def test_discover_validate_and_apply_mods_with_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods_folder = Path(tmp)
            self.create_mod_file(
                mods_folder,
                'alpha',
                "PRIORITY = 2\nVERSION = '1.0.0'\n"
                "def apply(ctx=None):\n"
                "    ctx.append('alpha')\n",
            )
            self.create_mod_file(
                mods_folder,
                'beta',
                "PRIORITY = 1\nVERSION = '2.0.0'\n"
                "def apply(ctx=None):\n"
                "    ctx.append('beta')\n",
            )
            self.create_mod_file(
                mods_folder,
                'broken',
                "def noop():\n"
                "    return None\n",
            )
            self.create_mod_file(
                mods_folder,
                'failing',
                "PRIORITY = 3\nVERSION = '9.9.9'\n"
                "def apply(ctx=None):\n"
                "    raise RuntimeError('boom')\n",
            )

            ctx = []
            report = loader.load_mods(mods_folder=mods_folder, ctx=ctx)

            self.assertEqual([candidate.name for candidate in report.discovered_mods], ['alpha', 'beta', 'broken', 'failing'])
            self.assertEqual([mod.name for mod in report.valid_mods], ['alpha', 'beta', 'failing'])
            self.assertEqual([mod.name for mod in report.loaded_mods], ['beta', 'alpha'])
            self.assertEqual([mod.name for mod in report.failed_mods], ['failing'])
            self.assertEqual([mod.candidate.name for mod in report.rejected_mods], ['broken'])
            self.assertEqual(ctx, ['beta', 'alpha'])
            self.assertEqual(sorted(loader.LOADED_MODS), ['alpha', 'beta'])

    def test_showmods_displays_status_version_priority_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods_folder = Path(tmp)
            self.create_mod_file(
                mods_folder,
                'ok_mod',
                "PRIORITY = 4\nVERSION = '1.2.3'\n"
                "def apply(ctx=None):\n"
                "    return None\n",
            )
            self.create_mod_file(
                mods_folder,
                'bad_mod',
                "def nope():\n"
                "    return None\n",
            )
            report = loader.load_mods(mods_folder=mods_folder, ctx={})
            ui = UI_Renderer()

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                ui.showmods(report)

            output = buffer.getvalue()
            self.assertIn('ok_mod | status: carregado | versão: 1.2.3 | prioridade: 4 | motivo: -', output)
            self.assertIn('bad_mod | status: rejeitado | versão: desconhecida | prioridade: - | motivo: mod sem função', output)


if __name__ == '__main__':
    unittest.main()
