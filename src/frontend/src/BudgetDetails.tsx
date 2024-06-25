"use client";
import {
  Box,
  Flex,
  Text,
  Button,
  VStack,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Center,
  Spinner,
  Heading,
  HStack,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { useEnv } from "./useEnv";
import { JobRecord } from "./JobRecord";
import { fetchAuthSession } from "aws-amplify/auth";
import axios from "axios";
import {
  VictoryChart,
  VictoryBar,
  VictoryGroup,
} from "victory";
import { Style } from "victory-core";
import React from "react";

const myColors = Style.getColorScale("warm");
const legendLabels = [
  { name: "previous budget allocation" },
  { name: "optimized budget allocation" },
];

interface BudgetDetailsProps {
  selectedItem: JobRecord;
}

interface DataPoint {
  x: string;
  y: number;
}

interface BarAllocationGraphData {
  id: string;
  data: DataPoint[];
}
interface TargetVariableGraphData {
  data: DataPoint[];
}
interface BudgetGraphData {
  graph1: BarAllocationGraphData[];
  graph2: TargetVariableGraphData;
}

async function getIdToken() {
  try {
    const { accessToken, idToken } = (await fetchAuthSession()).tokens ?? {};
    return idToken;
  } catch (err) {
    console.log(err);
  }
}

export default function BudgetDetails({ selectedItem }: BudgetDetailsProps) {
  const [sliderValue, setSliderValue] = useState(50000);
  const [loadingBudget, setLoadingBudget] = useState(false);
  const [graphData, setGraphData] = useState<BudgetGraphData | undefined>(
    undefined
  );
  const { env } = useEnv();

  useEffect(() => {
    if (
      selectedItem &&
      selectedItem.job_status === "completed" &&
      loadingBudget
    ) {
      getIdToken().then((idToken) => {
        const apiUrl = env?.apiEndpoint;

        const axiosInstance = axios.create({
          baseURL: apiUrl,
          headers: {
            Authorization: `Bearer ${idToken}`, 
            "Content-Type": "application/json", 
          },
        });

        axiosInstance
          .get("/backend/budget", {
            params: {
              job_id: selectedItem.job_id,
              budget: sliderValue,
            },
          })
          .then((response) => {
            setGraphData(response.data);
            setLoadingBudget(false);
          })
          .catch((error) => {
            console.error("Error:", error);
          });
      });
    }
  }, [selectedItem, loadingBudget]);

  const handleOptimizeBudget = () => {
    setLoadingBudget(true);
  };

  const handleSliderChange = (value: number) => {
    setSliderValue(value);
  };

  const formatCurrency = (
    value: number,
    currency: string = "USD",
    locale: string = "en-US"
  ): string => {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: currency,
    }).format(value);
  };

  if (!env) return <>loading...</>;

  return (
    <>
      <Flex align="center">
        <VStack>
          <Heading as="h2" size="md" mb={3}>
            Budget Optimization
          </Heading>
          <Text>12 Week Budget</Text>
          <Slider
            min={1}
            max={1000000}
            step={1}
            value={sliderValue}
            onChange={handleSliderChange}
            aria-label="slider-ex"
            colorScheme="blue"
            flex="1"
            mr={4}
          >
            <SliderTrack>
              <SliderFilledTrack />
            </SliderTrack>
            <SliderThumb />
          </Slider>
          <Box>
            <Text fontSize="lg" fontWeight="bold">
              {formatCurrency(sliderValue)}
            </Text>
          </Box>
          <Button onClick={handleOptimizeBudget}>Optimize Budget</Button>
          {loadingBudget ? (
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
              <HStack>
                {graphData ? (
                  <>
                    <VStack>
                      <Text fontSize="xs">
                        Before and After Optimization Budget Allocation
                        Comparison
                      </Text>

                      <VictoryChart width={400}>
                        <VictoryGroup offset={30}>
                          {graphData?.graph1.map((item, index) => (
                            <VictoryBar
                              key={item.id}
                              style={{
                                data: {
                                  fill: myColors[index + 2],
                                },
                              }}
                              data={item.data}
                              labels={({ datum }) =>
                                `${(datum.y1_label * 100).toFixed(0)}%`
                              }
                            />
                          ))}
                        </VictoryGroup>
                      </VictoryChart>
                    </VStack>
                  </>
                ) : null}
                {graphData && graphData.graph2 && graphData.graph2.data ? (
                  <>
                    <VStack>
                      <Text fontSize="xs">
                        Pre Post Optimization Target Variable Comparison
                      </Text>
                      <VictoryChart width={400} domainPadding={200}>
                        <VictoryBar
                          style={{
                            data: {
                              fill: myColors[1],
                            },
                          }}
                          data={graphData.graph2.data}
                        />
                      </VictoryChart>
                    </VStack>
                  </>
                ) : null}
              </HStack>
            </>
          )}
        </VStack>
      </Flex>
    </>
  );
}
