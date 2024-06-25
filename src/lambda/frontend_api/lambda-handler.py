import boto3
import json
import os
import uuid
from dataclasses import dataclass, asdict
from decimal import Decimal
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from typing import Optional
import awswrangler as wr
from jobrecord import JobRecord, JobStatus

tracer = Tracer()
logger = Logger()
cors_config = CORSConfig(allow_origin="*", max_age=300)
app = APIGatewayRestResolver(cors=cors_config)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return super(DecimalEncoder, self).default(o)

batch_client = boto3.client("batch")
glue_client = boto3.client("glue")
athena_client = boto3.client("athena")
dynamodb = boto3.resource("dynamodb")
s3_resource = boto3.resource("s3")
job_names_string = os.environ.get("job_names", "")

job_queue_names = job_names_string.split(",")

if "S3_BUCKET_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable S3_BUCKET_NAME")
if "DDB_TABLE_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable DDB_TABLE_NAME")
if "SOURCE_GLUE_DB" not in os.environ:
    raise Exception("Missing mandatory ENV variable SOURCE_GLUE_DB")
if "AWS_REGION" not in os.environ:
    raise Exception("Missing mandatory ENV variable AWS_REGION")
if "GPU_HIGH_JOB_DEF_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable GPU_HIGH_JOB_DEF_NAME")
if "GPU_HIGH_JOB_QUEUE_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable GPU_HIGH_JOB_QUEUE_NAME")
if "GPU_LOW_JOB_DEF_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable GPU_LOW_JOB_DEF_NAME")
if "GPU_LOW_JOB_QUEUE_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable GPU_LOW_JOB_QUEUE_NAME")
if "CPU_JOB_DEF_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable CPU_JOB_DEF_NAME")
if "CPU_JOB_QUEUE_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable CPU_JOB_QUEUE_NAME")

BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
DDB_TABLE_NAME = os.environ.get("DDB_TABLE_NAME")
GLUE_DB = os.environ.get("SOURCE_GLUE_DB")
REGION = os.environ.get("AWS_REGION")
GPU_HIGH_JOB_DEF_NAME = os.environ.get("GPU_HIGH_JOB_DEF_NAME")
GPU_HIGH_JOB_QUEUE_NAME = os.environ.get("GPU_HIGH_JOB_QUEUE_NAME")
GPU_LOW_JOB_DEF_NAME = os.environ.get("GPU_LOW_JOB_DEF_NAME")
GPU_LOW_JOB_QUEUE_NAME = os.environ.get("GPU_LOW_JOB_QUEUE_NAME")
CPU_JOB_DEF_NAME = os.environ.get("CPU_JOB_DEF_NAME")
CPU_JOB_QUEUE_NAME = os.environ.get("CPU_JOB_QUEUE_NAME")

ddb_table = dynamodb.Table(DDB_TABLE_NAME)


@app.get("/frontend/tables")
@tracer.capture_method
def get_tables():
    logger.info(f"Getting all tables")
    try:
        response = glue_client.get_tables(DatabaseName=GLUE_DB)

        table_names = [table["Name"] for table in response["TableList"]]

        return table_names

    except Exception as e:
        logger.exception(f"Error: {e}")
        return []


@app.get("/frontend/jobs/<job_id>")
@tracer.capture_method
def get_job_by_id(job_id: str):
    logger.info(f"Getting data for job {job_id}")

    response = ddb_table.get_item(Key={"job_id": job_id})

    if "Item" in response:
        job_details = response["Item"]
        return job_details


@app.get("/frontend/jobs/<job_id>/graph")
@tracer.capture_method
def get_job_graph(job_id: str):
    graph_type: str = app.current_event.get_query_string_value(
        name="graph_type", default_value=""
    )

    logger.info(f"Getting graph data for job {job_id} and graph type {graph_type}")

    graph_data = []

    match graph_type:
        case "media_baseline_contribution_area_plot":
            contribution_graph_df = wr.athena.read_sql_query(
                sql=f"SELECT * FROM contribution_graph_data WHERE job_id=:job_id",
                params={"job_id": job_id},
                database=GLUE_DB,
                encryption="SSE_S3",
                data_source="HpcBlogDataLakeAthenaCatalog",
                workgroup="HpcBlogDataLakeAthenaWorkGroup",
                ctas_approach=False,
            )

            for col in contribution_graph_df.columns[1:-1]:
                contribution_data = []
                for i, row in contribution_graph_df.iterrows():
                    contribution_data.append(
                        {"x": f"period_{row['period']}", "y": row[col]}
                    )
                graph_data.append({"id": col, "data": contribution_data})
        case "bars_media_metrics":
            bars_metrics_graph_df = wr.athena.read_sql_query(
                sql=f"SELECT * FROM contribution_percentage_data WHERE job_id=:job_id",
                params={"job_id": job_id},
                database=GLUE_DB,
                encryption="SSE_S3",
                data_source="HpcBlogDataLakeAthenaCatalog",
                workgroup="HpcBlogDataLakeAthenaWorkGroup",
                ctas_approach=False,
            )
                        
            for _, row in bars_metrics_graph_df.iterrows():
                graph_data.append({
                    "x": row['contribution_channel'],
                    "y": row['contribution_pct'],
                    "errorX": 0,
                    "errorY": row['error_max']
                })

        case _:
            None

    return json.dumps(graph_data)


