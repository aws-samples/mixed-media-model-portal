FROM nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04
#FROM nvidia/cuda:12.2.2-base-ubuntu22.04
#FROM nvcr.io/nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04
# Update the system
RUN apt-get update --allow-releaseinfo-change-suite && apt-get install -y

RUN apt-get install wget -y

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
RUN bash ~/miniconda.sh -b -p $HOME/miniconda
ENV PATH="/root/miniconda/bin:${PATH}"

COPY ./docker/application/environment.yaml/ /app/environment.yaml
WORKDIR /app

# Create the conda environment
RUN conda env create -f environment.yaml

RUN conda run -n batch-docker-conda pip3 install --upgrade "jax[cuda12_local]"==0.4.23 -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
RUN conda run -n batch-docker-conda pip3 install lightweight_mmm==0.1.9
RUN conda run -n batch-docker-conda pip3 install boto3==1.26.149
RUN conda run -n batch-docker-conda pip3 install awswrangler
RUN conda run -n batch-docker-conda pip3 install gpustat
RUN conda run -n batch-docker-conda pip3 install shortuuid
RUN conda run -n batch-docker-conda pip3 install ec2-metadata
RUN conda run -n batch-docker-conda pip3 install mpld3
RUN conda run -n batch-docker-conda pip3 install "scipy<1.13"

# Copy content of this dir to the docker image
COPY ./docker/application/ /app
COPY ./shared /app
WORKDIR /app
