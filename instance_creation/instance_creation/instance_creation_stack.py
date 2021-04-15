from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
import requests


class InstanceCreationStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, id="MyVPC",
                      nat_gateways=0,
                      cidr="192.168.0.0/20",
                      max_azs=1,
                      subnet_configuration=[])

        subnet = ec2.Subnet(self, id="MySubnet",
                            availability_zone="eu-central-1a",
                            cidr_block="192.168.1.0/24",
                            vpc_id=vpc.vpc_id,
                            map_public_ip_on_launch=True)

        igw = ec2.CfnInternetGateway(self, id="MyIGW",
                                     tags=[core.CfnTag(key="Name", value="IGW")])

        ec2.CfnVPCGatewayAttachment(self, id="IGW_Assoc",
                                    vpc_id=vpc.vpc_id,
                                    internet_gateway_id=igw.ref)

        subnet.add_route(id="default_route",
                         router_id=igw.ref,
                         router_type=ec2.RouterType('GATEWAY'),
                         destination_cidr_block="0.0.0.0/0",
                         enables_internet_connectivity=True)

        sg_public = ec2.CfnSecurityGroup(self, id="SG_PUBLIC",
                                         group_description="SG for the Public Subnet",
                                         group_name="SG_PUBLIC",
                                         vpc_id=vpc.vpc_id,
                                         tags=[core.CfnTag(key="Name", value="SG_Public")])

        my_home_ip = requests.get("https://api.ipify.org").text

        ports_pub = {'tcp': [22, 80],
                     'icmp': [-1]
                     }

        for protocol, ports_list in ports_pub.items():
            for port in ports_list:
                ec2.CfnSecurityGroupIngress(self, id=f"sg_pub_in_{protocol}_{port}",
                                            group_id=sg_public.attr_group_id,
                                            ip_protocol=protocol,
                                            cidr_ip=f"{my_home_ip}/32",
                                            to_port=port,
                                            from_port=port,
                                            description=f"{protocol.upper()} {port} from home IP")

        with open("/home/dragos/Documents/AWS_CDK/instance_creation/instance_creation/configure.sh", 'r') as config_file:
            ud = core.Fn.base64(config_file.read())

        instance = ec2.CfnInstance(self, id="MyInstance",
                                   image_id="ami-0de9f803fcac87f46",
                                   instance_type="t2.micro",
                                   subnet_id=subnet.subnet_id,
                                   key_name="proton_mail_kp",
                                   security_group_ids=[sg_public.ref],
                                   tags=[core.CfnTag(key="Name", value="MyInstance")])

        instance.user_data = ud
