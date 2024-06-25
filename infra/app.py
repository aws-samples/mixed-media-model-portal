#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_stacks.vpc_stack import CdkVpcStack
from cdk_stacks.compute_stack import CdkComputeStack
from cdk_stacks.datalake_stack import CdkDataLakeStack
from cdk_stacks.frontend_web_stack import CdkFrontEndWebStack
from cdk_stacks.frontend_common import CdkFrontEndCommonStack

app = cdk.App()

env = {
    "account": os.environ["CDK_DEFAULT_ACCOUNT"],
    "region": os.environ["CDK_DEFAULT_REGION"],
}

vpc_stack = CdkVpcStack(app, "NetworkStack", env=env)

frontend_common_stack = CdkFrontEndCommonStack(
    app,
    "FrontendCommonStack",
    env=env,
)

datalake_stack = CdkDataLakeStack(app, "DatalakeStack", env=env)

batchjob_stack = CdkComputeStack(
    app,
    "ComputeStack",
    vpc=vpc_stack.vpc,
    datalake_bucket=datalake_stack.datalake_bucket,
    datalake_glue_db=datalake_stack.datalake_glue_db,
    frontend_ddb_table=frontend_common_stack.ddb_table,
    athena_workgroup_name=datalake_stack.cfn_work_group.name,
    athena_catalog_name=datalake_stack.cfn_data_catalog.name,
    env=env,
)

frontend_web_stack = CdkFrontEndWebStack(
    app,
    "FrontendWebStack",
    frontend_user_pool=frontend_common_stack.user_pool,
    frontend_user_pool_client=frontend_common_stack.user_pool_client,
    frontend_ddb_table=frontend_common_stack.ddb_table,
    batch_job_setup=batchjob_stack.batch_job_setup,
    datalake_glue_db=datalake_stack.datalake_glue_db,
    datalake_bucket=datalake_stack.datalake_bucket,
    logging_bucket=frontend_common_stack.logging_bucket,
    athena_workgroup_name=datalake_stack.cfn_work_group.name,
    athena_catalog_name=datalake_stack.cfn_data_catalog.name,
    env=env,
)

frontend_web_stack.node.add_dependency(batchjob_stack)

app.synth()
