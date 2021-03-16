from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
import requests


class AppLbSampleStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, id="MyVPC",
                      nat_gateways=0,
                      cidr="192.168.0.0/20",
                      max_azs=3,
                      subnet_configuration=[])
        pub_subnet = ec2.PublicSubnet(self, id="PublicSubnet",
                                      availability_zone="eu-central-1c",
                                      cidr_block="192.168.0.0/24",
                                      vpc_id=vpc.vpc_id,
                                      map_public_ip_on_launch=True)

        igw = ec2.CfnInternetGateway(self, id="MyIGW",
                                     tags=[core.CfnTag(key="Name", value="IGW")])

        ec2.CfnVPCGatewayAttachment(self, id="IGW_Assoc",
                                    vpc_id=vpc.vpc_id,
                                    internet_gateway_id=igw.ref)

        pub_subnet.add_route(id="default_route-sub01",
                             router_id=igw.ref,
                             router_type=ec2.RouterType('GATEWAY'),
                             destination_cidr_block="0.0.0.0/0",
                             enables_internet_connectivity=True)

        # Elastic IP
        eip_01 = ec2.CfnEIP(self, id="EIP01")

        # NAT gateway
        ngw = ec2.CfnNatGateway(self, id="NAT_GW",
                                allocation_id=eip_01.attr_allocation_id,
                                subnet_id=pub_subnet.subnet_id,
                                tags=[core.CfnTag(key="Name", value="NAT_GW")])

        subnet01 = ec2.Subnet(self, id="Subnet01",
                              availability_zone="eu-central-1a",
                              cidr_block="192.168.1.0/24",
                              vpc_id=vpc.vpc_id,
                              map_public_ip_on_launch=False)

        subnet02 = ec2.Subnet(self, id="Subnet02",
                              availability_zone="eu-central-1b",
                              cidr_block="192.168.2.0/24",
                              vpc_id=vpc.vpc_id,
                              map_public_ip_on_launch=False)

        subnet01.add_route(id="default_route-sub01",
                           router_id=ngw.ref,
                           router_type=ec2.RouterType('NAT_GATEWAY'),
                           destination_cidr_block="0.0.0.0/0",
                           enables_internet_connectivity=True)

        subnet02.add_route(id="default_route-sub02",
                           router_id=ngw.ref,
                           router_type=ec2.RouterType('NAT_GATEWAY'),
                           destination_cidr_block="0.0.0.0/0",
                           enables_internet_connectivity=True)

        sg_lb = ec2.CfnSecurityGroup(self, id="SG_ALB",
                                     group_description="SG for the APP LB",
                                     group_name="SG_ALB",
                                     vpc_id=vpc.vpc_id,
                                     tags=[core.CfnTag(key="Name", value="SG_ALB")])

        sg_ec2i = ec2.CfnSecurityGroup(self, id="SG_Instances",
                                       group_description="SG for the Instances",
                                       group_name="SG_Instances",
                                       vpc_id=vpc.vpc_id,
                                       tags=[core.CfnTag(key="Name", value="SG_Instances")])

        my_home_ip = requests.get("https://api.ipify.org").text

        ports_pub = {'tcp': [22, 80],
                     'icmp': [-1]
                     }

        for protocol, ports_list in ports_pub.items():
            for port in ports_list:
                ec2.CfnSecurityGroupIngress(self, id=f"sg_alb_in_{protocol}_{port}",
                                            group_id=sg_lb.attr_group_id,
                                            ip_protocol=protocol,
                                            cidr_ip=f"{my_home_ip}/32",
                                            to_port=port,
                                            from_port=port,
                                            description=f"{protocol.upper()} {port} from home IP")

                ec2.CfnSecurityGroupIngress(self, id=f"sg_ec2i_in_{protocol}_{port}",
                                            group_id=sg_ec2i.attr_group_id,
                                            ip_protocol=protocol,
                                            to_port=port,
                                            from_port=port,
                                            source_security_group_id=sg_lb.ref,
                                            description=f"{protocol.upper()} {port} from the ALB SG")

        with open("/home/dragos/Documents/AWS_CDK/app_lb_sample/app_lb_sample/configure.sh", 'r') as config_file:
            ud = core.Fn.base64(config_file.read())

        instance01 = ec2.CfnInstance(self, id="WebServer01",
                                     image_id="ami-0de9f803fcac87f46",
                                     instance_type="t2.micro",
                                     subnet_id=subnet01.subnet_id,
                                     key_name="proton_mail_kp",
                                     security_group_ids=[sg_ec2i.ref],
                                     user_data=ud,
                                     tags=[core.CfnTag(key="Name", value="WebServer01")])

        instance02 = ec2.CfnInstance(self, id="WebServer02",
                                     image_id="ami-0de9f803fcac87f46",
                                     instance_type="t2.micro",
                                     subnet_id=subnet02.subnet_id,
                                     key_name="proton_mail_kp",
                                     security_group_ids=[sg_ec2i.ref],
                                     user_data=ud,
                                     tags=[core.CfnTag(key="Name", value="WebServer02")])

        health_check = elbv2.HealthCheck(enabled=True,
                                         healthy_http_codes="200",
                                         path="/index.html",
                                         protocol=elbv2.Protocol("HTTP"))

        tg = elbv2.ApplicationTargetGroup(self, id="TG-WEB-HTTP",
                                          port=80,
                                          protocol=elbv2.ApplicationProtocol("HTTP"),
                                          target_group_name="TG-WEB-HTTP",
                                          target_type=elbv2.TargetType("INSTANCE"),
                                          vpc=vpc.vpc_id,
                                          health_check=health_check,
                                          targets=[])
