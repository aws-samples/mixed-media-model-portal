from dataclasses import dataclass, asdict
import os
import multiprocessing
import pickle
import io
import re
from io import BytesIO

os.environ["XLA_FLAGS"] = "--xla_force_host_platform_device_count={}".format(
    multiprocessing.cpu_count()
)
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
os.environ["XLA_PYTHON_CLIENT_MEM_FRACTION"] = ".50"
os.environ["XLA_PYTHON_CLIENT_ALLOCATOR"] = "platform"

import jax.numpy as jnp
import numpyro

import pandas as pd
import numpy as np
from lightweight_mmm import lightweight_mmm
from lightweight_mmm import plot

from datetime import datetime
import boto3
import awswrangler as wr

from numpyro.diagnostics import summary
from operator import attrgetter
from ec2_metadata import ec2_metadata
from jax.lib import xla_bridge
import jax
from util import LightweightMMMSerializer
from jobrecord import JobRecord, JobStatus

c_type = xla_bridge.get_backend().platform

n_cores = len(os.sched_getaffinity(0))

if c_type == "gpu":
    n_cores = jax.local_device_count()

print(f"Setting host device count to {n_cores}")

numpyro.set_host_device_count(n_cores)

s3_client = boto3.client("s3")

def create_multi_dim_array(df, value_column):
    index_mapping = {}
    for column in df.columns:
        if column != value_column:
            unique_values = df[column].unique()
            index_mapping[column] = {
                label: idx for idx, label in enumerate(unique_values)
            }

    shape = [
        len(index_mapping[column]) for column in df.columns if column != value_column
    ]

    multi_dim_array = np.zeros(shape, dtype=np.float32)

    for _, row in df.iterrows():
        indices = tuple(
            index_mapping[column][row[column]]
            for column in df.columns
            if column != value_column
        )
        value = row[value_column]
        multi_dim_array[indices] = value

    return multi_dim_array


def transform_media_data(input_data):
    weeks = input_data["week_number"].unique()
    channels = input_data["media_channel"].unique()
    week_to_index = {week: i for i, week in enumerate(weeks)}
    channel_to_index = {channel: i for i, channel in enumerate(channels)}

    num_weeks = len(weeks)
    num_channels = len(channels)
    num_geographies = input_data["geography"].nunique()

    multi_dim_array = np.zeros(
        (num_weeks, num_channels, num_geographies), dtype=np.float32
    )

    for _, row in input_data.iterrows():
        week_idx = week_to_index[row["week_number"]]
        channel_idx = channel_to_index[row["media_channel"]]
        geo_idx = row["geography"]
        impression = row["impressions"]
        multi_dim_array[week_idx, channel_idx, geo_idx] = impression

    return multi_dim_array


def transform_cost_data(input_data):
    channels = input_data["media_channel"].unique()
    channel_to_index = {channel: i for i, channel in enumerate(channels)}

    num_channels = len(channels)

    multi_dim_array = np.zeros((num_channels), dtype=np.float32)

    for _, row in input_data.iterrows():
        channel_idx = channel_to_index[row["media_channel"]]
        cost = row["avg_cost_per_unit"]
        multi_dim_array[channel_idx] = cost

    return multi_dim_array

def sanitize_table_name(table_name):
    pattern = re.compile(r"^[a-zA-Z0-9_]+$")
    if pattern.match(table_name):
        return table_name
    else:
        raise ValueError(
            "Table name contains invalid characters. Only alphanumeric characters and underscores are allowed."
        )

