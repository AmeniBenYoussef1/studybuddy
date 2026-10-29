"""Infrastructure tests: the CDK stack synthesizes and has the expected safety settings.

Skipped automatically if aws-cdk-lib is not installed.
"""

import sys
import unittest
from pathlib import Path

try:
    import aws_cdk as cdk
    from aws_cdk.assertions import Match, Template
except ImportError:  # pragma: no cover
    cdk = None  # type: ignore[assignment]

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))


@unittest.skipIf(cdk is None, "aws-cdk-lib not installed")
class StackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from stacks.studybuddy_stack import StudyBuddyStack

        app = cdk.App()
        stack = StudyBuddyStack(app, "Test", allowed_user_ids="42", budget_email="test@example.com")
        cls.template = Template.from_stack(stack)

    def test_two_python_functions_on_arm(self) -> None:
        functions = self.template.find_resources(
            "AWS::Lambda::Function",
            {"Properties": {"Runtime": "python3.12", "Architectures": ["arm64"]}},
        )
        self.assertEqual(len(functions), 2)

    def test_queue_has_dead_letter_queue(self) -> None:
        self.template.has_resource_properties(
            "AWS::SQS::Queue",
            {"RedrivePolicy": Match.object_like({"maxReceiveCount": 3})},
        )

    def test_dedup_table_is_on_demand_with_ttl(self) -> None:
        self.template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "BillingMode": "PAY_PER_REQUEST",
                "TimeToLiveSpecification": {"AttributeName": "expires_at", "Enabled": True},
            },
        )

    def test_worker_reports_batch_failures(self) -> None:
        self.template.has_resource_properties(
            "AWS::Lambda::EventSourceMapping",
            {"FunctionResponseTypes": ["ReportBatchItemFailures"]},
        )

    def test_budget_and_dlq_alarm_exist(self) -> None:
        self.template.resource_count_is("AWS::Budgets::Budget", 1)
        self.template.resource_count_is("AWS::CloudWatch::Alarm", 1)

    def test_no_wildcard_actions_in_policies(self) -> None:
        for policy in self.template.find_resources("AWS::IAM::Policy").values():
            for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
                actions = statement["Action"]
                actions = actions if isinstance(actions, list) else [actions]
                self.assertNotIn("*", actions)


if __name__ == "__main__":
    unittest.main()
