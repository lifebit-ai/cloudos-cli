# cloudos-py-aws-lambda-function
A demonstration of cloudos python package usage with AWS Lambda function

## Build and deploy the docker image to AWS ECR 

```bash
docker build -t cloudos-cli-for-aws-lambda .

aws ecr get-login-password --region <aws_region> | docker login --username AWS --password-stdin <aws_account>.dkr.ecr.<aws_region>.amazonaws.co

docker tag cloudos-cli-for-aws-lambda:latest <aws_account>.dkr.ecr.<aws_region>.amazonaws.com/lifebit/cloudos-cli-for-aws-lambda:latest
docker push <aws_account>.dkr.ecr.<aws_region>.amazonaws.com/lifebit/cloudos-cli-for-aws-lambda:latest
```

