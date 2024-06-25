import json
import numpy as np
from typing import Any, Dict
from lightweight_mmm import lightweight_mmm
from io import BytesIO

# External serializer for the LightweightMMM class
class LightweightMMMSerializer:
    @staticmethod
    def serialize(obj: lightweight_mmm.LightweightMMM) -> BytesIO:
        if not isinstance(obj, lightweight_mmm.LightweightMMM):
            raise TypeError("Object is not an instance of LightweightMMM")

        data = {
            "model_name": obj.model_name,
            "_weekday_seasonality": obj._weekday_seasonality,
            "custom_priors": obj.custom_priors,
            "_prior_names": list(
                obj._prior_names
            ),  # frozenset needs to be converted to a list
            "n_media_channels": obj.n_media_channels,
            "n_geos": obj.n_geos,
            "_number_samples": obj._number_samples,
            "_number_warmup": obj._number_warmup,
            "_number_chains": obj._number_chains,
            "_train_media_size": obj._train_media_size,
            "_degrees_seasonality": obj._degrees_seasonality,
            "_seasonality_frequency": obj._seasonality_frequency,
            "media_names": obj.media_names,
        }
        json_data = json.dumps(data)
        # write standard data
        bytes_ = BytesIO()

        np_obj = np.savez_compressed(
            bytes_,
            _extra_features=obj._extra_features,
            _media_prior=obj._media_prior,
            _target=obj._target,
            media=obj.media,
            trace_ad_effect_retention_rate=obj.trace["ad_effect_retention_rate"],
            trace_channel_coef_media=obj.trace["channel_coef_media"],
            trace_coef_extra_features=obj.trace["coef_extra_features"],
            trace_coef_media=obj.trace["coef_media"],
            trace_coef_seasonality=obj.trace["coef_seasonality"],
            trace_coef_trend=obj.trace["coef_trend"],
            trace_expo_trend=obj.trace["expo_trend"],
            trace_exponent=obj.trace["exponent"],
            trace_gamma_seasonality=obj.trace["gamma_seasonality"],
            trace_intercept=obj.trace["intercept"],
            trace_media_transformed=obj.trace["media_transformed"],
            trace_mu=obj.trace["mu"],
            trace_peak_effect_delay=obj.trace["peak_effect_delay"],
            trace_sigma=obj.trace["sigma"],
        )
        bytes_.seek(0)

        return json_data, bytes_

    @staticmethod
    def deserialize(numpy_bytes, json_bytes) -> lightweight_mmm.LightweightMMM:
        # Parse the JSON string back to a dictionary
        json_data = json.load(json_bytes)
        numpy_obj = np.load(numpy_bytes, allow_pickle=True)
        # Create the instance of LightweightMMM with the non-underscored attributes
        loaded_mmm_model = lightweight_mmm.LightweightMMM(json_data["model_name"])

        # Manually set attributes from JSON

        loaded_mmm_model._weekday_seasonality = json_data["_weekday_seasonality"]
        loaded_mmm_model.custom_priors = json_data["custom_priors"]
        loaded_mmm_model._prior_names = frozenset(json_data["_prior_names"])
        loaded_mmm_model.n_media_channels = json_data["n_media_channels"]
        loaded_mmm_model.n_geos = json_data["n_geos"]
        loaded_mmm_model._number_samples = json_data["_number_samples"]
        loaded_mmm_model._number_warmup = json_data["_number_warmup"]
        loaded_mmm_model._number_chains = json_data["_number_chains"]
        loaded_mmm_model._train_media_size = json_data["_train_media_size"]
        loaded_mmm_model._degrees_seasonality = json_data["_degrees_seasonality"]
        loaded_mmm_model._seasonality_frequency = json_data["_seasonality_frequency"]
        loaded_mmm_model.media_names = json_data["media_names"]

        # Manually set attributes from numpy binary

        loaded_mmm_model._extra_features = numpy_obj["_extra_features"]
        loaded_mmm_model._media_prior = numpy_obj["_media_prior"]
        loaded_mmm_model._target = numpy_obj["_target"]
        loaded_mmm_model.media = numpy_obj["media"]

        loaded_mmm_model.trace = {
            "ad_effect_retention_rate": numpy_obj["trace_ad_effect_retention_rate"],
            "channel_coef_media": numpy_obj["trace_channel_coef_media"],
            "coef_extra_features": numpy_obj["trace_coef_extra_features"],
            "coef_media": numpy_obj["trace_coef_media"],
            "coef_seasonality": numpy_obj["trace_coef_seasonality"],
            "coef_trend": numpy_obj["trace_coef_trend"],
            "expo_trend": numpy_obj["trace_expo_trend"],
            "exponent": numpy_obj["trace_exponent"],
            "gamma_seasonality": numpy_obj["trace_gamma_seasonality"],
            "intercept": numpy_obj["trace_intercept"],
            "media_transformed": numpy_obj["trace_media_transformed"],
            "mu": numpy_obj["trace_mu"],
            "peak_effect_delay": numpy_obj["trace_peak_effect_delay"],
            "sigma": numpy_obj["trace_sigma"],
        }

        return loaded_mmm_model