def get_data(
    glue_db,
    media_train_table,
    cost_train_table,
    target_train_table,
    extra_features_train_table,
):
    media_data_df = wr.athena.read_sql_query(
        sql=f"SELECT * FROM {sanitize_table_name(media_train_table)}",
        database=glue_db,
        encryption="SSE_S3",
        data_source="HpcBlogDataLakeAthenaCatalog",
        workgroup="HpcBlogDataLakeAthenaWorkGroup",
        ctas_approach=False,
    )

    media_data_train = create_multi_dim_array(media_data_df, "impressions")
    print(
        f"Media data summary: Data Size#{len(media_data_train)} Media Channels#{len(media_data_train[0])} Geos#{len(media_data_train[0][0])}"
    )

    cost_data_df = wr.athena.read_sql_query(
        sql=f"SELECT * FROM {sanitize_table_name(cost_train_table)}",
        database=glue_db,
        encryption="SSE_S3",
        data_source="HpcBlogDataLakeAthenaCatalog",
        workgroup="HpcBlogDataLakeAthenaWorkGroup",
        ctas_approach=False,
    )

    cost_data_train = create_multi_dim_array(cost_data_df, "avg_cost_per_unit")
    print(f"Cost data summary: Media Channels#{len(cost_data_train)}")

    target_data_df = wr.athena.read_sql_query(
        sql=f"SELECT * FROM {sanitize_table_name(target_train_table)}",
        database=glue_db,
        encryption="SSE_S3",
        data_source="HpcBlogDataLakeAthenaCatalog",
        workgroup="HpcBlogDataLakeAthenaWorkGroup",
        ctas_approach=False,
    )

    target_data_train = create_multi_dim_array(target_data_df, "kpi")
    print(
        f"Target KPI data summary: Data Size#{len(target_data_train)} Geos#{len(target_data_train[0])}"
    )

    extra_feature_df = wr.athena.read_sql_query(
        sql=f"SELECT * FROM {sanitize_table_name(extra_features_train_table)}",
        database=glue_db,
        encryption="SSE_S3",
        data_source="HpcBlogDataLakeAthenaCatalog",
        workgroup="HpcBlogDataLakeAthenaWorkGroup",
        ctas_approach=False,
    )

    extra_features_train = create_multi_dim_array(extra_feature_df, "feature_value")
    print(
        f"Media data summary: Data Size#{len(extra_features_train)} Extra Features#{len(extra_features_train[0])} Geos#{len(extra_features_train[0][0])}"
    )

    return media_data_train, cost_data_train, target_data_train, extra_features_train


def write_data(df, glue_db_name, table_name, bucket_name):
    wr.s3.to_parquet(
        df=df,
        database=glue_db_name,
        table=table_name,
        dataset=True,
        path=f"s3://{bucket_name}/masterdata/{table_name}",
    )


def save_model_to_s3(bucket_name, job_id, model):
    start_time = datetime.now()
    print(f"Starting Model Transfer to S3")

    json_bucket_key = f"saved_models/{job_id}_media_mix_model.json"
    numpy_bucket_key = f"saved_models/{job_id}_media_mix_model.npz"

    json_str, numpy_bytes_obj = LightweightMMMSerializer.serialize(model)

    json_file_obj = BytesIO(json_str.encode("utf-8"))

    s3_client.upload_fileobj(
        Fileobj=json_file_obj, Bucket=bucket_name, Key=json_bucket_key
    )

    print(f"json metadata was saved to bucket#{bucket_name} key#{json_bucket_key}")

    s3_client.upload_fileobj(
        Fileobj=numpy_bytes_obj, Bucket=bucket_name, Key=numpy_bucket_key
    )

    print(f"numpy binary data was saved to bucket#{bucket_name} key#{numpy_bucket_key}")

    end_time = datetime.now()
    transfer_time = end_time - start_time

    print("Model Transfer Time: %s" % transfer_time)

    return numpy_bucket_key


def get_contribution_graph_data(target_scaler, model):
    channel_names = None
    contribution_df = plot.create_media_baseline_contribution_df(
        media_mix_model=model, target_scaler=target_scaler, channel_names=channel_names
    )

    contribution_columns = [
    col for col in contribution_df.columns if "contribution" in col
    ]
    contribution_df_for_plot = contribution_df.loc[:, contribution_columns]
    contribution_df_for_plot = contribution_df_for_plot[
    contribution_df_for_plot.columns[::-1]]
    period = np.arange(1, contribution_df_for_plot.shape[0] + 1)
    contribution_df_for_plot.loc[:, "period"] = period

    return contribution_df_for_plot


def get_contribution_percentage_with_error_graph_data(
    target_scaler, cost_scaler, model
):
    interval_mid_range: float = 0.9
    media_contribution, roi_hat = model.get_posterior_metrics(
        target_scaler=target_scaler, cost_scaler=cost_scaler
    )
    metric = media_contribution

    upper_quantile = 1 - (1 - interval_mid_range) / 2
    lower_quantile = (1 - interval_mid_range) / 2

    if metric.ndim == 3:
        metric = jnp.mean(metric, axis=-1)

    quantile_bounds = np.quantile(
    metric, q=[lower_quantile, upper_quantile], axis=0)
    quantile_bounds[0] = metric.mean(axis=0) - quantile_bounds[0]
    quantile_bounds[1] = quantile_bounds[1] - metric.mean(axis=0)

    tmp_data = metric.mean(axis=0)

    contribution_percentage_df = pd.DataFrame(
        {
            "contribution_channel": [
                f"channel_{i}" for i in range(quantile_bounds.shape[1])
            ],
            "error_min": quantile_bounds[0, :],
            "error_max": quantile_bounds[1, :],
            "contribution_pct": tmp_data[:],
        }
    )

    return contribution_percentage_df