@app.get("/frontend/jobs")
@tracer.capture_method
def get_all_jobs():
    logger.info(f"Getting all jobs")

    limit = 100

    scan_kwargs = {"Limit": limit}

    response = ddb_table.scan(**scan_kwargs)

    job_list = {
        "items": response["Items"],
        "next_key": response.get("LastEvaluatedKey"),
    }

    return job_list


@app.put("/frontend/jobs")
@tracer.capture_method
def put_job():
    request_body = app.current_event.json_body

    required_fields = [
        "req_media_table",
        "req_kpi_table",
        "req_cost_table",
        "req_feature_table",
        "req_number_warmup",
        "req_number_samples",
        "req_number_chains",
        "req_compute_type",
        "req_compute_cores",
    ]

    for field in required_fields:
        if field not in request_body or not request_body[field]:
            error_message = f"Field '{field}' is missing or empty in the request body."
            raise BadRequestError(error_message)

    job_id = str(uuid.uuid4())[:8]

    job_data = JobRecord(
        job_id=job_id,
        job_name=request_body["job_name"],
        req_media_table=request_body["req_media_table"],
        req_kpi_table=request_body["req_kpi_table"],
        req_cost_table=request_body["req_cost_table"],
        req_feature_table=request_body["req_feature_table"],
        req_number_warmup=int(request_body["req_number_warmup"]),
        req_number_samples=int(request_body["req_number_samples"]),
        req_number_chains=int(request_body["req_number_chains"]),
        req_compute_type=request_body["req_compute_type"],
        req_compute_cores=request_body["req_compute_cores"],
        req_memory_multp=request_body["req_memory_multp"],
        job_status=JobStatus.PENDING.value, 
    )

    ddb_table.put_item(Item=asdict(job_data))

    batch_result = submit_batch_job(job_data)

    logger.info(batch_result)

    return {"job": json.dumps(asdict(job_data))}, 201


def submit_batch_job(job_data):
    req_mem = (
        (int(job_data.req_compute_cores) * int(job_data.req_memory_multp)) - 5
    ) * 1000

    match job_data.req_compute_type:
        case "GPU (A10)":
            job_queue_name = GPU_LOW_JOB_QUEUE_NAME
            job_definition_name = GPU_LOW_JOB_DEF_NAME
        case "GPU (H100)":
            job_queue_name = GPU_HIGH_JOB_QUEUE_NAME
            job_definition_name = GPU_HIGH_JOB_DEF_NAME
        case _:
            job_queue_name = CPU_JOB_QUEUE_NAME
            job_definition_name = CPU_JOB_DEF_NAME

    response = batch_client.submit_job(
        jobName=job_data.job_name,
        jobQueue=job_queue_name,
        jobDefinition=job_definition_name,
        parameters={},
        containerOverrides={
            "command": [
                "conda",
                "run",
                "--no-capture-output",
                "-n",
                "batch-docker-conda",
                "python",
                "-u",
                "mainathena.py",
            ],
            "resourceRequirements": [
                {"type": "VCPU", "value": job_data.req_compute_cores},
                {"type": "MEMORY", "value": str(req_mem)},
            ],
            "environment": [
                {
                    "name": "SOURCE_COST_TRAIN_TABLE",
                    "value": job_data.req_cost_table,
                },
                {
                    "name": "SOURCE_TARGET_TRAIN_TABLE",
                    "value": job_data.req_kpi_table,
                },
                {
                    "name": "SOURCE_EXTRA_FEATURES_TRAIN_TABLE",
                    "value": job_data.req_feature_table,
                },
                {
                    "name": "SOURCE_MEDIA_TRAIN_TABLE",
                    "value": job_data.req_media_table,
                },
                {"name": "AWS_DEFAULT_REGION", "value": REGION},
                {"name": "S3_BUCKET_NAME", "value": BUCKET_NAME},
                {"name": "SOURCE_GLUE_DB", "value": GLUE_DB},
                {
                    "name": "DDB_TABLE_NAME",
                    "value": DDB_TABLE_NAME,
                },
                {
                    "name": "JOB_ID",
                    "value": job_data.job_id,
                },
            ],
        },
    )

    return response


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.debug(f"API request event: {event}")
    return app.resolve(event, context)
