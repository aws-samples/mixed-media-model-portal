from aws_cdk import (Stack , Fn)
from constructs import Construct

from aws_cdk import (

    aws_s3 as s3,
    aws_glue_alpha as glue,
    aws_lambda as lambda_,
    BundlingOptions,
    BundlingOutput,
    RemovalPolicy,
    Duration,
    aws_iam as iam,
    aws_athena as athena
)
import os

DEPLOYMENT_ACCOUNT = os.getenv("CDK_DEFAULT_ACCOUNT")
DEPLOYMENT_REGION = os.getenv("CDK_DEFAULT_REGION")

class CdkDataLakeStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.cfn_data_catalog = athena.CfnDataCatalog(
            self,
            "HpcBlogDataLakeAthenaCatalog",
            name="HpcBlogDataLakeAthenaCatalog",
            type="GLUE",
            description="description",
            parameters={"catalog-id": DEPLOYMENT_ACCOUNT},
        )

        self.datalake_bucket = s3.Bucket(
            self,
            "HpcBlogDataLakeBucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # bucket_name="batch-job-datalake-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        self.cfn_work_group = athena.CfnWorkGroup(
            self,
            "HpcBlogDataLakeAthenaWorkGroup",
            name="HpcBlogDataLakeAthenaWorkGroup",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                enforce_work_group_configuration=False,
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    encryption_configuration=athena.CfnWorkGroup.EncryptionConfigurationProperty(
                        encryption_option="SSE_S3",
                    ),
                    output_location=f"s3://{self.datalake_bucket.bucket_name}/athena-query-results/",
                ),
            ),
        )

        self.datalake_glue_db = glue.Database(
            self,
            "HpcBlogDataLakeGlueDb"
        )

        environment_variables = {
                            "S3_BUCKET_NAME": self.datalake_bucket.bucket_name,
                            "SOURCE_GLUE_DB": self.datalake_glue_db.database_name,
                        }
        lambda_from_image = lambda_.DockerImageFunction(
            scope=self,
            id="HpcBlogDataGenerator",
            code=lambda_.DockerImageCode.from_image_asset(
                directory="../src/", 
                file="./lambda/data_generator/Dockerfile"
            ),
            environment=environment_variables,
            memory_size=10240,
            timeout=Duration.minutes(10),
        )

        # Create an IAM policy that grants write access to the S3 bucket
        lambda_s3_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:ListBucketMultipartUploads",
                "s3:ListMultipartUploadParts",
                "s3:AbortMultipartUpload",
                "s3:CreateBucket",
                "s3:PutObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],  # Modify the actions as needed
            resources=[
                self.datalake_bucket.bucket_arn,
                f"{self.datalake_bucket.bucket_arn}/*",
            ],
        )

        # Create an IAM policy that grants athena access
        # The wildcard scope here allows access to all metadata actions
        lambda_athena_wide_policy = iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "athena:ListWorkGroups",
                        "athena:ListDataCatalogs",
                        "athena:ListEngineVersions",
                    ],
                    resources=["*"],
                )
        lambda_athena_scoped_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "athena:BatchGetQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:GetQueryResultsStream",
                "athena:ListQueryExecutions",
                "athena:StartQueryExecution",
                "athena:StopQueryExecution",
                "athena:GetWorkGroup",
                "athena:GetDatabase",
                "athena:GetTableMetadata",
                "athena:ListDatabases",
                "athena:ListTableMetadata",
            ],
            resources=[
                f"arn:aws:athena:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:workgroup/{self.cfn_work_group.name}",
                f"arn:aws:athena:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:datacatalog/{self.cfn_data_catalog.name}",
            ],
        )
        # Create an IAM policy that grants glue db access
        # The wildcard permission allows us to read and write to tables created under our Glue DB for this project
        lambda_glue_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "glue:GetDatabase",
                "glue:GetDatabases",
                "glue:GetTable",
                "glue:GetTables",
                "glue:DeleteTable",
                "glue:CreateTable",
            ],
            resources=[
                self.datalake_glue_db.database_arn,
                f"{self.datalake_glue_db.database_arn}/*",
                f"arn:aws:glue:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:catalog",
                f"arn:aws:glue:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:table/{self.datalake_glue_db.database_name}/*",
            ],
        )
        lambda_from_image.add_to_role_policy(lambda_s3_policy)
        lambda_from_image.add_to_role_policy(lambda_athena_wide_policy)
        lambda_from_image.add_to_role_policy(lambda_athena_scoped_policy)
        lambda_from_image.add_to_role_policy(lambda_glue_policy)