def get_scaler(bucket_name, table_name):
    scaler_key = f"saved_scaler/{table_name}_scaler.pkl"

    pickled_scaler = s3_client.get_object(Bucket=bucket_name, Key=scaler_key)[
        "Body"
    ].read()

    loaded_scaler = pickle.loads(pickled_scaler)

    return loaded_scaler

def do_tripple_m(
    media_data_train,
    costs,
    target_train,
    extra_features_train,
    number_warmup,
    number_samples,
    number_chains
):
    start_time = datetime.now()
    print(f"Starting Tripple M Training")

    SEED = 105

    mmm = lightweight_mmm.LightweightMMM(model_name="carryover")

    mmm.fit(
        media=media_data_train,
        media_prior=costs,
        target=target_train,
        extra_features=extra_features_train,
        number_warmup=number_warmup,
        number_samples=number_samples,
        number_chains=number_chains,
        seed=SEED,
    )

    states = mmm._mcmc._states
    sample_field = mmm._mcmc._sample_field
    last_state = mmm._mcmc._last_state

    sites = states[sample_field]
    if isinstance(sites, dict):
        state_sample_field = attrgetter(sample_field)(last_state)
        if isinstance(state_sample_field, dict):
            sites = {
                k: v for k, v in states[sample_field].items() if k in state_sample_field
            }

    x = summary(sites, prob=0.9)

    end_time = datetime.now()
    execution_time = end_time - start_time

    print("MMM Training Time: %s" % execution_time)

    return mmm, execution_time


def get_mandatory_env(name):
    """
    Reads the env variable, raises an exception if missing.
    """
    if name not in os.environ:
        raise Exception("Missing mandatory ENV variable '%s'" % name)

    print(f"{name} has Value: {os.environ.get(name)}")

    return os.environ.get(name)


def main():
    """
    Batch job execution entry point script.
    """

    dynamodb = boto3.resource("dynamodb")

    bucket_name = get_mandatory_env("S3_BUCKET_NAME")
    ddb_table_name = get_mandatory_env("DDB_TABLE_NAME")
    glue_db = get_mandatory_env("SOURCE_GLUE_DB")
    job_id = get_mandatory_env("JOB_ID")
    batch_job_id = get_mandatory_env("AWS_BATCH_JOB_ID")
    ddb_table = dynamodb.Table(ddb_table_name)

    response = ddb_table.get_item(Key={"job_id": job_id})

    if "Item" in response:
        job_item = JobRecord(**response["Item"])
    else:
        raise Exception(f"Job entry with id {job_id} not found")

    number_warmup = job_item.req_number_warmup
    number_samples = job_item.req_number_samples
    number_chains = job_item.req_number_chains

    start_time = datetime.now()
    print(f"Get data from Athena")
    media_data_train, costs, target_train, extra_features_train = get_data(
        glue_db,
        job_item.req_media_table,
        job_item.req_cost_table,
        job_item.req_kpi_table,
        job_item.req_feature_table,
    )

    end_time = datetime.now()
    data_retrieval_time = end_time - start_time
    print("Get data from Athena: %s" % data_retrieval_time)

    model, execution_time = do_tripple_m(
        media_data_train,
        costs,
        target_train,
        extra_features_train,
        int(job_item.req_number_warmup),
        int(job_item.req_number_samples),
        int(job_item.req_number_chains)
    )

    model_save_path = save_model_to_s3(bucket_name, job_id, model)

    target_scaler = get_scaler(bucket_name, job_item.req_kpi_table)
    cost_scaler = get_scaler(bucket_name, job_item.req_cost_table)

    contribution_graph_df = get_contribution_graph_data(target_scaler, model)
    contribution_graph_df.insert(0, "job_id", job_id)
    write_data(contribution_graph_df, glue_db, "contribution_graph_data", bucket_name)

    contribution_percentage_df = get_contribution_percentage_with_error_graph_data(
        target_scaler, cost_scaler, model
    )
    contribution_percentage_df.insert(0, "job_id", job_id)
    write_data(
        contribution_percentage_df, glue_db, "contribution_percentage_data", bucket_name
    )

    compute_type = xla_bridge.get_backend().platform

    compute_cores = os.cpu_count()

    if compute_type == "gpu":
        compute_cores = jax.local_device_count()

    job_item.proc_data_size = len(media_data_train)
    job_item.proc_n_media_channels = 222
    job_item.proc_n_geos = 333
    job_item.proc_instance_type = ec2_metadata.instance_type
    job_item.proc_compute_cores = compute_cores
    job_item.proc_compute_type = (compute_type).upper()
    job_item.execution_time = execution_time
    job_item.model_uri = model_save_path
    job_item.job_status = JobStatus.COMPLETED.value

    ddb_table.put_item(Item=job_item.dict())


if __name__ == "__main__":
    main()
