"use client";
import {
  Center,
  Heading,
  Spinner,
  VStack,
} from "@chakra-ui/react";
import { JobRecord } from "./JobRecord";
import { useEffect, useState } from "react";
import { fetchAuthSession } from "aws-amplify/auth";
import axios from "axios";
import { useEnv } from "./useEnv";
import {
  VictoryChart,
  VictoryStack,
  VictoryGroup,
  VictoryArea,
  VictoryAxis,
  VictoryLegend,
  VictoryVoronoiContainer,
} from "victory";

interface DataPoint {
  x: string;
  y: number;
}

interface LineGraphData {
  id: string;
  data: DataPoint[];
}

interface ContributionLineChartProps {
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
const labelStyle = {
  axisLabel: {
    fontsize: 13
  }
};

export default function ContributionLineChart({ selectedItem, targetRef }: ContributionLineChartProps) {
  const [loadingGraph, setLoadingGraph] = useState(true);
  const [graphData, setGraphData] = useState<LineGraphData[]>([]);
  const { env } = useEnv();

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
              graph_type: "media_baseline_contribution_area_plot",
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
          Attribution over time
        </Heading>
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
            <VictoryChart
              width={800}
              containerComponent={
                <VictoryVoronoiContainer
                  labels={({ datum }) =>
                    `${
                      graphData.map((obj) => ({ name: obj.id }))[
                        datum._stack - 1
                      ].name
                    }, ${datum.x}, ${Math.round(datum.y)}`
                  }
                />
              }
            >
              <VictoryStack colorScale={"warm"} name={"vicstack1"}>
                {graphData.map((item) => (

                  <VictoryGroup data={item.data} name={item.id} key={item.id}>
                    <VictoryAxis
                      tickValues={graphData[0].data.map((point, index) =>
                        index % 20 === 0 ? point.x : ""
                      )}
                      key={`${item.id}axis1`}
                      label="Period"
                      style={{
                        axisLabel: { fontSize: 8, padding: 40 },
                      }}
                    />
                    <VictoryAxis
                      dependentAxis
                      key={`${item.id}axis2`}
                      label="Baseline & Media Channels Attribution"
                      style={{
                        axisLabel: { fontSize: 8, padding: 40 },
                      }}
                    />
                    <VictoryArea key={`${item.id}area`} />
                  </VictoryGroup>
                ))}
              </VictoryStack>
              <VictoryLegend
                data={graphData.map((obj) => ({ name: obj.id }))}
                standalone={false}
                centerTitle
                orientation="horizontal"
                colorScale={"warm"}
                titleOrientation="bottom"
              />
            </VictoryChart>
          </>
        )}
      </VStack>
    </>
  );
  
}
