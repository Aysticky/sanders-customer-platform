from aws_cdk import (
    aws_batch as batch,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    Tags
)
from constructs import Construct
from typing import List


class BatchEnvironment(Construct):
    """
    AWS Batch Environment construct
    Creates compute environment, job queue, and job definitions
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        security_group: ec2.ISecurityGroup,
        batch_service_role_arn: str,
        ecs_task_execution_role_arn: str,
        batch_job_role_arn: str,
        ecr_repository_uri: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Batch Compute Environment
        self.compute_environment = batch.CfnComputeEnvironment(
            self,
            f"ComputeEnvironment",
            compute_environment_name=f"sanders-batch-compute-{environment}",
            type="MANAGED",
            state="ENABLED",
            service_role=batch_service_role_arn,
            compute_resources=batch.CfnComputeEnvironment.ComputeResourcesProperty(
                type="FARGATE",
                maxv_cpus=16,
                subnets=[subnet.subnet_id for subnet in vpc.private_subnets],
                security_group_ids=[security_group.security_group_id]
            )
        )

        # Create Job Queue
        self.job_queue = batch.CfnJobQueue(
            self,
            f"JobQueue",
            job_queue_name=f"sanders-batch-queue-{environment}",
            priority=1,
            state="ENABLED",
            compute_environment_order=[
                batch.CfnJobQueue.ComputeEnvironmentOrderProperty(
                    compute_environment=self.compute_environment.attr_compute_environment_arn,
                    order=1
                )
            ]
        )

        # Create Job Definitions for different memory sizes
        self.job_definitions = {}
        
        memory_configs = [
            {"name": "2g", "memory": "2048", "cpu": "0.5"},    # 2GB, 0.5 vCPU (valid Fargate combo)
            {"name": "8g", "memory": "8192", "cpu": "2"},      # 8GB, 2 vCPU (valid Fargate combo)
            {"name": "16g", "memory": "16384", "cpu": "4"}     # 16GB, 4 vCPU (valid Fargate combo)
        ]

        for config in memory_configs:
            job_def = batch.CfnJobDefinition(
                self,
                f"JobDef{config['name'].upper()}",
                job_definition_name=f"sanders-job-{config['name']}-{environment}",
                type="container",
                platform_capabilities=["FARGATE"],
                container_properties=batch.CfnJobDefinition.ContainerPropertiesProperty(
                    image=f"{ecr_repository_uri}:latest",
                    execution_role_arn=ecs_task_execution_role_arn,
                    job_role_arn=batch_job_role_arn,
                    fargate_platform_configuration=batch.CfnJobDefinition.FargatePlatformConfigurationProperty(
                        platform_version="LATEST"
                    ),
                    resource_requirements=[
                        batch.CfnJobDefinition.ResourceRequirementProperty(
                            type="VCPU",
                            value=config["cpu"]
                        ),
                        batch.CfnJobDefinition.ResourceRequirementProperty(
                            type="MEMORY",
                            value=config["memory"]
                        )
                    ],
                    log_configuration=batch.CfnJobDefinition.LogConfigurationProperty(
                        log_driver="awslogs"
                    )
                )
            )
            self.job_definitions[config['name']] = job_def

        # Add tags
        Tags.of(self.compute_environment).add("Environment", environment)
        Tags.of(self.job_queue).add("Environment", environment)
        for job_def in self.job_definitions.values():
            Tags.of(job_def).add("Environment", environment)

    @property
    def queue_arn(self) -> str:
        return self.job_queue.attr_job_queue_arn

    @property
    def queue_name(self) -> str:
        return self.job_queue.job_queue_name
