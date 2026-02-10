from aws_cdk import (
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    Duration,
    Tags
)
from constructs import Construct
import json


class StepFunctionsStateMachine(Construct):
    """
    Step Functions State Machine construct
    Orchestrates AWS Batch jobs
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        job_queue_arn: str,
        job_definitions: dict,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM role for Step Functions
        self.state_machine_role = iam.Role(
            self,
            f"StateMachineRole",
            role_name=f"sanders-stepfunctions-role-{environment}",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        # Add Batch permissions
        self.state_machine_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "batch:SubmitJob",
                    "batch:DescribeJobs",
                    "batch:TerminateJob"
                ],
                resources=["*"]
            )
        )

        # Add Events permissions for Batch job status
        self.state_machine_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "events:PutTargets",
                    "events:PutRule",
                    "events:DescribeRule"
                ],
                resources=["*"]
            )
        )

        # Define a simple parallel job execution workflow
        # Jobs accept command from input: $.command (array of strings)
        # Example input: {"command": ["jobs/daily_features_tlc.py"]}
        
        # Job 1: Feature extraction with 8GB
        job_1 = tasks.BatchSubmitJob(
            self,
            "FeatureExtractionJob",
            job_name="feature-extraction",
            job_queue_arn=job_queue_arn,
            job_definition_arn=job_definitions['8g'].ref,
            container_overrides=tasks.BatchContainerOverrides(
                command=sfn.JsonPath.list_at("$.command")
            ),
            result_path="$.featureJob"
        )

        # Job 2: Data processing with 2GB
        job_2 = tasks.BatchSubmitJob(
            self,
            "DataProcessingJob",
            job_name="data-processing",
            job_queue_arn=job_queue_arn,
            job_definition_arn=job_definitions['2g'].ref,
            container_overrides=tasks.BatchContainerOverrides(
                command=sfn.JsonPath.list_at("$.command")
            ),
            result_path="$.processingJob"
        )

        # Job 3: Model training with 16GB (runs after feature extraction)
        job_3 = tasks.BatchSubmitJob(
            self,
            "ModelTrainingJob",
            job_name="model-training",
            job_queue_arn=job_queue_arn,
            job_definition_arn=job_definitions['16g'].ref,
            container_overrides=tasks.BatchContainerOverrides(
                command=sfn.JsonPath.list_at("$.command")
            ),
            result_path="$.trainingJob"
        )

        # Success state
        succeed = sfn.Succeed(
            self,
            "SuccessState",
            comment="All jobs completed successfully"
        )

        # Fail state
        fail = sfn.Fail(
            self,
            "FailState",
            cause="Job execution failed",
            error="JobFailed"
        )

        # Define workflow: Run job_1 and job_2 in parallel, then job_3
        parallel_jobs = sfn.Parallel(
            self,
            "ParallelJobs",
            result_path="$.parallelResults"
        )
        parallel_jobs.branch(job_1)
        parallel_jobs.branch(job_2)

        # Chain: parallel jobs -> training job -> success
        definition = parallel_jobs.next(job_3).next(succeed)

        # Add error handling
        parallel_jobs.add_catch(fail, result_path="$.error")
        job_3.add_catch(fail, result_path="$.error")

        # Create State Machine
        self.state_machine = sfn.StateMachine(
            self,
            f"StateMachine",
            state_machine_name=f"sanders-orchestrator-{environment}",
            definition=definition,
            role=self.state_machine_role,
            timeout=Duration.hours(24)
        )

        # Add tags
        Tags.of(self.state_machine).add("Environment", environment)
        Tags.of(self.state_machine).add("Service", "sanders-customer-platform")

    @property
    def state_machine_arn(self) -> str:
        return self.state_machine.state_machine_arn

    @property
    def state_machine_name(self) -> str:
        return self.state_machine.state_machine_name
