import boto3

globalVars = {}
globalVars['REGION_NAME'] = "us-west-2"
globalVars['AZ1'] = "us-west-2a"
globalVars['AZ2'] = "us-west-2b"
globalVars['AZ3'] = "us-west-2c"
ec2 = boto3.resource('ec2', region_name = globalVars['REGION_NAME'])
ec2Client = boto3.client('ec2', region_name = globalVars['REGION_NAME'])
# Create VPC
vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
vpc.wait_until_available()
print(vpc.id)
vpc.modify_attribute(EnableDnsSupport = { 'Value': True })
vpc.modify_attribute( EnableDnsHostnames = {'Value': True })
# Create public Subntes
pubsubnet1 = vpc.create_subnet(CidrBlock = '10.0.1.0/24', VpcId= vpc.id, AvailabilityZone = globalVars['AZ1'])
pubsubnet2 = vpc.create_subnet(CidrBlock = '10.0.2.0/24', VpcId= vpc.id, AvailabilityZone = globalVars['AZ2'])
pubsubnet3 = vpc.create_subnet(CidrBlock = '10.0.3.0/24', VpcId= vpc.id, AvailabilityZone = globalVars['AZ3'])
# Create the Internet Gatway & Attach to the VPC
intGateway  = ec2.create_internet_gateway()
intGateway.attach_to_vpc(VpcId = vpc.id)
# Create another route table for Public traffic
pubRouteTable = ec2.create_route_table(VpcId = vpc.id)
pubRouteTable.associate_with_subnet(SubnetId = pubsubnet1.id)
pubRouteTable.associate_with_subnet(SubnetId = pubsubnet2.id)
pubRouteTable.associate_with_subnet(SubnetId = pubsubnet3.id)
# Create a route for internet traffic to flow out
intRoute = ec2Client.create_route(RouteTableId = pubRouteTable.id, DestinationCidrBlock = '0.0.0.0/0', GatewayId = intGateway.id)
# Tag the resources
vpc.create_tags(Tags=[{"Key":"Name","Value":"K8s_VPC"}])
pubsubnet1.create_tags(Tags=[{"Key":"Name","Value":"K8s_Pubsubnet1"}])
pubsubnet2.create_tags(Tags=[{"Key":"Name","Value":"K8s_Pubsubnet2"}])
pubsubnet3.create_tags(Tags=[{"Key":"Name","Value":"K8s_Pubsubnet3"}])
intGateway.create_tags(Tags=[{"Key":"Name","Value":"K8s_IGW"}])
pubRouteTable.create_tags(Tags=[{"Key":"Name","Value":"K8s_RT"}])
instance_sec_group = ec2.create_security_group(
    GroupName='k8s_Master_Group', Description='k8s_Master security group', VpcId=vpc.id)
ec2Client.authorize_security_group_ingress(
    GroupId=instance_sec_group.id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
             'FromPort': 22,
             'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
             'FromPort': 6443,
             'ToPort': 6443,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                        {'IpProtocol': 'tcp',
             'FromPort': 10250,
             'ToPort': 10252,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                        {'IpProtocol': 'tcp',
             'FromPort': 2379,
             'ToPort': 2380,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                        {'IpProtocol': 'tcp',
             'FromPort': 8200,
             'ToPort': 8200,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                        {'IpProtocol': 'tcp',
             'FromPort': 80,
             'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])
instance_sec_group.create_tags(Tags=[{"Key":"Name","Value":"K8s_master_sg"}])
# Creating instance
instance = ec2.create_instances(
    ImageId = 'ami-0326d95bf52eb37fd',
        MinCount = 1,
    MaxCount = 1,
        InstanceType = 't2.medium',
        KeyName = 'kubeadm',
        BlockDeviceMappings=[
        {
            'DeviceName': '/dev/xvda',
            'Ebs': {

                'DeleteOnTermination': False,
                'VolumeSize': 20,
                'VolumeType': 'gp2'
            },
        },
    ],
        NetworkInterfaces=[
            {
                   'SubnetId': pubsubnet1.id,
                   'DeviceIndex': 0,
                   'AssociatePublicIpAddress': True,
                   'Groups': [instance_sec_group.group_id]
                }
        ],
	TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'master'
                        },
                    ]
                },
            ]
)
instance_id = instance[0].instance_id

