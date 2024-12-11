# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.10

# Install system dependencies
RUN yum update -y && \
    yum install -y gcc python3-devel git openblas-devel lapack-devel && \
    yum clean all && \
    rm -rf /var/cache/yum

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Clone the specific branch of cloudos-cli
RUN git clone https://github.com/lifebit-ai/cloudos-cli.git cloudos-cli && \
    cd cloudos-cli && \
    git checkout remove-numpy

# Install dependencies
RUN pip install --no-cache-dir \
    numpy==1.21.6 \
    urllib3==1.26.15 \
    ./cloudos-cli

# Copy data
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py

# Set the CMD to your lambda handler
CMD [ "lambda_function.lambda_handler" ]
