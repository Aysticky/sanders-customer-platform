"""
CloudWatch Monitoring Construct
Creates dashboards and alarms for Sanders Customer Platform
"""
from aws_cdk import Duration, Tags
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_sns as sns
from constructs import Construct


class MonitoringDashboard(Construct):
    """
    CloudWatch Dashboard and Alarms for monitoring the platform
    
    Monitors:
    - Batch job success/failure rates
    - Job duration
    - DynamoDB read/write capacity
    - S3 bucket size
    - Step Functions execution status
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        job_queue_name: str,
        dynamodb_table_name: str,
        s3_bucket_name: str,
        state_machine_name: str,
        alarm_email: str = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SNS topic for alarms
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=f"sanders-alarms-{environment}",
            display_name=f"Sanders Platform Alarms ({environment})"
        )

        # Subscribe email if provided
        if alarm_email:
            sns.Subscription(
                self,
                "AlarmEmailSubscription",
                topic=self.alarm_topic,
                protocol=sns.SubscriptionProtocol.EMAIL,
                endpoint=alarm_email
            )

        # Create dashboard
        dashboard = cw.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"sanders-platform-{environment}",
        )

        # Batch Job Metrics
        batch_failed_jobs = cw.Metric(
            namespace="AWS/Batch",
            metric_name="JobsFailed",
            dimensions_map={"JobQueue": job_queue_name},
            statistic="Sum",
            period=Duration.minutes(5)
        )

        batch_succeeded_jobs = cw.Metric(
            namespace="AWS/Batch",
            metric_name="JobsSucceeded",
            dimensions_map={"JobQueue": job_queue_name},
            statistic="Sum",
            period=Duration.minutes(5)
        )

        batch_running_jobs = cw.Metric(
            namespace="AWS/Batch",
            metric_name="JobsRunning",
            dimensions_map={"JobQueue": job_queue_name},
            statistic="Average",
            period=Duration.minutes(1)
        )

        # DynamoDB Metrics
        ddb_consumed_read_capacity = cw.Metric(
            namespace="AWS/DynamoDB",
            metric_name="ConsumedReadCapacityUnits",
            dimensions_map={"TableName": dynamodb_table_name},
            statistic="Sum",
            period=Duration.minutes(5)
        )

        ddb_consumed_write_capacity = cw.Metric(
            namespace="AWS/DynamoDB",
            metric_name="ConsumedWriteCapacityUnits",
            dimensions_map={"TableName": dynamodb_table_name},
            statistic="Sum",
            period=Duration.minutes(5)
        )

        # Step Functions Metrics
        sfn_failed_executions = cw.Metric(
            namespace="AWS/States",
            metric_name="ExecutionsFailed",
            dimensions_map={"StateMachineArn": state_machine_name},
            statistic="Sum",
            period=Duration.minutes(5)
        )

        sfn_succeeded_executions = cw.Metric(
            namespace="AWS/States",
            metric_name="ExecutionsSucceeded",
            dimensions_map={"StateMachineArn": state_machine_name},
            statistic="Sum",
            period=Duration.minutes(5)
        )

        # Add widgets to dashboard
        dashboard.add_widgets(
            cw.GraphWidget(
                title="Batch Job Status",
                left=[batch_succeeded_jobs, batch_failed_jobs],
                width=12,
                height=6
            ),
            cw.GraphWidget(
                title="Running Jobs",
                left=[batch_running_jobs],
                width=12,
                height=6
            )
        )

        dashboard.add_widgets(
            cw.GraphWidget(
                title="DynamoDB Capacity",
                left=[ddb_consumed_read_capacity],
                right=[ddb_consumed_write_capacity],
                width=12,
                height=6
            ),
            cw.GraphWidget(
                title="Step Functions Executions",
                left=[sfn_succeeded_executions, sfn_failed_executions],
                width=12,
                height=6
            )
        )

        # Create alarms
        
        # Alarm: Batch job failures
        batch_failure_alarm = cw.Alarm(
            self,
            "BatchJobFailureAlarm",
            alarm_name=f"sanders-batch-failures-{environment}",
            alarm_description=f"Alert when Batch jobs fail in {environment}",
            metric=batch_failed_jobs,
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING
        )
        batch_failure_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Alarm: Step Functions failures
        sfn_failure_alarm = cw.Alarm(
            self,
            "StepFunctionsFailureAlarm",
            alarm_name=f"sanders-stepfunctions-failures-{environment}",
            alarm_description=f"Alert when Step Functions executions fail in {environment}",
            metric=sfn_failed_executions,
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING
        )
        sfn_failure_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Alarm: High DynamoDB write capacity (cost control)
        ddb_high_writes_alarm = cw.Alarm(
            self,
            "DynamoDBHighWritesAlarm",
            alarm_name=f"sanders-dynamodb-high-writes-{environment}",
            alarm_description=f"Alert when DynamoDB writes are unusually high in {environment}",
            metric=ddb_consumed_write_capacity,
            threshold=10000,  # Adjust based on expected workload
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING
        )
        ddb_high_writes_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Add tags
        Tags.of(self).add("Environment", environment)
        Tags.of(self).add("Service", "sanders-customer-platform")

    @property
    def topic_arn(self) -> str:
        return self.alarm_topic.topic_arn
