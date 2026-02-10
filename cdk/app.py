#!/usr/bin/env python3
import os
import aws_cdk as cdk
from cdk.sanders_customer_platform_stack import SandersCustomerPlatformStack

app = cdk.App()

# Get environment from context or default to 'dev'
environment = app.node.try_get_context('environment') or 'dev'

# Environment configuration
env_config = {
    'dev': {
        'account': os.environ.get('CDK_DEFAULT_ACCOUNT'),
        'region': os.environ.get('CDK_DEFAULT_REGION', 'eu-central-1')
    },
    'prod': {
        'account': os.environ.get('CDK_DEFAULT_ACCOUNT'),
        'region': os.environ.get('CDK_DEFAULT_REGION', 'eu-central-1')
    }
}

# Create the main stack
SandersCustomerPlatformStack(
    app,
    f"SandersCustomerPlatformStack-{environment}",
    environment=environment,
    env=cdk.Environment(
        account=env_config[environment]['account'],
        region=env_config[environment]['region']
    ),
    description=f"Sanders Customer Platform Infrastructure - {environment}"
)

app.synth()
