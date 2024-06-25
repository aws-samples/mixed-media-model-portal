import os
import jax.numpy as jnp
import numpyro
import pandas as pd
from lightweight_mmm import preprocessing
from lightweight_mmm import utils
from datetime import datetime
import awswrangler as wr
from numpyro.diagnostics import summary
from jax.lib import xla_bridge
import jax
import boto3
import pickle

CHANNELS = ["Facebook", "TikTok", "Amazon", "Instagram", "Google", "Youtube"]
FEATURES = ["feature1", "feature2"]


def write_media_data(input_media_data, output_name, s3_bucket_base_path, glue_db_name):
    weeks = [f"Week {i + 1}" for i in range(len(input_media_data))]

    media_data_flat = [
        (week, channel, geography, impression.item())
        for week, week_data in enumerate(input_media_data)
        for channel, channel_data in enumerate(week_data)
        for geography, impression in enumerate(channel_data)
    ]

    df = pd.DataFrame(
        media_data_flat,
        columns={
            "week_number": pd.Series(dtype="int"),
            "media_channel": pd.Series(dtype="str"),
            "geography": pd.Series(dtype="str"),
            "impressions": pd.Series(dtype="float"),
        },
    )

    df["week_number"] = df["week_number"].map(dict(enumerate(weeks)))
    df["media_channel"] = df["media_channel"].map(dict(enumerate(CHANNELS)))

    wr.s3.to_parquet(  
        df=df,
        database=glue_db_name,
        table=output_name,
        dataset=True,
        path=f"{s3_bucket_base_path}/{output_name}",
    )


def write_feature_data(
    input_feature_data, output_name, s3_bucket_base_path, glue_db_name
):

    weeks = [f"Week {i + 1}" for i in range(len(input_feature_data))]

    feature_data_flat = [
        (week, feature, geography, feature_value.item())
        for week, week_data in enumerate(input_feature_data)
        for feature, feature_data in enumerate(week_data)
        for geography, feature_value in enumerate(feature_data)
    ]

    df2 = pd.DataFrame(
        feature_data_flat,
        columns=["week_number", "feature", "geography", "feature_value"],
    )
    df2["week_number"] = df2["week_number"].map(dict(enumerate(weeks)))
    df2["feature"] = df2["feature"].map(dict(enumerate(FEATURES)))
    print(df2)

    wr.s3.to_parquet(
        df=df2,
        database=glue_db_name,
        table=output_name,
        dataset=True,
        path=f"{s3_bucket_base_path}/{output_name}",
    )


def write_cost_data(input_cost_data, output_name, s3_bucket_base_path, glue_db_name):

    cost_data_flat = [
        (channel, cost.item()) for channel, cost in enumerate(input_cost_data)
    ]
    df3 = pd.DataFrame(cost_data_flat, columns=["media_channel", "avg_cost_per_unit"])
    df3["media_channel"] = df3["media_channel"].map(dict(enumerate(CHANNELS)))
    print(df3)

    wr.s3.to_parquet( 
        df=df3,
        database=glue_db_name,
        table=output_name,
        dataset=True,
        path=f"{s3_bucket_base_path}/{output_name}",
    )


def write_kpi_data(input_kpi_data, output_name, s3_bucket_base_path, glue_db_name):

    weeks = [f"Week {i + 1}" for i in range(len(input_kpi_data))]

    target_data_flat = [
        (week, geography, kpi.item())
        for week, week_data in enumerate(input_kpi_data)
        for geography, kpi in enumerate(week_data)
    ]
    df4 = pd.DataFrame(target_data_flat, columns=["week_number", "geography", "kpi"])
    df4["week_number"] = df4["week_number"].map(dict(enumerate(weeks)))

    print(df4)

    wr.s3.to_parquet(
        df=df4,
        database=glue_db_name,
        table=output_name,
        dataset=True,
        path=f"{s3_bucket_base_path}/{output_name}",
    )


def save_scaler_object(scaler_object, bucket_name, bucket_key):
    scaler_pickle_byte_obj = pickle.dumps(obj=scaler_object)
    s3_resource = boto3.resource("s3")
    s3_resource.Object(bucket_name, bucket_key).put(Body=scaler_pickle_byte_obj)


