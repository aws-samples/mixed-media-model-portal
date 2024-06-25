"use client";
import {
  TableContainer,
  Table,
  Thead,
  Th,
  Tr,
  Tbody,
  Td,
  Center,
  Spinner,
  Button,
} from "@chakra-ui/react";
import { JobRecord } from "./JobRecord";
import { useEffect, useRef, useState } from "react";
import { fetchAuthSession } from "@aws-amplify/auth";
import axios from "axios";
import { useEnv } from "./useEnv";

interface JobTableProps {
  setSelectedItem: (item: JobRecord | null) => void;
  targetRef: (React.RefObject<HTMLDivElement>);
}

async function getIdToken() {
  try {
    const { accessToken, idToken } = (await fetchAuthSession()).tokens ?? {};
    return idToken;
  } catch (err) {
    console.log(err);
  }
}


export default function JobTable({ setSelectedItem, targetRef }: JobTableProps) {
  const [data, setData] = useState<JobRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const handleScrollToPosition = () => {
    if (targetRef.current) {
      targetRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handleButtonClick = (id: string) => {
    const selectedItem = data.find((item) => item.job_id === id);
    
    if (selectedItem) {
      setSelectedItem(selectedItem);
    }
  };

  const { env } = useEnv();

  if (!env) return <>loading...</>;

  useEffect(() => {
    const apiUrl = env.apiEndpoint;

    getIdToken().then((idToken) => {
      const axiosInstance = axios.create({
        baseURL: apiUrl,
        headers: {
          Authorization: `Bearer ${idToken}`,
          "Content-Type": "application/json",
        },
        withCredentials: false,
      });

      axiosInstance
        .get("/frontend/jobs")
        .then((response) => {
          setData(response.data.items);
          setLoading(false);
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  }, []);

  return (
    <>
      <TableContainer>
        <Table variant="simple" size="sm">
          <Thead>
            <Tr>
              <Th>Job Id</Th>
              <Th>Job Name</Th>
              <Th>Training Time</Th>
              <Th>Compute Type</Th>
              <Th>Cores</Th>
              <Th>Job Status</Th>
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {loading ? (
              <Tr>
                <Td colSpan={8}>
                  <Center>
                    <Spinner
                      thickness="4px"
                      speed="0.65s"
                      emptyColor="gray.200"
                      color="blue.500"
                      size="xl"
                    />
                  </Center>
                </Td>
              </Tr>
            ) : (
              data.map((item, index) => (
                <Tr key={index}>
                  <Td>{item.job_id}</Td>
                  <Td>{item.job_name}</Td>
                  <Td>{item.execution_time}</Td>
                  <Td>{item.req_compute_type}</Td>
                  <Td>{item.req_compute_cores}</Td>
                  <Td>{item.job_status}</Td>
                  <Td>
                    <Button
                      size="xs"
                      onClick={() => handleButtonClick(item.job_id)}
                    >
                      Details
                    </Button>
                  </Td>
                </Tr>
              ))
            )}
          </Tbody>
        </Table>
      </TableContainer>
    </>
  );
}
