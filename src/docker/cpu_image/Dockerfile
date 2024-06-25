FROM ubuntu:20.04

# Update the system
RUN apt-get update --allow-releaseinfo-change-suite && apt-get install -y

RUN apt install wget -y

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
RUN bash ~/miniconda.sh -b -p $HOME/miniconda
ENV PATH="/root/miniconda/bin:${PATH}"

# Copy content of this dir to the docker image
COPY ./docker/application/environment.yaml/ /app/environment.yaml
WORKDIR /app

# Create the conda environment
RUN conda env create -f environment.yaml

# Use pip3 to install requirements - split to preserve order

RUN conda run -n batch-docker-conda pip3 install --upgrade pip
RUN conda run -n batch-docker-conda pip3 install --upgrade "jax[cpu]"==0.4.23
RUN conda run -n batch-docker-conda pip3 install lightweight_mmm==0.1.9
RUN conda run -n batch-docker-conda pip3 install boto3==1.26.149
RUN conda run -n batch-docker-conda pip3 install awswrangler
RUN conda run -n batch-docker-conda pip3 install shortuuid
RUN conda run -n batch-docker-conda pip3 install ec2-metadata
RUN conda run -n batch-docker-conda pip3 install mpld3
RUN conda run -n batch-docker-conda pip3 install "scipy<1.13"

# Copy the main application last so that code changes dont require rebuilding the image completely
COPY ./docker/application /app
COPY ./shared /app

# Run the batch job
#ENTRYPOINT ["conda", "run", "-n", "batch-docker-conda-gpu", "python", "maintest.py"]
