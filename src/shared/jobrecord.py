from dataclasses import dataclass, asdict
from enum import Enum

# Define Enum for job status
class JobStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobRecord:
    job_id: str
    job_name: str
    req_media_table: str
    req_kpi_table: str
    req_cost_table: str
    req_feature_table: str
    req_number_warmup: int
    req_number_samples: int
    req_number_chains: int
    req_compute_type: str
    req_compute_cores: str
    job_status: str
    req_memory_multp: str = None
    batch_job_id: str = None
    batch_job_status: str = None
    batch_job_status_time: str = None
    model_uri: str = None
    proc_data_size: str = None
    proc_n_media_channels: str = None
    proc_n_geos: str = None
    proc_compute_type: str = None
    proc_compute_cores: str = None
    proc_instance_type: str = None
    execution_time: str = None

    def dict(self):
        return {k: str(v) for k, v in asdict(self).items()}
