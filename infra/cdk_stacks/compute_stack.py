from aws_cdk import Stack
from constructs import Construct

from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_batch as batch,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ecr_assets,
    Duration,
    Size,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    
    
)
import os
from cdk_stacks.common.batch_job_setup import MMMJobSetup, MMMJobType
from aws_cdk.aws_ecr_assets import DockerImageAsset, DockerImageAssetInvalidationOptions

# Relative path to the source code for the aws batch job, from the project root
DOCKER_BASE_DIR = "../src/"
DEPLOYMENT_REGION = os.getenv("CDK_DEFAULT_REGION")
DEPLOYMENT_ACCOUNT = os.getenv("CDK_DEFAULT_ACCOUNT")

class CdkComputeStack(Stack):

    def create_access_control(
        self,
        datalake_bucket_arn,
        ddb_table_arn,
        athena_workgroup_name,
        athena_catalog_name,
        datalake_glue_db,
    ):

        job_role = iam.Role(
            self,
            "HpcBlogJobRole",
            assumed_by=iam.PrincipalWithConditions(
                principal=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                conditions={
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:ecs:{DEPLOYMENT_REGION}:{DEPLOYMENT_ACCOUNT}:*"
                    },
                    "StringEquals": {"aws:SourceAccount": DEPLOYMENT_ACCOUNT},
                },
            ),
        )

        job_s3_policy = iam.PolicyStatement(
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
                datalake_bucket_arn,
                f"{datalake_bucket_arn}/*"
            ],
        )

        job_role.attach_inline_policy(
            iam.Policy(self, "S3WritePolicy", statements=[job_s3_policy])
        )

        # Create an IAM policy that grants athena access
        # The wildcard scope here allows access to all metadata actions
        job_athena_wide_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "athena:ListWorkGroups",
                "athena:ListDataCatalogs",
                "athena:ListEngineVersions",
            ],
            resources=["*"],
        )
        job_athena_scoped_policy = iam.PolicyStatement(
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

        job_role.attach_inline_policy(
            iam.Policy(
                self,
                "HpcBlogAthenaPolicy",
                statements=[job_athena_wide_policy, job_athena_scoped_policy],
            )
        )

        job_glue_policy = iam.PolicyStatement(
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

        job_role.attach_inline_policy(
            iam.Policy(self, "HpcBlogGluePolicy", statements=[job_glue_policy])
        )

        job_dynamodb_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
            ],
            resources=[ddb_table_arn],
        )

        job_role.attach_inline_policy(
            iam.Policy(self, "HpcBlogDynamoDBPolicy", statements=[job_dynamodb_policy])
        )

        task_execution_role = iam.Role(
            self,
            "HpcBlogTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )

        return job_role, task_execution_role

    def create_batch_infra(
        self,
        mmm_job_type: MMMJobType,
        s3_bucket_name,
        glue_db_name,
        ddb_table_name,
        container_asset,
        timeout,
        instance_classes,
        vpc,
        sg,
        gpu_enabled,
        job_role,
        task_execution_role,
    ):
        environment_variables = {
            "S3_BUCKET_NAME": s3_bucket_name,
            "DDB_TABLE_NAME": ddb_table_name,
            "AWS_DEFAULT_REGION": DEPLOYMENT_REGION,
            "SOURCE_GLUE_DB": glue_db_name,
            "SOURCE_MEDIA_TRAIN_TABLE": "media_data_train",
            "SOURCE_COST_TRAIN_TABLE": "cost_data_train",
            "SOURCE_TARGET_TRAIN_TABLE": "kpi_data_train",
            "SOURCE_EXTRA_FEATURES_TRAIN_TABLE": "feature_data_train",
        }
        container_def = {
            "image": ecs.ContainerImage.from_docker_image_asset(container_asset),
            "cpu": 192,
            "memory": Size.gibibytes(100),
            "execution_role": task_execution_role,
            "job_role": job_role,
            "environment": environment_variables,
        }
        if gpu_enabled:
            container_def["gpu"] = 8

        batch_job_definition = batch.EcsJobDefinition(
            self,
            mmm_job_type.job_definition_name,
            job_definition_name=mmm_job_type.job_definition_name,
            container=batch.EcsEc2ContainerDefinition(
                self, mmm_job_type.job_container_name, **container_def
            ),
            retry_attempts=1,
            timeout=Duration.minutes(timeout),
        )

        compute_environment = batch.ManagedEc2EcsComputeEnvironment(
            self,
            mmm_job_type.job_compute_env_name,
            #compute_environment_name=compute_env_name + suffix,
            spot=False,
            # spot_bid_percentage=75,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            minv_cpus=0,
            maxv_cpus=999,
            use_optimal_instance_classes=False,
            instance_classes=instance_classes,
            security_groups=[sg],
        )

        job_queue = batch.JobQueue(
            self,
            mmm_job_type.job_queue_name,
            job_queue_name=mmm_job_type.job_queue_name,
            priority=1,
        )

        job_queue.add_compute_environment(compute_environment, 1)

        return batch_job_definition, job_queue

    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc,
        datalake_bucket,
        datalake_glue_db,
        frontend_ddb_table,
        athena_workgroup_name,
        athena_catalog_name,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.batch_job_setup = MMMJobSetup(
            gpu_high=MMMJobType(
                job_definition_name="HpcBlogBatchJobGpuHigh",
                job_queue_name="HpcBlogBatchJobQueueGpuHigh",
                job_container_name="BatchJobContainerGpuHigh",
                job_compute_env_name="HpcBlogBatchJobComputeGpuHigh",
            ),
            gpu_low=MMMJobType(
                job_definition_name="HpcBlogBatchJobGpuLow",
                job_queue_name="HpcBlogBatchJobQueueGpuLow",
                job_container_name="BatchJobContainerGpuLow",
                job_compute_env_name="HpcBlogBatchJobComputeGpuLow",
            ),
            cpu=MMMJobType(
                job_definition_name="HpcBlogBatchJobCpu",
                job_queue_name="HpcBlogBatchJobQueueCpu",
                job_container_name="BatchJobContainerCpu",
                job_compute_env_name="HpcBlogBatchJobComputeCpu",
            ),
        )

        sg = ec2.SecurityGroup(
            self,
            "HpcBlogBatchSecurityGroup",
            vpc=vpc
        )

        gpu_docker_image_asset = DockerImageAsset(
            self,
            "HpcBlogGpuDockerImage",
            directory=DOCKER_BASE_DIR,
            file="./docker/gpu_image/Dockerfile",
        )

        cpu_docker_image_asset = DockerImageAsset(
            self,
            "HpcBlogCpuDockerImage",
            directory=DOCKER_BASE_DIR,
            file="./docker/cpu_image/Dockerfile",
        )

        job_role, task_execution_role = self.create_access_control(
            datalake_bucket_arn=datalake_bucket.bucket_arn,
            ddb_table_arn=frontend_ddb_table.table_arn,
            athena_workgroup_name=athena_workgroup_name,
            athena_catalog_name=athena_catalog_name,
            datalake_glue_db=datalake_glue_db,
        )

        self.create_batch_infra(
            self.batch_job_setup.gpu_low,
            datalake_bucket.bucket_name,
            datalake_glue_db.database_name,
            frontend_ddb_table.table_name,
            gpu_docker_image_asset,
            120,
            [ec2.InstanceClass.G5],
            vpc,
            sg,
            True,
            job_role,
            task_execution_role,
        )

        self.create_batch_infra(
            self.batch_job_setup.gpu_high,
            datalake_bucket.bucket_name,
            datalake_glue_db.database_name,
            frontend_ddb_table.table_name,
            gpu_docker_image_asset,
            120,
            [ec2.InstanceClass.G5],
            vpc,
            sg,
            True,
            job_role,
            task_execution_role,
        )

        self.create_batch_infra(
            self.batch_job_setup.cpu,
            datalake_bucket.bucket_name,
            datalake_glue_db.database_name,
            frontend_ddb_table.table_name,
            cpu_docker_image_asset,
            1440,
            [ec2.InstanceClass.C6I],
            vpc,
            sg,
            False,
            job_role,
            task_execution_role,
        )
