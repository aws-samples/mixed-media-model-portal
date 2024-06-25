import os
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_cognito as _cognito,
    CfnElement,
    RemovalPolicy,
    aws_s3 as s3,
)
from constructs import Construct

class CdkFrontEndCommonStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.logging_bucket = s3.Bucket(
            self,
            "HpcBlogLoggingBucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # bucket_name="batch-job-datalake-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership= s3.ObjectOwnership.OBJECT_WRITER,
        )

        self.ddb_table = dynamodb.Table(
            self,
            "HpcBlogJobTable",
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            # table_name="batch-job-benchmark-table-ondemand",
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.user_pool = _cognito.UserPool(
            self,
            "HpcBlogUserPool",
            self_sign_up_enabled=False,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            advanced_security_mode=_cognito.AdvancedSecurityMode.ENFORCED,
        )
        self.user_pool_client = self.user_pool.add_client(
            "HpcBlogUserPoolClient",
            auth_flows=_cognito.AuthFlow(user_srp=True),
            generate_secret=False,
            supported_identity_providers=[
                _cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )
