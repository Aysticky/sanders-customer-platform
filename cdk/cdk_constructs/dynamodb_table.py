from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    Tags
)
from constructs import Construct


class DynamoDBTable(Construct):
    """
    DynamoDB Table construct for Sanders Customer Platform
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        table_name: str,
        partition_key: str,
        sort_key: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB table
        self.table = dynamodb.Table(
            self,
            f"Table",
            table_name=table_name,
            partition_key=dynamodb.Attribute(
                name=partition_key,
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name=sort_key,
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN if environment == 'prod' else RemovalPolicy.DESTROY,
            point_in_time_recovery=True if environment == 'prod' else False,
        )

        # Add tags
        Tags.of(self.table).add("Environment", environment)
        Tags.of(self.table).add("Service", "sanders-customer-platform")

    @property
    def table_name(self) -> str:
        return self.table.table_name

    @property
    def table_arn(self) -> str:
        return self.table.table_arn
