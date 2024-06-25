FROM public.ecr.aws/lambda/python:3.11

COPY ./lambda/data_generator/requirements.txt ./
RUN pip install -r requirements.txt
RUN pip install --no-deps lightweight_mmm==0.1.9

COPY ./tensorflow_custom ./
RUN python setup.py install

RUN pip cache purge
COPY ./lambda/data_generator/lambda-handler.py ./
CMD ["lambda-handler.handler"]