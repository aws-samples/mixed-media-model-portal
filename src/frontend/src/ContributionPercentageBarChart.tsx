"use client";
import { Center, Heading, Spinner, VStack, Text } from "@chakra-ui/react";
import { JobRecord } from "./JobRecord";
import { useEffect, useState } from "react";
import { fetchAuthSession } from "aws-amplify/auth";
import axios from "axios";
import { useEnv } from "./useEnv";
import { VictoryChart, VictoryBar, VictoryErrorBar } from "victory";
import { Style } from "victory-core";

interface BarGraphData {
  x: string;
  y: number;
  errorX: number;
  errorY: number;
}

interface ContributionPercentageBarChartProps {
  selectedItem: JobRecord;
  targetRef: React.RefObject<HTMLDivElement>;
}
async function getIdToken() {
  try {
    const { accessToken, idToken } = (await fetchAuthSession()).tokens ?? {};
    return idToken;
  } catch (err) {
    console.log(err);
  }
}
export default function ContributionPercentageBarChart({
  selectedItem,
  targetRef,
}: ContributionPercentageBarChartProps) {
  const [loadingGraph, setLoadingGraph] = useState(true);
  const [graphData, setGraphData] = useState<BarGraphData[]>([]);
  const { env } = useEnv();
  const myColors = Style.getColorScale("warm");
  const handleScrollToPosition = () => {
    if (targetRef.current) {
      targetRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  if (!env) return <>loading...</>;

  useEffect(() => {
    setLoadingGraph(true);

    if (selectedItem && selectedItem.job_status === "completed") {
      getIdToken().then((idToken) => {
        const apiUrl = env.apiEndpoint;

        const axiosInstance = axios.create({
          baseURL: apiUrl,
          headers: {
            Authorization: `Bearer ${idToken}`,
            "Content-Type": "application/json",
          },
        });

        axiosInstance
          .get(`/frontend/jobs/${selectedItem.job_id}/graph`, {
            params: {
              graph_type: "bars_media_metrics",
            },
          })
          .then((response) => {
            setGraphData(response.data);
            setLoadingGraph(false);
            handleScrollToPosition();
          })
          .catch((error) => {
            console.error("Error:", error);
          });
      });
    }
  }, [selectedItem]);

  return (
    <>
      <VStack>
        <Heading as="h2" size="md" mb={3}>
          Media contribution percentage
        </Heading>
        <Text fontSize={"xs"}>Error bars show 0.05 - 0.95 credibility interval</Text>
        {loadingGraph ? (
          <Center>
            <Spinner
              thickness="4px"
              speed="0.65s"
              emptyColor="gray.200"
              color="blue.500"
              size="xl"
            />
          </Center>
        ) : (
          <>
            <VictoryChart domainPadding={12} width={800}>
              <VictoryBar
                style={{
                  data: {
                    fill: ({ datum, index }) => {
                      return myColors[index ?? 0];
                    },
                  },
                }}
                data={graphData}
              />
              <VictoryErrorBar data={graphData} />
            </VictoryChart>
          </>
        )}
      </VStack>
    </>
  );
}
