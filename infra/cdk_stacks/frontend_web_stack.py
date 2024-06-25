import os
from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3_deployment,
    Fn,
    aws_ssm as ssm,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    Duration,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
from cdk_stacks.common.batch_job_setup import MMMJobSetup
from aws_cdk.aws_cognito import UserPool, UserPoolClient
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_glue_alpha import Database

REACT_CODE_PATH = "../src/frontend/dist"
DEPLOYMENT_REGION = os.getenv("CDK_DEFAULT_REGION")
DEPLOYMENT_ACCOUNT = os.getenv("CDK_DEFAULT_ACCOUNT")


class CdkFrontEndWebStack(Stack):

    def __init__(
        self,
        scope: Construct,
        id: str,
        frontend_user_pool: UserPool,
        frontend_user_pool_client: UserPoolClient,
        frontend_ddb_table: Table,
        batch_job_setup: MMMJobSetup,
        datalake_glue_db: Database,
        datalake_bucket: s3.Bucket,
        logging_bucket: s3.Bucket,
        athena_workgroup_name: str,
        athena_catalog_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            id="lambda-powertools",
            layer_version_arn=f"arn:aws:lambda:{DEPLOYMENT_REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV2:69",
        )

        awswrangler_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            id="lambda-awswrangler",
            layer_version_arn=f"arn:aws:lambda:{DEPLOYMENT_REGION}:336392948345:layer:AWSSDKPandas-Python310:16",
        )

        frontend_api_func = lambda_.Function(
            self,
            "HpcBlogFrontendApiFunction",
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset(
                "../src/",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_10.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        f"cp -r ./shared/* /asset-output && "
                        f"cp -r ./lambda/frontend_api/* /asset-output",
                    ],
                ),
            ),
            handler="lambda-handler.lambda_handler",
            memory_size=256,
            timeout=Duration.seconds(6),
            environment={
                "GPU_HIGH_JOB_DEF_NAME": batch_job_setup.gpu_high.job_definition_name,
                "GPU_HIGH_JOB_QUEUE_NAME": batch_job_setup.gpu_high.job_queue_name,
                "GPU_LOW_JOB_DEF_NAME": batch_job_setup.gpu_low.job_definition_name,
                "GPU_LOW_JOB_QUEUE_NAME": batch_job_setup.gpu_low.job_queue_name,
                "CPU_JOB_DEF_NAME": batch_job_setup.cpu.job_definition_name,
                "CPU_JOB_QUEUE_NAME": batch_job_setup.cpu.job_queue_name,
                "S3_BUCKET_NAME": datalake_bucket.bucket_name,
                "DDB_TABLE_NAME": frontend_ddb_table.table_name,
                "SOURCE_GLUE_DB": datalake_glue_db.database_name,
            },
            layers=[powertools_layer, awswrangler_layer],
        )

        # This statement allows the lambda function to list all batch jobs
        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "batch:ListJobs",
                ],
                resources=[
                    "*",
                ],
            )
        )

        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "batch:SubmitJob",
                ],
                resources=[
                    f"arn:aws:batch:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:job-definition/{batch_job_setup.gpu_high.job_definition_name}*",
                    f"arn:aws:batch:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:job-definition/{batch_job_setup.gpu_low.job_definition_name}*",
                    f"arn:aws:batch:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:job-definition/{batch_job_setup.cpu.job_definition_name}*",
                    f"arn:aws:batch:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:job-queue/{batch_job_setup.gpu_high.job_queue_name}",
                    f"arn:aws:batch:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:job-queue/{batch_job_setup.gpu_low.job_queue_name}",
                    f"arn:aws:batch:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:job-queue/{batch_job_setup.cpu.job_queue_name}",
                ],
            )
        )

        # This statement allows the lambda function to list all glue tables amd get the specific tables for this project
        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
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
                    datalake_glue_db.database_arn,
                    f"{datalake_glue_db.database_arn}/*",
                    f"arn:aws:glue:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:catalog",
                    f"arn:aws:glue:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:table/{datalake_glue_db.database_name}/*",
                ],
            )
        )

        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
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
                ],
                resources=[
                    f"arn:aws:s3:::{datalake_bucket.bucket_name}",
                    f"arn:aws:s3:::{datalake_bucket.bucket_name}/*",
                ],
            )
        )
        # Create an IAM policy that grants athena access
        # The wildcard scope here allows access to all metadata actions
        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "athena:ListWorkGroups",
                    "athena:ListDataCatalogs",
                    "athena:ListEngineVersions",
                ],
                resources=["*"],
            )
        )
        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
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
                    "athena:GetDataCatalog",
                ],
                resources=[
                    f"arn:aws:athena:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:workgroup/{athena_workgroup_name}",
                    f"arn:aws:athena:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:datacatalog/{athena_catalog_name}",
                ],
            )
        )
        frontend_api_func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:DescribeTable",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DeleteItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                ],
                resources=[frontend_ddb_table.table_arn],
            )
        )

        backend_api_func = lambda_.DockerImageFunction(
            scope=self,
            id="HpcBlogBackendApiFunction",
            code=lambda_.DockerImageCode.from_image_asset(
                directory="../src/", file="./lambda/backend_api/Dockerfile"
            ),
            environment={
                "S3_BUCKET_NAME": datalake_bucket.bucket_name,
                "DDB_TABLE_NAME": frontend_ddb_table.table_name,
            },
            memory_size=10240,
            timeout=Duration.minutes(5),
        )

        backend_api_func.add_to_role_policy(
            iam.PolicyStatement(
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
                ],
                resources=[
                    f"arn:aws:s3:::{datalake_bucket.bucket_name}",
                    f"arn:aws:s3:::{datalake_bucket.bucket_name}/*",
                ],
            )
        )

        backend_api_func.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:DescribeTable",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:DeleteItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                ],
                resources=[frontend_ddb_table.table_arn],
            )
        )

        apigw_log_group = logs.LogGroup(self, "ApiGatewayAccessLogs")

        self.apigw_instance = apigw.LambdaRestApi(
            self,
            "HpcBlogFrontendApiEndpoint",
            handler=frontend_api_func,
            proxy=False,
            deploy_options=apigw.StageOptions(
                access_log_destination=apigw.LogGroupLogDestination(apigw_log_group),
                access_log_format=apigw.AccessLogFormat.clf(),
            ),
            endpoint_types=[apigw.EndpointType.REGIONAL],
        )
        apigw_authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "HpcBlogFrontendApiAuthorizer",
            cognito_user_pools=[frontend_user_pool],
        )

        frontend_resource = self.apigw_instance.root.add_resource(
            "frontend",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=["GET", "PUT", "OPTIONS"],
                allow_origins=apigw.Cors.ALL_ORIGINS,
            ),
        )

        frontend_resource_proxy = frontend_resource.add_proxy(
            default_integration=apigw.LambdaIntegration(frontend_api_func),
            any_method=False,
        )

        frontend_resource_proxy_method = frontend_resource_proxy.add_method(
            "ANY",
            authorizer=apigw_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        backend_resource = self.apigw_instance.root.add_resource(
            "backend",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=["GET", "PUT", "OPTIONS"],
                allow_origins=apigw.Cors.ALL_ORIGINS,
            ),
        )

        backend_resource_proxy = backend_resource.add_proxy(
            default_integration=apigw.LambdaIntegration(backend_api_func),
            any_method=False,
        )

        backend_resource_proxy_method = backend_resource_proxy.add_method(
            "ANY",
            authorizer=apigw_authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        self.webapp_bucket = s3.Bucket(
            self,
            "HpcBlogWebAppBucket",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # bucket_name="batch-job-webapp-bucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
        )

        distribution = cloudfront.Distribution(
            self,
            "HpcBlogWebAppCloudfrontDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                origin=origins.S3Origin(self.webapp_bucket),
            ),
            default_root_object="index.html",
            enable_logging=True,
            log_bucket=logging_bucket,
            log_file_prefix="cloudfront-access-logs/",
            log_includes_cookies=True,
        )

        user_pool_id_param_temp = ssm.StringParameter(
            self,
            "HpcBloguserPoolIdParam",
            allowed_pattern=".*",
            description="User Pool ID for Auth",
            parameter_name="userPoolIdParam",
            string_value=frontend_user_pool.user_pool_id,
            tier=ssm.ParameterTier.STANDARD,
        )

        user_pool_client_id_param_temp = ssm.StringParameter(
            self,
            "HpcBloguserPoolClientIdParam",
            allowed_pattern=".*",
            description="User Pool Client ID for Auth",
            parameter_name="userPoolClientIdParam",
            string_value=frontend_user_pool_client.user_pool_client_id,
            tier=ssm.ParameterTier.STANDARD,
        )

        frontend_env_config = {
            "userPoolId": user_pool_id_param_temp.string_value,
            "userPoolClientId": user_pool_client_id_param_temp.string_value,
            "apiEndpoint": self.apigw_instance.url,
        }

        deployment = s3_deployment.BucketDeployment(
            self,
            "HpcBlogWebAppBucketBucketDeployment",
            sources=[
                s3_deployment.Source.asset(REACT_CODE_PATH),
                s3_deployment.Source.json_data("env.json", frontend_env_config),
            ],
            destination_bucket=self.webapp_bucket,
            distribution=distribution,
        )
