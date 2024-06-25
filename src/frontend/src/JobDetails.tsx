"use client";
import { Box, Text, Heading, Grid, Flex } from "@chakra-ui/react";
import { JobRecord } from "./JobRecord";

interface JobDetailsProps {
  selectedItem: JobRecord;
}

export default function JobDetails({ selectedItem }: JobDetailsProps) {
  return (
    <>
      <Flex align="center">
        <h2>Details for {selectedItem.job_id}</h2>
      </Flex>

      <Grid
        templateColumns="repeat(auto-fill, minmax(200px, 1fr))"
        gap={4}
        fontSize="xs"
      >
        <Heading as="h2" size="md" mb={3}>
          {selectedItem.job_name}
        </Heading>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Job Status:
          </Text>
          <Text>{selectedItem.job_status}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Media Data Table:
          </Text>
          <Text>{selectedItem.req_media_table}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            KPI Data Table:
          </Text>
          <Text>{selectedItem.req_kpi_table}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Cost Data Table:
          </Text>
          <Text>{selectedItem.req_cost_table}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Feature Data Table:
          </Text>
          <Text>{selectedItem.req_feature_table}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Warmup Cycles:
          </Text>
          <Text>{selectedItem.req_number_warmup}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Samples:
          </Text>
          <Text>{selectedItem.req_number_samples}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Chains:
          </Text>
          <Text>{selectedItem.req_number_chains}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Requested Compute Type:
          </Text>
          <Text>{selectedItem.req_compute_type}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Requested Compute Cores:
          </Text>
          <Text>{selectedItem.req_compute_cores}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Batch Job ID:
          </Text>
          <Text>{selectedItem.batch_job_id ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Batch Job Status:
          </Text>
          <Text>{selectedItem.batch_job_status ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Batch Job Status Time:
          </Text>
          <Text>{selectedItem.batch_job_status_time ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Model URI:
          </Text>
          <Text>{selectedItem.model_uri ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Processed Data Size:
          </Text>
          <Text>{selectedItem.proc_data_size ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Processed Media Channels:
          </Text>
          <Text>{selectedItem.proc_n_media_channels ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Processed Geos:
          </Text>
          <Text>{selectedItem.proc_n_geos ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Processed Compute Type:
          </Text>
          <Text>{selectedItem.proc_compute_type ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Processed Compute Cores:
          </Text>
          <Text>{selectedItem.proc_compute_cores ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Processed Instance Type:
          </Text>
          <Text>{selectedItem.proc_instance_type ?? "N/A"}</Text>
        </Box>
        <Box>
          <Text fontWeight="bold" textTransform="uppercase">
            Execution Time:
          </Text>
          <Text>{selectedItem.execution_time ?? "N/A"}</Text>
        </Box>
      </Grid>
    </>
  );
}
