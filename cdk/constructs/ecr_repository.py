from aws_cdk import (
    aws_ecr as ecr,
    RemovalPolicy,
    Tags
)
from constructs import Construct


class ECRRepository(Construct):
    """
    ECR Repository construct for Sanders Customer Platform
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        repository_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create ECR repository
        self.repository = ecr.Repository(
            self,
            f"Repository",
            repository_name=repository_name,
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN if environment == 'prod' else RemovalPolicy.DESTROY,
            empty_on_delete=False if environment == 'prod' else True,
        )

        # Add lifecycle policy to manage image retention
        self.repository.add_lifecycle_rule(
            description="Keep last 10 images",
            max_image_count=10,
            tag_status=ecr.TagStatus.ANY
        )

        # Add tags
        Tags.of(self.repository).add("Environment", environment)
        Tags.of(self.repository).add("Service", "sanders-customer-platform")

    @property
    def repository_uri(self) -> str:
        return self.repository.repository_uri

    @property
    def repository_arn(self) -> str:
        return self.repository.repository_arn

    @property
    def repository_name(self) -> str:
        return self.repository.repository_name
