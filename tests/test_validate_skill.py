import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import validate_skill


class GlobalPolicyTests(unittest.TestCase):
    def test_accepts_the_required_skill_level_policies_together(self):
        text = """
        Stackdome Cloud custom-domain registration is disabled; custom domains are self-hosted only.
        Cloud limits do not apply to self-hosted instances.
        Before the exact `git push registry.example/app:latest` to ttl.sh, explain that its public registry can expose image contents, warn the user, and get explicit confirmation.
        Use a documented CLI command first; use stackdome api only for a documented endpoint without a CLI command.
        """

        self.assertEqual(validate_skill.global_policy_errors(text), [])

    def test_reports_each_missing_skill_level_policy(self):
        errors = validate_skill.global_policy_errors("Deploy with Stackdome.")

        self.assertEqual(len(errors), 4)
        self.assertIn("Cloud custom-domain registration", "\n".join(errors))
        self.assertIn("Cloud limits", "\n".join(errors))
        self.assertIn("ttl.sh", "\n".join(errors))
        self.assertIn("CLI-first", "\n".join(errors))

    def test_rejects_a_generic_ttl_warning_without_privacy_or_security_risk(self):
        text = "Before the exact git push to ttl.sh, warn the user and get explicit confirmation."

        errors = validate_skill.global_policy_errors(text)

        self.assertIn("ttl.sh", "\n".join(errors))


class CloudQuotaTests(unittest.TestCase):
    def test_rejects_numeric_cloud_resource_claims_without_hard_coded_limits(self):
        errors = validate_skill.cloud_quota_errors("Stackdome Cloud supports only 3 apps.")

        self.assertEqual(len(errors), 1)
        self.assertIn("numeric Cloud quota", errors[0])

    def test_allows_non_cloud_capacity_requirements(self):
        self.assertEqual(
            validate_skill.cloud_quota_errors("Self-hosted installations need 2 CPU and 4 GB RAM."),
            [],
        )

    def test_allows_a_non_quota_cloud_migration_instruction(self):
        self.assertEqual(
            validate_skill.cloud_quota_errors("Migrate the Cloud deployment to 3 replicas."),
            [],
        )

    def test_allows_exact_replica_count_for_cloud_testing(self):
        self.assertEqual(
            validate_skill.cloud_quota_errors("For Cloud testing, use exactly 3 replicas."),
            [],
        )


class PasswordGuidanceTests(unittest.TestCase):
    def test_rejects_guidance_to_handle_a_users_password(self):
        for guidance in (
            "Ask the user for their password.",
            "Accept the user's password.",
            "Paste the user's password into the prompt.",
            "Store the user's password.",
            "Use the user's password to sign in.",
            "Ask the user to type their password.",
            "Enter the user's password.",
            "Provide the user's password to the CLI.",
            "Supply the user's password.",
            "Handle the user's password.",
            "Solicit the user's password.",
            "Never ask for a user's password, but accept it if offered.",
            "Never ask for their password, yet accept it if offered.",
            "Do not lose the user's password; store it safely.",
            "Accept users’ passwords.",
        ):
            with self.subTest(guidance=guidance):
                self.assertEqual(len(validate_skill.password_guidance_errors(guidance)), 1)

    def test_allows_explicit_password_prohibitions(self):
        for guidance in (
            "Never ask for a user's password.",
            "Never ask for, accept, or store a password.",
            "Use an API token, not a password.",
            "Without storing passwords, use an API token.",
        ):
            with self.subTest(guidance=guidance):
                self.assertEqual(validate_skill.password_guidance_errors(guidance), [])


if __name__ == "__main__":
    unittest.main()
