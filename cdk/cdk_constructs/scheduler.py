"""
EventBridge Scheduler Construct
Automates recurring job execution for Sanders Customer Platform
"""
from aws_cdk import (
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    Tags
)
from constructs import Construct
import json


class JobScheduler(Construct):
    """
    EventBridge rules for scheduling recurring jobs
    
    Schedules:
    - Daily feature generation (runs at 2 AM UTC)
    - Weekly model training (runs Sunday at 3 AM UTC)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        job_queue_arn: str,
        job_definition_arn_8g: str,
        job_definition_arn_16g: str,
        s3_bucket_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # IAM role for EventBridge to submit Batch jobs
        self.scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            role_name=f"sanders-scheduler-role-{environment}",
            assumed_by=iam.ServicePrincipal("events.amazonaws.com"),
        )

        self.scheduler_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["batch:SubmitJob"],
                resources=["*"]
            )
        )

        # Schedule 1: Daily feature generation (2 AM UTC)
        daily_features_rule = events.Rule(
            self,
            "DailyFeaturesRule",
            rule_name=f"sanders-daily-features-{environment}",
            description=f"Run daily feature generation job at 2 AM UTC ({environment})",
            schedule=events.Schedule.cron(
                minute="0",
                hour="2",
                month="*",
                week_day="*",
                year="*"
            ),
            enabled=True if environment == "prod" else False  # Only enable in prod
        )

        # Target: Batch job for daily features
        daily_features_rule.add_target(
            targets.BatchJob(
                job_queue_arn=job_queue_arn,
                job_queue_scope=None,
                job_definition_arn=job_definition_arn_8g,
                job_definition_scope=None,
                job_name=f"daily-features-scheduled",
                event=events.RuleTargetInput.from_object({
                    "command": ["jobs/daily_features_tlc.py"],
                    "environment": [
                        {"name": "SCP_ENV", "value": environment},
                        {"name": "TLC_DATA_PATH", "value": f"s3://{s3_bucket_name}/raw/nyc_tlc/tlc_small.parquet"},
                        {"name": "LOG_LEVEL", "value": "INFO"}
                    ]
                }),
                attempts=2,  # Retry once on failure
                role=self.scheduler_role
            )
        )

        # Schedule 2: Weekly model training (Sunday 3 AM UTC)
        weekly_training_rule = events.Rule(
            self,
            "WeeklyTrainingRule",
            rule_name=f"sanders-weekly-training-{environment}",
            description=f"Run weekly model training job on Sunday at 3 AM UTC ({environment})",
            schedule=events.Schedule.cron(
                minute="0",
                hour="3",
                month="*",
                week_day="SUN",
                year="*"
            ),
            enabled=False  # Disabled by default (enable when training job ready)
        )

        # Target: Batch job for model training (placeholder)
        weekly_training_rule.add_target(
            targets.BatchJob(
                job_queue_arn=job_queue_arn,
                job_queue_scope=None,
                job_definition_arn=job_definition_arn_16g,
                job_definition_scope=None,
                job_name=f"weekly-training-scheduled",
                event=events.RuleTargetInput.from_object({
                    "command": ["jobs/daily_features_tlc.py"],  # Placeholder
                    "environment": [
                        {"name": "SCP_ENV", "value": environment},
                        {"name": "LOG_LEVEL", "value": "INFO"}
                    ]
                }),
                attempts=1,
                role=self.scheduler_role
            )
        )

        # Add tags
        Tags.of(self).add("Environment", environment)
        Tags.of(self).add("Service", "sanders-customer-platform")
