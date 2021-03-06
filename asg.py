#!/usr/bin/python
import boto3
import botocore
import datetime
from termcolor import colored
import argparse


parser = argparse.ArgumentParser(description='Display AWS Auto Scaling Groups',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-g', '--asg', help='Auto Scaling Group', default='', required=False)
args = parser.parse_args()

asg = args.asg
print ("asg: {0}".format(asg))


def get_metrics_elb(asset):
    try:
        client1 = boto3.client('elb')
    except botocore.exceptions.ClientError as e:
        print(colored("Unexpected error: {0}".format(e), 'red'))
    try:
        response1 = client1.describe_instance_health(
         LoadBalancerName=asset,
        )
    except botocore.exceptions.ClientError as e:
        print(colored("Unexpected error: {0}".format(e), 'red'))
        return 1

    for instancestates in response1['InstanceStates']:
        if instancestates['State'] == 'InService':
            ins_state = colored(instancestates['State'], 'green')
        else:
            ins_state = colored(instancestates['State'], 'red')

        print('Instance Id: {0} | Instance State: {1}'
              .format(instancestates['InstanceId'], ins_state))


def get_metrics_ec2(asset):
    client = boto3.client('cloudwatch')
    response = client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        StartTime=datetime.datetime.utcnow()-datetime.timedelta(seconds=7200),
        EndTime=datetime.datetime.utcnow(),
        Period=300,
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': asset
            },
        ],
        Statistics=['Average'],
        Unit='Percent'
    )
    newlist = response['Datapoints']
    newlist = sorted(newlist, key=lambda k: k['Timestamp'])
    if len(newlist) > 0:
        return newlist[-1]['Average']


def asg_list(ASG):
    client = boto3.client('autoscaling')
    try:
        response = client.describe_auto_scaling_groups(AutoScalingGroupNames=ASG.split(','))
    except:
        response = client.describe_auto_scaling_groups()
    ASGs = response['AutoScalingGroups']

    for ASG in ASGs:
        try:
            asg_display(ASG)
        except Exception as err:
            print(err)


def asg_display(ASG):
    healthy = 0
    unhealthy = 0
    print('#'*150)
    print('ASG Name: {0}'.format(colored(ASG['AutoScalingGroupName'], 'cyan')))
    print('ASG Min Size: {0}'.format(ASG['MinSize']))
    print('ASG Max Size: {0}'.format(ASG['MaxSize']))
    print('ASG Desired Size: {0}'.format(ASG['DesiredCapacity']))
    print('ASG instance count: {0}'.format(len(ASG['Instances'])))
    print('x'*150)

    for instance in ASG['Instances']:
        if instance['HealthStatus'] == 'Healthy':
            ins_health = colored('Healthy', 'green')
            ins_cpu = get_metrics_ec2(instance['InstanceId'])
            if ins_cpu and ins_cpu > 50:
                ins_cpu = colored(ins_cpu, 'red')
            else:
                ins_cpu = colored(ins_cpu, 'green')
            healthy += 1
        else:
            ins_health = colored(instance['HealthStatus'], 'red')
            unhealthy += 1
        if instance['LifecycleState'] == 'InService':
            ins_life = colored(instance['LifecycleState'], 'green')
        else:
            ins_life = colored(instance['LifecycleState'], 'red')

        print('Instance Id: {0} | Instance Zone: {1} | Instance LifecycleState: {2} | Instance Status: {3} | Instance Cpu: {4}'.format(
              colored(instance['InstanceId'], 'yellow'), colored(instance['AvailabilityZone'], 'yellow'), ins_life, ins_health, ins_cpu))

    if unhealthy == 0:
        unhealthycolor = 'green'
    else:
        unhealthycolor = 'red'
    print('x'*150)
    print('ASG Healthy Instance Count: {0}'.format(colored(healthy, 'green')))
    print('ASG Unhealthy Instance Count: {0}'.format(colored(unhealthy, unhealthycolor)))

    for ELB in (ASG['LoadBalancerNames']):
        print('~'*150)
        print('ELB Name: {0}'.format(colored(ELB, 'blue')))
        print('~'*150)
        get_metrics_elb(ELB)
        print('~'*150)


if __name__ == "__main__":
    try:
        asg_list(asg)
    except Exception as err:
        print(err)
