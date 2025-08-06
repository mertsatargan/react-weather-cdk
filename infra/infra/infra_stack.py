from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,   
)
from constructs import Construct
class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "WeatherVPC", max_azs=2)

        # ECS Cluster

        cluster = ecs.Cluster(self,"WeatherCluster", vpc=vpc)

        # Fargate Service + Load Balancer

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "WeatherService",
            cluster =cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            public_load_balancer=True,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry(
                    "420053132520.dkr.ecr.us-east-1.amazonaws.com/react-weather-cdk:latest"
                )
            )
        )

        execution_role = fargate_service.task_definition.obtain_execution_role()

        execution_role.add_to_policy(iam.PolicyStatement(
            actions=["ecr:GetAuthorizationToken",
                     "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"],
            resources=["*"]  # This action requires * for resources
        ))
