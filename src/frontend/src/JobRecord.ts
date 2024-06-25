export interface JobRecord {
  job_id: string;
  job_name: string;
  req_media_table: string;
  req_kpi_table: string;
  req_cost_table: string;
  req_feature_table: string;
  req_number_warmup: string;
  req_number_samples: string;
  req_number_chains: string;
  req_compute_type: string;
  req_compute_cores: string;
  job_status: string;
  batch_job_id?: string | null;
  batch_job_status?: string | null;
  batch_job_status_time?: string | null;
  model_uri?: string | null;
  proc_data_size?: string | null;
  proc_n_media_channels?: string | null;
  proc_n_geos?: string | null;
  proc_compute_type?: string | null;
  proc_compute_cores?: string | null;
  proc_instance_type?: string | null;
  execution_time?: string | null;
}
