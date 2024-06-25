from dataclasses import dataclass, asdict

@dataclass
class MMMJobType:
    job_definition_name: str
    job_queue_name: str
    job_container_name: str
    job_compute_env_name: str
@dataclass
class MMMJobSetup:
    gpu_low: MMMJobType = MMMJobType("", "", "", "")
    gpu_high: MMMJobType = MMMJobType("", "", "", "")
    cpu: MMMJobType = MMMJobType("", "", "", "")

    def dict(self):
        return {k: str(v) for k, v in asdict(self).items()}
