from decimal import Decimal
import os
import jax.numpy as jnp
import pickle
from lightweight_mmm import optimize_media
from datetime import datetime
import json
import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from io import BytesIO
from typing import Optional
from util import LightweightMMMSerializer

tracer = Tracer()
logger = Logger()
cors_config = CORSConfig(allow_origin="*", max_age=300)
app = APIGatewayRestResolver(cors=cors_config, enable_validation=True)

# Get mandotory settings from env variables
if "S3_BUCKET_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable S3_BUCKET_NAME")
if "DDB_TABLE_NAME" not in os.environ:
    raise Exception("Missing mandatory ENV variable DDB_TABLE_NAME")

bucket_name = os.environ.get("S3_BUCKET_NAME")
ddb_table_name = os.environ.get("DDB_TABLE_NAME")
dynamodb = boto3.resource("dynamodb")
ddb_table = dynamodb.Table(ddb_table_name)
s3_client = boto3.client("s3")


# Helper class to encode dynamodb response type Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return super(DecimalEncoder, self).default(o)

@app.get("/backend/budget")
@tracer.capture_method
def get_optimized_budget(job_id: str, budget: int):
    logger.info(f"Running inference [Budget] for job {job_id}")
    model = get_model(job_id)
    logger.info(f"Model downloading for job {job_id} complete")
    default_fig_size = (5, 5)

    logger.info(f"Getting data for job {job_id}")

    response = ddb_table.get_item(Key={"job_id": job_id})

    job_details = response["Item"]

    prices = jnp.ones(model.n_media_channels)
    SEED = 105
    n_time_periods = 12
    target_scaler = get_scaler(job_details["req_kpi_table"])
    extra_features_scaler = get_scaler(job_details["req_feature_table"])
    media_scaler = get_scaler(job_details["req_media_table"])

    (
        solution,
        kpi_without_optim,
        previous_media_allocation,
    ) = optimize_media.find_optimal_budgets(
        n_time_periods=n_time_periods,
        media_mix_model=model,
        budget=budget,
        prices=prices,
        media_scaler=media_scaler,
        target_scaler=target_scaler,
        seed=SEED,
    )

    optimal_buget_allocation = prices * solution.x

    previous_budget_allocation = prices * previous_media_allocation

    previous_budget_allocation_pct = previous_budget_allocation / jnp.sum(
    previous_budget_allocation)
    optimized_budget_allocation_pct = optimal_buget_allocation / jnp.sum(
    optimal_buget_allocation)

    channel_names = model.media_names
    kpi_with_optim=solution['fun']

    pre_optimizaiton_predicted_target = kpi_without_optim * -1
    post_optimization_predictiond_target = kpi_with_optim * -1
    predictions = [
    pre_optimizaiton_predicted_target, post_optimization_predictiond_target
    ]

    graph1_data = []
    optimal_buget_allocation = optimal_buget_allocation.tolist()
    optimized_budget_allocation_pct = optimized_budget_allocation_pct.tolist()
    previous_budget_allocation = previous_budget_allocation.tolist()
    previous_budget_allocation_pct = previous_budget_allocation_pct.tolist()

    graph1_data = [
        {
            "id": "optimal_budget_allocation",
            "data": [
                {
                    "x": channel_names[i],
                    "y": optimal_buget_allocation[i],
                    "y1_label": optimized_budget_allocation_pct[i],
                }
                for i in range(len(channel_names))
            ],
        },
        {
            "id": "previous_budget_allocation",
            "data": [
                {
                    "x": channel_names[i],
                    "y": previous_budget_allocation[i],
                    "y1_label": previous_budget_allocation_pct[i],
                }
                for i in range(len(channel_names))
            ],
        },
    ]

    graph2_data = [
        {
            "x": "Pre optimization \n predicted target",
            "y": int(pre_optimizaiton_predicted_target),
        },
        {
            "x": "Post optimization \n predicted target",
            "y": int(post_optimization_predictiond_target),
        },
    ]

    graph_data = {"graph1": graph1_data, "graph2": {"data": graph2_data}}
    return json.dumps(graph_data)

def get_scaler(table_name):
    scaler_key = f"saved_scaler/{table_name}_scaler.pkl"

    pickled_scaler = s3_client.get_object(Bucket=bucket_name, Key=scaler_key)["Body"].read()

    loaded_scaler = pickle.loads(pickled_scaler)

    return loaded_scaler


def get_model_size(job_id):
    numpy_bucket_key = f"saved_models/{job_id}_media_mix_model.npz"

    model_size_in_bytes = s3_client.get_object(
        Bucket=bucket_name, Key=numpy_bucket_key
    ).content_length

    model_size_in_gigabytes = model_size_in_bytes / (1024**3)

    return model_size_in_gigabytes

def get_model(job_id):
    json_bucket_key = f"saved_models/{job_id}_media_mix_model.json"
    numpy_bucket_key = f"saved_models/{job_id}_media_mix_model.npz"

    json_bytes = BytesIO()
    numpy_bytes = BytesIO()

    s3_client.download_fileobj(Bucket=bucket_name, Key=json_bucket_key, Fileobj=json_bytes)
    s3_client.download_fileobj(Bucket=bucket_name, Key=numpy_bucket_key, Fileobj=numpy_bytes)

    json_bytes.seek(0)
    numpy_bytes.seek(0)

    loaded_mmm_model = LightweightMMMSerializer.deserialize(numpy_bytes=numpy_bytes, json_bytes=json_bytes)

    return loaded_mmm_model


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.debug(f"API request event: {event}")
    return app.resolve(event, context)
