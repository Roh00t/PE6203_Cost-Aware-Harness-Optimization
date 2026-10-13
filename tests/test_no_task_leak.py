import tempfile
import unittest
from pathlib import Path

from scripts.check_no_task_leak import find_leaks


class TaskLeakTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path]:
        tasks = root / "benchmark" / "tasks"
        task_dir = tasks / "777-synthetic-task"
        task_dir.mkdir(parents=True)
        (task_dir / "task.toml").write_text(
            'schema_version = "1.1"\n[task]\nname = "synthetic"\n',
            encoding="utf-8",
        )
        (task_dir / "instruction.md").write_text(
            "Create `private-output.xlsx` from the input.\n",
            encoding="utf-8",
        )
        harness = root / "harness"
        harness.mkdir()
        (root / "configs" / "harness").mkdir(parents=True)
        return tasks, harness

    def test_clean_files_have_no_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks, harness = self.make_fixture(root)
            (harness / "agent.py").write_text("print('generic harness')\n", encoding="utf-8")
            (root / "agent_instructions.md").write_text("Work with the task's inputs.\n", encoding="utf-8")
            self.assertEqual(find_leaks(root, tasks), [])

    def test_task_id_and_instruction_filename_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks, harness = self.make_fixture(root)
            (harness / "agent.py").write_text(
                "task = '777-synthetic-task'\noutput = 'private-output.xlsx'\n",
                encoding="utf-8",
            )
            leaks = find_leaks(root, tasks)
            self.assertEqual({leak.kind for leak in leaks}, {"task ID", "instruction filename"})
            self.assertEqual({leak.value for leak in leaks}, {"777-synthetic-task", "private-output.xlsx"})

    def test_missing_task_sources_fail_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(FileNotFoundError, "TUA-Bench task sources not found"):
                find_leaks(root, root / "missing" / "tasks")

    def test_missing_instruction_fails_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / "tasks"
            task_dir = tasks / "777-synthetic-task"
            task_dir.mkdir(parents=True)
            (task_dir / "task.toml").write_text('[task]\nname = "synthetic"\n', encoding="utf-8")
            with self.assertRaisesRegex(FileNotFoundError, "Task instruction not found"):
                find_leaks(root, tasks)


if __name__ == "__main__":
    unittest.main()