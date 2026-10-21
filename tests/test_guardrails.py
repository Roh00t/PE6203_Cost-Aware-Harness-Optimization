import unittest

from harness.guardrails import check_command, check_extra_tool_calls


class GuardrailCommandTests(unittest.TestCase):
    def assert_rule(self, command: str, rule_id: str, message: str, *, c2: bool = False) -> None:
        result = check_command(command, c2_enabled=c2)
        self.assertEqual(result.rule_id, rule_id)
        self.assertTrue(result.blocked)
        self.assertEqual(result.message, message)

    def test_destructive_rules_block_and_allow_scoped_commands(self) -> None:
        cases = (
            ("rm -rf /", "G-DST-01", "rm -rf /tmp/build"),
            ("mkfs.ext4 /dev/sda", "G-DST-02", "dd if=/dev/zero of=/tmp/disk.img bs=1k count=1"),
            (":(){ :|:& };:", "G-DST-03", "kill -9 1234"),
            ("reboot", "G-DST-04", "echo restart later"),
            ("chmod -R 777 /", "G-DST-05", "chmod -R 700 /tmp/build"),
        )
        message = "BLOCKED [{rule_id}]: this command could destroy the environment and was not run. Delete or modify only the specific files the task requires."
        for blocked, rule_id, allowed in cases:
            with self.subTest(rule=rule_id):
                self.assert_rule(blocked, rule_id, message.format(rule_id=rule_id))
                self.assertEqual(check_command(allowed).action, "allow")
        for command in ("dd if=/dev/zero of=/dev/sda", "wipefs /dev/sda", "echo bad > /dev/sda"):
            with self.subTest(command=command):
                self.assertEqual(check_command(command).rule_id, "G-DST-02")
        for command in ("kill -9 -1", "pkill -9 -u root"):
            with self.subTest(command=command):
                self.assertEqual(check_command(command).rule_id, "G-DST-03")
        for command in ("systemctl poweroff", "init 0"):
            with self.subTest(command=command):
                self.assertEqual(check_command(command).rule_id, "G-DST-04")
        self.assertEqual(check_command("chown -R root / ").rule_id, "G-DST-05")

    def test_integrity_rule_blocks_and_allows_normal_paths(self) -> None:
        self.assert_rule(
            "cat /tests/secret.py",
            "G-INT-01",
            "BLOCKED [G-INT-01]: paths reserved for the benchmark's grader are not part of the task. Work only from the task's inputs.",
        )
        self.assertEqual(check_command("cat /tmp/input.txt").action, "allow")

    def test_secret_probe_is_logged_and_allowed(self) -> None:
        result = check_command("env")
        self.assertEqual((result.rule_id, result.action, result.message), ("G-SEC-01", "log", None))
        self.assertEqual(check_command("env", c2_enabled=True).action, "log")
        self.assertEqual(check_command("echo env | grep PATH").action, "allow")

    def test_c2_is_opt_in_and_strips_heredoc_bodies(self) -> None:
        self.assertEqual(check_command("vim file").action, "allow")
        result = check_command("vim file", c2_enabled=True)
        self.assertEqual(result.rule_id, "U-INT-01")
        self.assertEqual(result.message, "BLOCKED [U-INT-01]: 'vim' is interactive and would hang. Read with cat/head/sed -n, edit with sed, python, or cat <<'EOF' > file.")
        self.assertEqual(check_command("cat <<'EOF'\nvim is only text\nEOF", c2_enabled=True).action, "allow")
        self.assertEqual(check_command("cat <<EOF\n\tEOF\nvim file", c2_enabled=True).rule_id, "U-FMT-03")
        self.assertEqual(check_command("cat <<-EOF\n\tvim is only text\n\tEOF", c2_enabled=True).action, "allow")

    def test_interactive_rules_have_allowed_counterexamples(self) -> None:
        cases = (
            ("vim file", "cat file", "U-INT-01"),
            ("tail -f app.log", "tail -n 50 app.log", "U-INT-02"),
            ("python", "python -c 'print(1)'", "U-INT-03"),
            ("ssh host ls", "ssh -o BatchMode=yes host ls", "U-INT-04"),
        )
        for blocked, allowed, rule_id in cases:
            with self.subTest(rule=rule_id):
                result = check_command(blocked, c2_enabled=True)
                self.assertEqual(result.rule_id, rule_id)
                self.assertTrue(result.blocked)
                self.assertEqual(check_command(allowed, c2_enabled=True).action, "allow")

    def test_sudo_is_logged_not_blocked(self) -> None:
        # Dev review 2026-10-21: task containers grant passwordless sudo, so blocking it was a
        # false positive that rejected a correct `sudo useradd ...` command.
        result = check_command("sudo useradd -m charles && echo 'charles:pw' | sudo chpasswd", c2_enabled=True)
        self.assertEqual((result.rule_id, result.action, result.message), ("U-INT-05", "log", None))
        self.assertFalse(result.blocked)
        self.assertEqual(check_command("sudo -n apt update", c2_enabled=True).action, "allow")
        self.assertEqual(check_command("sudo apt update").action, "allow")  # C2 off: not checked
        # Logged last, so it never hides a blocking rule on the same command.
        self.assertEqual(check_command("sudo vim /etc/hosts", c2_enabled=True).rule_id, "U-INT-01")
        self.assertEqual(check_command("sudo ssh host ls", c2_enabled=True).rule_id, "U-INT-04")
        self.assertEqual(check_command("sudo rm -rf /", c2_enabled=True).rule_id, "G-DST-01")

    def test_c2_format_rules(self) -> None:
        cases = (
            ("", "U-FMT-01", "REJECTED [U-FMT-01]: empty command. Send one bash command."),
            ("x" * 8001, "U-FMT-02", "REJECTED [U-FMT-02]: command is 8001 characters (limit 8000). Write long content to a file with a heredoc across several steps."),
            ("cat <<'END'\nunfinished", "U-FMT-03", "REJECTED [U-FMT-03]: heredoc 'END' is never closed. End it with a line containing only END."),
            ("echo before && echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT", "U-FMT-04", "REJECTED [U-FMT-04]: submit on its own: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"),
        )
        for command, rule_id, message in cases:
            with self.subTest(rule=rule_id):
                self.assert_rule(command, rule_id, message, c2=True)
        self.assertEqual(check_command("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT", c2_enabled=True).action, "allow")
        self.assertEqual(check_command("x" * 8000, c2_enabled=True).action, "allow")
        self.assertEqual(check_command("echo ok", c2_enabled=True).action, "allow")
        self.assertEqual(check_command("cat <<'END'\ncontent\nEND", c2_enabled=True).action, "allow")

    def test_extra_tool_calls_are_not_blocked(self) -> None:
        self.assertIsNone(check_extra_tool_calls(1))
        result = check_extra_tool_calls(3)
        self.assertIsNotNone(result)
        self.assertEqual(result.rule_id, "U-FMT-05")
        self.assertEqual(result.action, "note")
        self.assertEqual(result.message, "NOTE: 2 extra tool call(s) were ignored; send one command per response.")
        with self.assertRaises(ValueError):
            check_extra_tool_calls(-1)


if __name__ == "__main__":
    unittest.main()