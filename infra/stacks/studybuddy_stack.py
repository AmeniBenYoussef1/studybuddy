"""StudyBuddy week-1 infrastructure.

Telegram -> API Gateway (HTTP API) -> webhook Lambda -> SQS -> worker Lambda -> Telegram

Everything is serverless and pay-per-use, so the idle cost is close to $0
(the only fixed cost is the Secrets Manager secret, about $0.40/month).
"""

from __future__ import annotations

from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as event_sources
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_sqs as sqs
from constructs import Construct

SRC_DIR = str(Path(__file__).resolve().parents[2] / "src")

WORKER_TIMEOUT = Duration.seconds(60)


class StudyBuddyStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        allowed_user_ids: str,
        budget_email: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)  # type: ignore[arg-type]

        # --- Secrets: bot token (set by you after deploy) + generated webhook secret ---
        telegram_secret = secretsmanager.Secret(
            self,
            "TelegramSecret",
            description="StudyBuddy Telegram bot token and webhook secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"bot_token": "REPLACE_ME"}',  # noqa: S106 placeholder, set after deploy
                generate_string_key="webhook_secret",
                # Telegram only allows A-Z, a-z, 0-9, _ and - in the secret token.
                exclude_punctuation=True,
                password_length=48,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- Queue with dead-letter queue ---
        dlq = sqs.Queue(
            self,
            "DeadLetterQueue",
            retention_period=Duration.days(14),
            enforce_ssl=True,
        )
        queue = sqs.Queue(
            self,
            "MessageQueue",
            # Must be >= 6x the worker timeout (AWS recommendation for Lambda consumers).
            visibility_timeout=Duration.seconds(WORKER_TIMEOUT.to_seconds() * 6),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
            enforce_ssl=True,
        )

        # --- Deduplication table (Telegram/SQS can deliver twice) ---
        dedup_table = dynamodb.Table(
            self,
            "ProcessedUpdates",
            partition_key=dynamodb.Attribute(name="update_id", type=dynamodb.AttributeType.NUMBER),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.DESTROY,
        )

        common = {
            "runtime": lambda_.Runtime.PYTHON_3_12,
            "architecture": lambda_.Architecture.ARM_64,
            "code": lambda_.Code.from_asset(SRC_DIR, exclude=["**/__pycache__", "**/*.pyc"]),
            "memory_size": 256,
            "log_retention": logs.RetentionDays.TWO_WEEKS,
        }

        # --- Webhook Lambda: verify, filter, enqueue, answer fast ---
        webhook_fn = lambda_.Function(
            self,
            "WebhookFunction",
            handler="webhook.handler.handler",
            timeout=Duration.seconds(10),
            environment={
                "TELEGRAM_SECRET_ARN": telegram_secret.secret_arn,
                "QUEUE_URL": queue.queue_url,
                "ALLOWED_USER_IDS": allowed_user_ids,
            },
            **common,  # type: ignore[arg-type]
        )
        telegram_secret.grant_read(webhook_fn)
        queue.grant_send_messages(webhook_fn)

        # --- Worker Lambda: process the queue, reply on Telegram ---
        worker_fn = lambda_.Function(
            self,
            "WorkerFunction",
            handler="worker.handler.handler",
            timeout=WORKER_TIMEOUT,
            environment={
                "TELEGRAM_SECRET_ARN": telegram_secret.secret_arn,
                "DEDUP_TABLE": dedup_table.table_name,
            },
            **common,  # type: ignore[arg-type]
        )
        telegram_secret.grant_read(worker_fn)
        dedup_table.grant_write_data(worker_fn)
        worker_fn.add_event_source(
            event_sources.SqsEventSource(
                queue,
                batch_size=5,
                report_batch_item_failures=True,
            )
        )

        # --- HTTP API: POST /webhook ---
        http_api = apigw.HttpApi(self, "TelegramApi", description="StudyBuddy Telegram webhook")
        http_api.add_routes(
            path="/webhook",
            methods=[apigw.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("WebhookIntegration", webhook_fn),
        )

        # --- Alarm: anything in the DLQ means a message failed 3 times ---
        cloudwatch.Alarm(
            self,
            "DeadLetterAlarm",
            alarm_description="StudyBuddy: messages failed processing and reached the DLQ",
            metric=dlq.metric_approximate_number_of_messages_visible(period=Duration.minutes(5)),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # --- Monthly budget with email alerts at 25%, 60% and 100% of $40 ---
        if budget_email:
            budgets.CfnBudget(
                self,
                "ProjectBudget",
                budget=budgets.CfnBudget.BudgetDataProperty(
                    budget_name="studybuddy-monthly",
                    budget_type="COST",
                    time_unit="MONTHLY",
                    budget_limit=budgets.CfnBudget.SpendProperty(amount=40, unit="USD"),
                ),
                notifications_with_subscribers=[
                    budgets.CfnBudget.NotificationWithSubscribersProperty(
                        notification=budgets.CfnBudget.NotificationProperty(
                            comparison_operator="GREATER_THAN",
                            notification_type="ACTUAL",
                            threshold=pct,
                            threshold_type="PERCENTAGE",
                        ),
                        subscribers=[
                            budgets.CfnBudget.SubscriberProperty(
                                address=budget_email, subscription_type="EMAIL"
                            )
                        ],
                    )
                    for pct in (25, 60, 100)
                ],
            )

        CfnOutput(self, "WebhookUrl", value=f"{http_api.api_endpoint}/webhook")
        CfnOutput(self, "TelegramSecretArn", value=telegram_secret.secret_arn)
        CfnOutput(self, "DeadLetterQueueUrl", value=dlq.queue_url)
