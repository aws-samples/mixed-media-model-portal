import React, { useRef, useState } from "react";
import {
  ChakraProvider,
  theme,
  VStack,
  Card,
  CardBody,
  Center,
  SimpleGrid,
  Box,
} from "@chakra-ui/react";
import NavWithAction from "./NavBar";
import NewJobMultiStep from "./NewJob";
import BudgetDetails from "./BudgetDetails";
import JobDetails from "./JobDetails";
import ContributionLineChart from "./ContributionLineChart";
import ContributionPercentageBarChart from "./ContributionPercentageBarChart";
import JobTable from "./JobTable";
import { Amplify } from "aws-amplify";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { useEnv } from "./useEnv";
import { JobRecord } from "./JobRecord";

function App() {
  const [selectedItem, setSelectedItem] = useState<JobRecord | null>(null);
  const { env } = useEnv();

  const targetRef = useRef<HTMLDivElement>(null);

  if (!env) return <>Loading...</>;
  
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: env.userPoolId,
        userPoolClientId: env.userPoolClientId,
      },
    },
  });
  return (
    <Authenticator hideSignUp={true}>
      {({ signOut, user }) => {
        return (
          <ChakraProvider theme={theme}>
            <NavWithAction user={user}>
              <VStack spacing={4} align="stretch">
                <Card size="sm">
                  <CardBody>
                    <NewJobMultiStep></NewJobMultiStep>
                  </CardBody>
                </Card>

                <Card size="sm">
                  <CardBody>
                    <JobTable
                      setSelectedItem={setSelectedItem}
                      targetRef={targetRef}
                    />
                  </CardBody>
                </Card>
                <Box ref={targetRef}>
                  {selectedItem && (
                    <SimpleGrid columns={2} spacing={5}>
                      <Card size="sm">
                        <CardBody>
                          <JobDetails selectedItem={selectedItem} />
                        </CardBody>
                      </Card>
                      {selectedItem.job_status === "completed" && (
                        <>
                          <Card size="sm">
                            <CardBody>
                              <Center>
                                <ContributionLineChart
                                  selectedItem={selectedItem}
                                  targetRef={targetRef}
                                />
                              </Center>
                            </CardBody>
                          </Card>
                          <Card size="sm">
                            <CardBody>
                              <BudgetDetails selectedItem={selectedItem} />
                            </CardBody>
                          </Card>
                          <Card size="sm">
                            <CardBody>
                              <Center>
                                <ContributionPercentageBarChart
                                  selectedItem={selectedItem}
                                  targetRef={targetRef}
                                />
                              </Center>
                            </CardBody>
                          </Card>
                        </>
                      )}
                    </SimpleGrid>
                  )}
                </Box>
              </VStack>
            </NavWithAction>
          </ChakraProvider>
        );
      }}
    </Authenticator>
  );
}

export default App;
