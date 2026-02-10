from aws_cdk import (
    aws_iam as iam,
    Tags
)
from constructs import Construct


class BatchIAMRoles(Construct):
    """
    IAM Roles construct for AWS Batch
    Creates roles for Batch service and job execution
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        s3_bucket_arn: str,
        dynamodb_table_arn: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Batch Service Role
        self.batch_service_role = iam.Role(
            self,
            f"BatchServiceRole",
            role_name=f"sanders-batch-service-role-{environment}",
            assumed_by=iam.ServicePrincipal("batch.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSBatchServiceRole"
                )
            ]
        )

        # ECS Task Execution Role (for pulling images from ECR)
        self.ecs_task_execution_role = iam.Role(
            self,
            f"EcsTaskExecutionRole",
            role_name=f"sanders-ecs-task-execution-role-{environment}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ]
        )

        # Batch Job Role (for actual job execution with S3/DynamoDB access)
        self.batch_job_role = iam.Role(
            self,
            f"BatchJobRole",
            role_name=f"sanders-batch-job-role-{environment}",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        # Add S3 permissions
        self.batch_job_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket"
                ],
                resources=[
                    s3_bucket_arn,
                    f"{s3_bucket_arn}/*"
                ]
            )
        )

        # Add DynamoDB permissions
        self.batch_job_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:BatchGetItem"
                ],
                resources=[dynamodb_table_arn]
            )
        )

        # Add CloudWatch Logs permissions
        self.batch_job_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                resources=["*"]
            )
        )

        # Add tags
        Tags.of(self.batch_service_role).add("Environment", environment)
        Tags.of(self.ecs_task_execution_role).add("Environment", environment)
        Tags.of(self.batch_job_role).add("Environment", environment)

    @property
    def service_role_arn(self) -> str:
        return self.batch_service_role.role_arn

    @property
    def task_execution_role_arn(self) -> str:
        return self.ecs_task_execution_role.role_arn

    @property
    def job_role_arn(self) -> str:
        return self.batch_job_role.role_arn
