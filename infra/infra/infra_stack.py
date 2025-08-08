from aws_cdk import (
    Stack,
    Duration,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_cloudwatch_actions as cw_actions,
    RemovalPolicy,   
)
from constructs import Construct
class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "WeatherVPC", max_azs=2)

        # ECS Cluster

        cluster = ecs.Cluster(self,"WeatherCluster", vpc=vpc)

        # Log Group 

        log_group = logs.LogGroup(
            self, "WeatherAppLogGroup",
            log_group_name = "ecs/weather-app",
            retention = logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

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
                ),
                log_driver = ecs.LogDriver.aws_logs(
                    stream_prefix = "weather",
                    log_group = log_group
                )
            )
        )
        
        execution_role = fargate_service.task_definition.obtain_execution_role()

        execution_role.add_managed_policy(
    iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly")
)

        execution_role.add_to_policy(iam.PolicyStatement(
            actions=["ecr:GetAuthorizationToken",
                     "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer"],
            resources=["*"]  # This action requires * for resources
        ))

        # SNS topic + email subscription

        topic = sns.Topic(self, "AlertTopic", display_name = "Weather App Alerts")
        topic.add_subscription(subs.EmailSubscription("mertsatargan53@gmail.com"))

        # CPU > 1% for 2 minutes => ALARM
        cpu_alarm = cloudwatch.Alarm(
            self, "CpuHighAlarm",
            metric = fargate_service.service.metric_cpu_utilization(
                period=Duration.minutes(1),
                statistic="Average"
            ),
            threshold = 1,
            evaluation_periods = 2,
            datapoints_to_alarm = 2,
            comparison_operator = cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description = "CPU >= 1% for 2 mins"
        )

        # Memory > 70% for 2 minutes => ALARM
        memory_alarm = cloudwatch.Alarm(
            self, "MemoryHighAlarm",
            metric = fargate_service.service.metric_memory_utilization(
                period=Duration.minutes(1),
                statistic="Average"
            ),
            threshold = 70,
            evaluation_periods = 2,
            datapoints_to_alarm = 2,
            comparison_operator = cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_description = "Memory >= 70% for 2 mins"
        )

        # Wire Alarms to SNS
        cpu_alarm.add_alarm_action(cw_actions.SnsAction(topic))
        memory_alarm.add_alarm_action(cw_actions.SnsAction(topic))


        # Configure Autoscaling for the Fargate Service
        scalable = fargate_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=3
        )

        # Target tracking: aim for %70 average CPU across tasks
        scalable.scale_on_cpu_utilization("CpuTargetTracking",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.minutes(2),
            scale_out_cooldown=Duration.minutes(1)
        )
