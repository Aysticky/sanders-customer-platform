from aws_cdk import (
    Stack,
    CfnOutput,
    Tags
)
from constructs import Construct
from cdk.constructs.s3_bucket import S3Bucket
from cdk.constructs.dynamodb_table import DynamoDBTable
from cdk.constructs.ecr_repository import ECRRepository
from cdk.constructs.vpc_network import VPCNetwork
from cdk.constructs.batch_iam_roles import BatchIAMRoles
from cdk.constructs.batch_environment import BatchEnvironment
from cdk.constructs.stepfunctions_statemachine import StepFunctionsStateMachine


class SandersCustomerPlatformStack(Stack):
    """
    Main stack for Sanders Customer Platform Infrastructure
    Creates all AWS resources needed for the batch processing pipeline
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add stack-level tags
        Tags.of(self).add("Project", "sanders-customer-platform")
        Tags.of(self).add("Environment", environment)
        Tags.of(self).add("ManagedBy", "CDK")

        # 1. Create S3 Bucket
        s3_bucket = S3Bucket(
            self,
            "S3Bucket",
            bucket_name=f"sanders-customer-platform-{environment}",
            environment=environment
        )

        # 2. Create DynamoDB Table
        dynamodb_table = DynamoDBTable(
            self,
            "DynamoDBTable",
            table_name=f"sanders_daily_customer_features_{environment}",
            partition_key="customer_id",
            sort_key="date",
            environment=environment
        )

        # 3. Create ECR Repository
        ecr_repository = ECRRepository(
            self,
            "ECRRepository",
            repository_name=f"sanders-customer-platform-{environment}",
            environment=environment
        )

        # 4. Create VPC and Network
        vpc_network = VPCNetwork(
            self,
            "VPCNetwork",
            environment=environment
        )

        # 5. Create IAM Roles for Batch
        batch_iam_roles = BatchIAMRoles(
            self,
            "BatchIAMRoles",
            s3_bucket_arn=s3_bucket.bucket_arn,
            dynamodb_table_arn=dynamodb_table.table_arn,
            environment=environment
        )

        # 6. Create Batch Environment, Queue, and Job Definitions
        batch_environment = BatchEnvironment(
            self,
            "BatchEnvironment",
            vpc=vpc_network.vpc,
            security_group=vpc_network.batch_security_group,
            batch_service_role_arn=batch_iam_roles.service_role_arn,
            ecs_task_execution_role_arn=batch_iam_roles.task_execution_role_arn,
            batch_job_role_arn=batch_iam_roles.job_role_arn,
            ecr_repository_uri=ecr_repository.repository_uri,
            environment=environment
        )

        # 7. Create Step Functions State Machine
        stepfunctions = StepFunctionsStateMachine(
            self,
            "StepFunctions",
            job_queue_arn=batch_environment.queue_arn,
            job_definitions=batch_environment.job_definitions,
            environment=environment
        )

        # ===== Outputs =====
        
        CfnOutput(
            self,
            "S3BucketName",
            value=s3_bucket.bucket_name,
            description="S3 Bucket for data storage",
            export_name=f"sanders-s3-bucket-{environment}"
        )

        CfnOutput(
            self,
            "DynamoDBTableName",
            value=dynamodb_table.table_name,
            description="DynamoDB table for customer features",
            export_name=f"sanders-dynamodb-table-{environment}"
        )

        CfnOutput(
            self,
            "ECRRepositoryURI",
            value=ecr_repository.repository_uri,
            description="ECR repository URI for Docker images",
            export_name=f"sanders-ecr-uri-{environment}"
        )

        CfnOutput(
            self,
            "VPCId",
            value=vpc_network.vpc_id,
            description="VPC ID",
            export_name=f"sanders-vpc-id-{environment}"
        )

        CfnOutput(
            self,
            "BatchJobQueueName",
            value=batch_environment.queue_name,
            description="AWS Batch Job Queue",
            export_name=f"sanders-batch-queue-{environment}"
        )

        CfnOutput(
            self,
            "StepFunctionsStateMachineARN",
            value=stepfunctions.state_machine_arn,
            description="Step Functions State Machine ARN",
            export_name=f"sanders-stepfunctions-arn-{environment}"
        )

        CfnOutput(
            self,
            "StepFunctionsStateMachineName",
            value=stepfunctions.state_machine_name,
            description="Step Functions State Machine Name",
            export_name=f"sanders-stepfunctions-name-{environment}"
        )
