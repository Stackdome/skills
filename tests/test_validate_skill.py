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
        Before the exact `docker push ttl.sh/stackdome-a1b2c3:1h`, explain that its public registry can expose image contents, warn the user, and get explicit confirmation.
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
        text = "Before the exact docker push to ttl.sh, warn the user and get explicit confirmation."

        errors = validate_skill.global_policy_errors(text)

        self.assertIn("ttl.sh", "\n".join(errors))

    def test_rejects_git_push_as_a_ttl_image_publication_instruction(self):
        text = "Before the exact `git push ttl.sh/stackdome-a1b2c3:1h`, explain that its public registry can expose image contents, warn the user, and get explicit confirmation."

        errors = validate_skill.global_policy_errors(text)

        self.assertIn("ttl.sh", "\n".join(errors))

    def test_rejects_git_push_even_when_the_oci_push_policy_is_present(self):
        text = """
        Stackdome Cloud custom-domain registration is disabled; custom domains are self-hosted only.
        Cloud limits do not apply to self-hosted instances.
        Before the exact `docker push ttl.sh/stackdome-a1b2c3:1h`, explain that its public registry can expose image contents, warn the user, and get explicit confirmation.
        Use a documented CLI command first; use stackdome api only for a documented endpoint without a CLI command.
        If Docker is unavailable, run `git push ttl.sh/stackdome-a1b2c3:1h` instead.
        """

        errors = validate_skill.global_policy_errors(text)

        self.assertIn("Git push", "\n".join(errors))

    def test_rejects_ttl_before_git_push_as_an_image_publication_instruction(self):
        text = "For ttl.sh publication, run git push with the exact image reference."

        errors = validate_skill.global_policy_errors(text)

        self.assertIn("Git push", "\n".join(errors))

    def test_rejects_reversed_git_push_wording_with_a_valid_oci_policy(self):
        text = """
        Stackdome Cloud custom-domain registration is disabled; custom domains are self-hosted only.
        Cloud limits do not apply to self-hosted instances.
        Before the exact `docker push ttl.sh/stackdome-a1b2c3:1h`, explain that its public registry can expose image contents, warn the user, and get explicit confirmation.
        Use a documented CLI command first; use stackdome api only for a documented endpoint without a CLI command.
        For ttl.sh publication, run git push with the exact image reference.
        """

        errors = validate_skill.global_policy_errors(text)

        self.assertEqual(
            errors,
            ["Git push cannot publish an OCI image to ttl.sh; require docker push"],
        )

    def test_rejects_git_push_before_ttl_across_punctuation_on_one_line(self):
        text = """
        Stackdome Cloud custom-domain registration is disabled; custom domains are self-hosted only.
        Cloud limits do not apply to self-hosted instances.
        Before the exact `docker push ttl.sh/stackdome-a1b2c3:1h`, explain that its public registry can expose image contents, warn the user, and get explicit confirmation.
        Use a documented CLI command first; use stackdome api only for a documented endpoint without a CLI command.
        Run git push. Publish the image to ttl.sh.
        """

        errors = validate_skill.global_policy_errors(text)

        self.assertEqual(
            errors,
            ["Git push cannot publish an OCI image to ttl.sh; require docker push"],
        )

    def test_rejects_ttl_before_git_push_across_punctuation_on_one_line(self):
        text = """
        Stackdome Cloud custom-domain registration is disabled; custom domains are self-hosted only.
        Cloud limits do not apply to self-hosted instances.
        Before the exact `docker push ttl.sh/stackdome-a1b2c3:1h`, explain that its public registry can expose image contents, warn the user, and get explicit confirmation.
        Use a documented CLI command first; use stackdome api only for a documented endpoint without a CLI command.
        Use ttl.sh for publication. Run git push with the image reference.
        """

        errors = validate_skill.global_policy_errors(text)

        self.assertEqual(
            errors,
            ["Git push cannot publish an OCI image to ttl.sh; require docker push"],
        )


class CloudQuotaTests(unittest.TestCase):
    def test_rejects_numeric_cloud_resource_claims_without_hard_coded_limits(self):
        for guidance in (
            "Stackdome Cloud supports only 3 apps.",
            "Cloud supports only 3 active apps.",
            "Cloud allows up to 3 running apps.",
        ):
            with self.subTest(guidance=guidance):
                errors = validate_skill.cloud_quota_errors(guidance)

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
            "Never ask for a user's password, but accept a password if offered.",
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
            "Never ask for a password or accept it.",
            "Never ask for a password, nor accept it.",
            "Never ask for a password and never accept it.",
            "Use an API token, not a password.",
            "Without storing passwords, use an API token.",
        ):
            with self.subTest(guidance=guidance):
                self.assertEqual(validate_skill.password_guidance_errors(guidance), [])

    def test_rejects_an_unnegated_action_after_the_password_referent(self):
        guidance = "Never ask for a user’s password and accept it."

        self.assertEqual(len(validate_skill.password_guidance_errors(guidance)), 1)


if __name__ == "__main__":
    unittest.main()
