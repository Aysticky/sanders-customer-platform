from aws_cdk import (
    aws_s3 as s3,
    RemovalPolicy,
    Tags
)
from constructs import Construct


class S3Bucket(Construct):
    """
    S3 Bucket construct for Sanders Customer Platform
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        bucket_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create S3 bucket
        self.bucket = s3.Bucket(
            self,
            f"Bucket",
            bucket_name=bucket_name,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN if environment == 'prod' else RemovalPolicy.DESTROY,
            auto_delete_objects=False if environment == 'prod' else True,
        )

        # Add tags
        Tags.of(self.bucket).add("Environment", environment)
        Tags.of(self.bucket).add("Service", "sanders-customer-platform")

    @property
    def bucket_name(self) -> str:
        return self.bucket.bucket_name

    @property
    def bucket_arn(self) -> str:
        return self.bucket.bucket_arn
