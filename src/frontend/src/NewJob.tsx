"use client";

import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import {
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  ModalFooter,
  useDisclosure,
  FormControl,
  FormLabel,
  Select,
  FormErrorMessage,
  Stack,
  Card,
  CardHeader,
  Heading,
  CardBody,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Grid,
  GridItem,
  Container,
  useBoolean,
  Input,
} from "@chakra-ui/react";
import { fetchAuthSession } from "@aws-amplify/auth";
import axios from "axios";
import { useEnv } from "./useEnv";

export default function NewJobMultiStep() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { control, handleSubmit, reset } = useForm();
  const [tables, setTables] = useState<String[]>([]);
  const [loadingTables, setLoadingTables] = useState(true);
  const [isLoading, setLoading] = useBoolean(false);
  const { env } = useEnv();

  if (!env) return <>loading...</>;

  const apiUrl = env.apiEndpoint;

  async function getIdToken() {
    try {
      const { accessToken, idToken } = (await fetchAuthSession()).tokens ?? {};
      return idToken;
    } catch (err) {
      console.log(err);
    }
  }

  useEffect(() => {
    getIdToken().then((idToken) => {

      const axiosInstance = axios.create({
        baseURL: apiUrl,
        headers: {
          Authorization: `Bearer ${idToken}`, 
          "Content-Type": "application/json",
        },
      });

      axiosInstance
        .get("/frontend/tables")
        .then((response) => {
          setTables(response.data);
          setLoadingTables(false);
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  }, []);

  const submit = async (data: any) => {
    setLoading.on();
    setTimeout(() => {
      setLoading.off();
      alert(JSON.stringify(data, null, 2));
      getIdToken().then((idToken) => {

        const axiosInstance = axios.create({
          baseURL: apiUrl,
          headers: {
            Authorization: `Bearer ${idToken}`,
            "Content-Type": "application/json",
          },
        });

        axiosInstance
          .put("/frontend/jobs", data) 
          .then((response) => {
          })
          .catch((error) => {
            console.error("Error:", error);
          });
      });
    }, 1200);
    handleClose();
  };

  const handleClose = () => {
    onClose();
  };

  return (
    <>
      <Button onClick={onOpen}>Train New Model</Button>
      <Modal isOpen={isOpen} onClose={handleClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Submit New Training Job</ModalHeader>
          <ModalCloseButton />
          <Container as="form" mb={12} onSubmit={handleSubmit(submit)}>
            <ModalBody>
              <Stack>
                <Card variant="outline">
                  <CardHeader mb="0" pb="0">
                    <Heading size="md" color="grey">
                      Model Input
                    </Heading>
                  </CardHeader>
                  <CardBody mt="0" pt="0">
                    <Stack direction="row">
                      <Controller
                        control={control}
                        name="job_name"
                        rules={{
                          required: "Please enter a job description",
                        }}
                        render={({
                          field: { onChange, onBlur, value, name, ref },
                          fieldState: { error },
                        }) => (
                          <FormControl py={4} isInvalid={!!error} id="job_name">
                            <FormLabel>Job Name</FormLabel>

                            <Input
                              name={name}
                              ref={ref}
                              onChange={onChange}
                              onBlur={onBlur}
                              value={value}
                            />
                            <FormErrorMessage>
                              {error && error.message}
                            </FormErrorMessage>
                          </FormControl>
                        )}
                      />
                    </Stack>
                    <Stack direction="row">
                      <Controller
                        control={control}
                        name="req_kpi_table"
                        rules={{
                          required: "Please choose a source table for KPI data",
                        }}
                        render={({
                          field: { onChange, onBlur, value, name, ref },
                          fieldState: { error },
                        }) => (
                          <FormControl
                            py={4}
                            isInvalid={!!error}
                            id="req_kpi_table"
                          >
                            <FormLabel>KPI Data Table</FormLabel>

                            <Select
                              name={name}
                              ref={ref}
                              onChange={onChange}
                              onBlur={onBlur}
                              value={value}
                            >
                              <option selected hidden disabled value="">
                                Select table..
                              </option>
                              {tables
                                .filter((x) => x.startsWith("kpi"))
                                .map((x, y) => (
                                  <option key={y}>{x}</option>
                                ))}
                            </Select>

                            <FormErrorMessage>
                              {error && error.message}
                            </FormErrorMessage>
                          </FormControl>
                        )}
                      />
                      <Controller
                        control={control}
                        name="req_cost_table"
                        rules={{
                          required:
                            "Please choose a source table for cost data",
                        }}
                        render={({
                          field: { onChange, onBlur, value, name, ref },
                          fieldState: { error },
                        }) => (
                          <FormControl
                            py={4}
                            isInvalid={!!error}
                            id="req_cost_table"
                          >
                            <FormLabel>Cost Data Table</FormLabel>

                            <Select
                              name={name}
                              ref={ref}
                              onChange={onChange}
                              onBlur={onBlur}
                              value={value}
                            >
                              <option selected hidden disabled value="">
                                Select table..
                              </option>
                              {tables
                                .filter((x) => x.startsWith("cost"))
                                .map((x, y) => (
                                  <option key={y}>{x}</option>
                                ))}
                            </Select>

                            <FormErrorMessage>
                              {error && error.message}
                            </FormErrorMessage>
                          </FormControl>
                        )}
                      />
                    </Stack>
                    <Stack direction="row">
                      <Controller
                        control={control}
                        name="req_feature_table"
                        rules={{
                          required:
                            "Please choose a source table for Feature data",
                        }}
                        render={({
                          field: { onChange, onBlur, value, name, ref },
                          fieldState: { error },
                        }) => (
                          <FormControl
                            py={4}
                            isInvalid={!!error}
                            id="req_feature_table"
                          >
                            <FormLabel>Feature Data Table</FormLabel>

                            <Select
                              name={name}
                              ref={ref}
                              onChange={onChange}
                              onBlur={onBlur}
                              value={value}
                            >
                              <option selected hidden disabled value="">
                                Select table..
                              </option>
                              {tables
                                .filter((x) => x.startsWith("feature"))
                                .map((x, y) => (
                                  <option key={y}>{x}</option>
                                ))}
                            </Select>

                            <FormErrorMessage>
                              {error && error.message}
                            </FormErrorMessage>
                          </FormControl>
                        )}
                      />
                      <Controller
                        control={control}
                        name="req_media_table"
                        rules={{
                          required:
                            "Please choose a source table for Media data",
                        }}
                        render={({
                          field: { onChange, onBlur, value, name, ref },
                          fieldState: { error },
                        }) => (
                          <FormControl
                            py={4}
                            isInvalid={!!error}
                            id="req_media_table"
                          >
                            <FormLabel>Media Data Table</FormLabel>

                            <Select
                              name={name}
                              ref={ref}
                              onChange={onChange}
                              onBlur={onBlur}
                              value={value}
                            >
                              <option selected hidden disabled value="">
                                Select table..
                              </option>
                              {tables
                                .filter((x) => x.startsWith("media"))
                                .map((x, y) => (
                                  <option key={y}>{x}</option>
                                ))}
                            </Select>

                            <FormErrorMessage>
                              {error && error.message}
                            </FormErrorMessage>
                          </FormControl>
                        )}
                      />
                    </Stack>
                  </CardBody>
                </Card>

                <Card variant="outline">
                  <CardHeader mb="0" pb="0">
                    <Heading size="md" color="grey">
                      Model Parameters
                    </Heading>
                  </CardHeader>
                  <CardBody mt="0" pt="0">
                    <Controller
                      control={control}
                      name="req_number_warmup"
                      rules={{
                        required:
                          "Please choose a valid number of warmup cycles (1 - 10000)",
                      }}
                      defaultValue={1000}
                      render={({
                        field: { onChange, onBlur, value, name, ref },
                        fieldState: { error },
                      }) => (
                        <FormControl
                          py={4}
                          isInvalid={!!error}
                          id="req_number_warmup"
                          mb="0"
                          pb="0"
                        >
                          <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                            <GridItem colSpan={1}>
                              <FormLabel>Warmup cycles</FormLabel>
                            </GridItem>
                            <GridItem colSpan={2}>
                              <NumberInput
                                name={name}
                                ref={ref}
                                onChange={onChange}
                                onBlur={onBlur}
                                value={value}
                                defaultValue={1000}
                              >
                                <NumberInputField />
                                <NumberInputStepper>
                                  <NumberIncrementStepper />
                                  <NumberDecrementStepper />
                                </NumberInputStepper>
                              </NumberInput>
                              <FormErrorMessage>
                                {error && error.message}
                              </FormErrorMessage>
                            </GridItem>
                            <GridItem colSpan={1}></GridItem>
                          </Grid>
                        </FormControl>
                      )}
                    />

                    <Controller
                      control={control}
                      name="req_number_samples"
                      rules={{
                        required:
                          "Please choose a valid number of samples (1 - 10000)",
                      }}
                      defaultValue={1000}
                      render={({
                        field: { onChange, onBlur, value, name, ref },
                        fieldState: { error },
                      }) => (
                        <FormControl
                          py={4}
                          isInvalid={!!error}
                          id="req_number_samples"
                          mb="0"
                          pb="0"
                          mt="0"
                          pt="0"
                        >
                          <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                            <GridItem colSpan={1}>
                              <FormLabel>Samples</FormLabel>
                            </GridItem>
                            <GridItem colSpan={2}>
                              <NumberInput
                                name={name}
                                ref={ref}
                                onChange={onChange}
                                onBlur={onBlur}
                                value={value}
                              >
                                <NumberInputField />
                                <NumberInputStepper>
                                  <NumberIncrementStepper />
                                  <NumberDecrementStepper />
                                </NumberInputStepper>
                              </NumberInput>

                              <FormErrorMessage>
                                {error && error.message}
                              </FormErrorMessage>
                            </GridItem>
                            <GridItem colSpan={1}></GridItem>
                          </Grid>
                        </FormControl>
                      )}
                    />

                    <Controller
                      control={control}
                      name="req_number_chains"
                      defaultValue={2}
                      rules={{
                        required:
                          "Please choose a valid number of chains (1 - 12)",
                      }}
                      render={({
                        field: { onChange, onBlur, value, name, ref },
                        fieldState: { error },
                      }) => (
                        <FormControl
                          py={4}
                          isInvalid={!!error}
                          id="req_number_chains"
                          mb="0"
                          pb="0"
                          mt="0"
                          pt="0"
                        >
                          <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                            <GridItem colSpan={1}>
                              <FormLabel>Number of Chains</FormLabel>
                            </GridItem>
                            <GridItem colSpan={2}>
                              <NumberInput
                                name={name}
                                ref={ref}
                                onChange={onChange}
                                onBlur={onBlur}
                                value={value}
                              >
                                <NumberInputField />
                                <NumberInputStepper>
                                  <NumberIncrementStepper />
                                  <NumberDecrementStepper />
                                </NumberInputStepper>
                              </NumberInput>
                              <FormErrorMessage>
                                {error && error.message}
                              </FormErrorMessage>
                            </GridItem>
                            <GridItem colSpan={1}></GridItem>
                          </Grid>
                        </FormControl>
                      )}
                    />

                    <Controller
                      control={control}
                      name="req_compute_type"
                      rules={{
                        required: "Please choose a source table for Media data",
                      }}
                      defaultValue="CPU"
                      render={({
                        field: { onChange, onBlur, value, name, ref },
                        fieldState: { error },
                      }) => (
                        <FormControl
                          py={4}
                          isInvalid={!!error}
                          id="req_compute_type"
                          mb="0"
                          pb="0"
                          mt="0"
                          pt="0"
                        >
                          <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                            <GridItem colSpan={1}>
                              <FormLabel>Compute Type</FormLabel>
                            </GridItem>
                            <GridItem colSpan={2}>
                              <Select
                                name={name}
                                ref={ref}
                                onChange={onChange}
                                onBlur={onBlur}
                                value={value}
                              >
                                <option key="0">CPU</option>
                                <option key="1">GPU (A10)</option>
                                <option key="2">GPU (H100)</option>
                              </Select>
                              <FormErrorMessage>
                                {error && error.message}
                              </FormErrorMessage>
                            </GridItem>
                            <GridItem colSpan={1}></GridItem>
                          </Grid>
                        </FormControl>
                      )}
                    />

                    <Controller
                      control={control}
                      name="req_compute_cores"
                      rules={{
                        required:
                          "Please choose a valid number of cores (1-8 GPU) or (1-192 CPU)",
                      }}
                      defaultValue={2}
                      render={({
                        field: { onChange, onBlur, value, name, ref },
                        fieldState: { error },
                      }) => (
                        <FormControl
                          py={4}
                          isInvalid={!!error}
                          id="req_compute_cores"
                          mt="0"
                          pt="0"
                        >
                          <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                            <GridItem colSpan={1}>
                              <FormLabel>Compute Cores</FormLabel>
                            </GridItem>
                            <GridItem colSpan={2}>
                              <Select
                                name={name}
                                ref={ref}
                                onChange={onChange}
                                onBlur={onBlur}
                                value={value}
                              >
                                <option key="0">1</option>
                                <option key="1">4</option>
                                <option key="2">8</option>
                                <option key="3">16</option>
                                <option key="4">32</option>
                                <option key="5">48</option>
                                <option key="6">64</option>
                                <option key="7">96</option>
                                <option key="8">128</option>
                              </Select>
                              <FormErrorMessage>
                                {error && error.message}
                              </FormErrorMessage>
                            </GridItem>
                            <GridItem colSpan={1}></GridItem>
                          </Grid>
                        </FormControl>
                      )}
                    />

                    <Controller
                      control={control}
                      name="req_memory_multp"
                      rules={{
                        required: "Please choose a memory multiplier",
                      }}
                      defaultValue={2}
                      render={({
                        field: { onChange, onBlur, value, name, ref },
                        fieldState: { error },
                      }) => (
                        <FormControl
                          py={4}
                          isInvalid={!!error}
                          id="req_memory_multp"
                          mt="0"
                          pt="0"
                        >
                          <Grid templateColumns="repeat(3, 1fr)" gap={6}>
                            <GridItem colSpan={1}>
                              <FormLabel>Memory Multiplier</FormLabel>
                            </GridItem>
                            <GridItem colSpan={2}>
                              <NumberInput
                                name={name}
                                ref={ref}
                                onChange={onChange}
                                onBlur={onBlur}
                                value={value}
                                defaultValue={2}
                              >
                                <NumberInputField />
                                <NumberInputStepper>
                                  <NumberIncrementStepper />
                                  <NumberDecrementStepper />
                                </NumberInputStepper>
                              </NumberInput>
                              <FormErrorMessage>
                                {error && error.message}
                              </FormErrorMessage>
                            </GridItem>
                            <GridItem colSpan={1}></GridItem>
                          </Grid>
                        </FormControl>
                      )}
                    />
                  </CardBody>
                </Card>
              </Stack>
            </ModalBody>

            <ModalFooter>
              <Button colorScheme="blue" mr={3} onClick={onClose}>
                Cancel
              </Button>
              <Button variant="ghost" type="submit">
                Submit
              </Button>
            </ModalFooter>
          </Container>
        </ModalContent>
      </Modal>
    </>
  );
}