def generate_data(
    bucket_name, data_size, n_media_channels, n_extra_features, n_geos, glue_db_name
):

    media_data, extra_features, target, costs = utils.simulate_dummy_data(
        data_size=data_size,
        n_media_channels=n_media_channels,
        n_extra_features=n_extra_features,
        geos=n_geos,
    )

    s3_bucket_base_path = f"s3://{bucket_name}/masterdata"

    write_media_data(
        media_data,
        f"media_data_{data_size}-{n_media_channels}-{n_extra_features}-{n_geos}",
        s3_bucket_base_path,
        glue_db_name,
    )
    write_feature_data(
        extra_features,
        f"feature_data_{data_size}-{n_media_channels}-{n_extra_features}-{n_geos}",
        s3_bucket_base_path,
        glue_db_name,
    )
    write_cost_data(
        costs,
        f"cost_dat_{data_size}-{n_media_channels}-{n_extra_features}-{n_geos}",
        s3_bucket_base_path,
        glue_db_name,
    )
    write_kpi_data(
        target,
        f"kpi_data_{data_size}-{n_media_channels}-{n_extra_features}-{n_geos}",
        s3_bucket_base_path,
        glue_db_name,
    )

    split_point = data_size - 13
    media_data_train = media_data[:split_point, ...]
    extra_features_train = extra_features[:split_point, ...]
    target_train = target[:split_point]

    media_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
    extra_features_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
    target_scaler = preprocessing.CustomScaler(divide_operation=jnp.mean)
    cost_scaler = preprocessing.CustomScaler(
        divide_operation=jnp.mean, multiply_by=0.15
    )

    media_data_train = media_scaler.fit_transform(media_data_train)
    extra_features_train = extra_features_scaler.fit_transform(extra_features_train)
    target_train = target_scaler.fit_transform(target_train)
    costs_train = cost_scaler.fit_transform(costs)

    write_media_data(
        media_data_train,
        f"media_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train",
        s3_bucket_base_path,
        glue_db_name,
    )
    write_feature_data(
        extra_features_train,
        f"feature_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train",
        s3_bucket_base_path,
        glue_db_name,
    )
    write_cost_data(
        costs_train,
        f"cost_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train",
        s3_bucket_base_path,
        glue_db_name,
    )
    write_kpi_data(
        target_train,
        f"kpi_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train",
        s3_bucket_base_path,
        glue_db_name,
    )

    save_scaler_object(
        media_scaler,
        bucket_name,
        f"saved_scaler/media_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train_scaler.pkl",
    )
    save_scaler_object(
        extra_features_scaler,
        bucket_name,
        f"saved_scaler/feature_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train_scaler.pkl",
    )
    save_scaler_object(
        target_scaler,
        bucket_name,
        f"saved_scaler/kpi_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train_scaler.pkl",
    )
    save_scaler_object(
        cost_scaler,
        bucket_name,
        f"saved_scaler/cost_data_{data_size}_{n_media_channels}_{n_extra_features}_{n_geos}_train_scaler.pkl",
    )


def get_mandatory_env(name):
    """
    Reads the env variable, raises an exception if missing.
    """
    if name not in os.environ:
        raise Exception("Missing mandatory ENV variable '%s'" % name)

    print(f"{name} has Value: {os.environ.get(name)}")
    return os.environ.get(name)


def handler(event, context):
    """
    Batch job execution entry point script.
    """
    bucket_name = get_mandatory_env("S3_BUCKET_NAME")
    glue_db_name = get_mandatory_env("SOURCE_GLUE_DB")

    data_size = 160
    n_media_channels = 6
    n_extra_features = 2

    start_time = datetime.now()
    print(f"Starting Data Generation")
    generate_data(bucket_name, data_size, 3, n_extra_features, 100, glue_db_name)

    generate_data(bucket_name, data_size, 3, n_extra_features, 200, glue_db_name)

    generate_data(bucket_name, data_size, 3, n_extra_features, 300, glue_db_name)

    generate_data(bucket_name, data_size, 6, n_extra_features, 100, glue_db_name)

    generate_data(bucket_name, data_size, 6, n_extra_features, 200, glue_db_name)

    generate_data(bucket_name, data_size, 6, n_extra_features, 300, glue_db_name)

    generate_data(bucket_name, data_size, 3, n_extra_features, 5, glue_db_name)

    generate_data(bucket_name, data_size, 3, n_extra_features, 5, glue_db_name)

    generate_data(bucket_name, data_size, 3, n_extra_features, 5, glue_db_name)

    end_time = datetime.now()
    execution_time = end_time - start_time
    print("Data Generation Time: %s" % execution_time)

    response = f"Data Generation Time: {execution_time}"
    print(response)
    return {"statusCode": 200, "body": response}
