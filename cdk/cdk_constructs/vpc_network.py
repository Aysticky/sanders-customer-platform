from aws_cdk import (
    aws_ec2 as ec2,
    Tags
)
from constructs import Construct


class VPCNetwork(Construct):
    """
    VPC Network construct for Sanders Customer Platform
    Creates VPC with public and private subnets for Batch compute
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC with public and private subnets
        # Using explicit AZ count without querying AWS to avoid permission requirements
        self.vpc = ec2.Vpc(
            self,
            f"VPC",
            vpc_name=f"sanders-customer-platform-vpc-{environment}",
            max_azs=2,  # Use 2 availability zones
            nat_gateways=1,  # 1 NAT gateway for cost optimization
            availability_zones=None,  # Let CDK use default without querying
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Security group for Batch compute
        self.batch_security_group = ec2.SecurityGroup(
            self,
            f"BatchSecurityGroup",
            vpc=self.vpc,
            description="Security group for AWS Batch compute environment",
            security_group_name=f"sanders-batch-sg-{environment}",
            allow_all_outbound=True
        )

        # Add tags
        Tags.of(self.vpc).add("Environment", environment)
        Tags.of(self.vpc).add("Service", "sanders-customer-platform")
        Tags.of(self.batch_security_group).add("Environment", environment)
        Tags.of(self.batch_security_group).add("Service", "sanders-customer-platform")

    @property
    def vpc_id(self) -> str:
        return self.vpc.vpc_id

    @property
    def private_subnets(self):
        return self.vpc.private_subnets

    @property
    def security_group_id(self) -> str:
        return self.batch_security_group.security_group_id
