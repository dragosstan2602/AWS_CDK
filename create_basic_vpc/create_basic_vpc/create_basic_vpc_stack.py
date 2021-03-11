from aws_cdk import core
from aws_cdk import aws_ec2 as ec2
import requests


class CreateBasicVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create an empty VPC
        # If you don't specify any other resources EXCEPT the VPC, there's a standard template applied
        vpc = ec2.Vpc(self, id="MyVPC",
                      nat_gateways=0,
                      cidr="192.168.0.0/20",
                      max_azs=1,
                      subnet_configuration=[], )

        # A couple of subnets
        app_subnet = ec2.CfnSubnet(self, id="Application",
                                   vpc_id=vpc.vpc_id,
                                   availability_zone="eu-central-1a",
                                   cidr_block="192.168.1.0/24",
                                   map_public_ip_on_launch=False,
                                   tags=[core.CfnTag(key="Name", value="Application")])

        web_subnet = ec2.CfnSubnet(self, id="Webhost",
                                   vpc_id=vpc.vpc_id,
                                   availability_zone="eu-central-1b",
                                   cidr_block="192.168.2.0/24",
                                   map_public_ip_on_launch=True,
                                   tags=[core.CfnTag(key="Name", value="WebHost")])

        # A couple of route tables
        private_rt = ec2.CfnRouteTable(self, id="Private_RT",
                                       vpc_id=vpc.vpc_id,
                                       tags=[core.CfnTag(key="Name", value="Private_RT")])

        public_rt = ec2.CfnRouteTable(self, id="Public_RT",
                                      vpc_id=vpc.vpc_id,
                                      tags=[core.CfnTag(key="Name", value="Public_RT")])

        # How to associate a subnet with a route table
        ec2.CfnSubnetRouteTableAssociation(self, id="WebHostRTAssoc",
                                           subnet_id=web_subnet.ref,
                                           route_table_id=public_rt.ref)

        ec2.CfnSubnetRouteTableAssociation(self, id="ApplicationRTAssoc",
                                           subnet_id=app_subnet.ref,
                                           route_table_id=private_rt.ref)

        # A gateway (Internet Gateway in this case)
        igw = ec2.CfnInternetGateway(self, id="MyIGW",
                                     tags=[core.CfnTag(key="Name", value="IGW")])

        # How to associate a gateway to a VPC (IGW in this case - for VGW use vpn_gateway_id=blablabla)
        ec2.CfnVPCGatewayAttachment(self, id="IGW_Assoc",
                                    vpc_id=vpc.vpc_id,
                                    internet_gateway_id=igw.ref)

        # Add a route to a route table
        default_route = ec2.CfnRoute(self, id="DefaultRoute",
                                     route_table_id=public_rt.ref,
                                     destination_cidr_block="0.0.0.0/0",
                                     gateway_id=igw.ref)
        # Elastic IP
        eip_01 = ec2.CfnEIP(self, id="EIP01")

        # NAT gateway
        ngw = ec2.CfnNatGateway(self, id="NAT_GW",
                                allocation_id=eip_01.attr_allocation_id,
                                subnet_id=web_subnet.ref,
                                tags=[core.CfnTag(key="Name", value="NAT_GW")])

        ngw.add_depends_on(eip_01)

        # Security Groups #

        # PUBLIC SUBNET SG
        sg_public = ec2.CfnSecurityGroup(self, id="SG_PUBLIC",
                                         group_description="SG for the Public Subnet",
                                         group_name="SG_PUBLIC",
                                         vpc_id=vpc.vpc_id,
                                         tags=[core.CfnTag(key="Name", value="SG_Public")])

        my_home_ip = requests.get("https://api.my-ip.io/ip.json").json()['ip']

        ports_pub = {'tcp': [22, 80],
                     'icmp': [-1]
                    }

        for protocl, ports_list in ports_pub.items():
            for port in ports_list:
                ec2.CfnSecurityGroupIngress(self, id=f"sg_pub_in_{protocl}_{port}",
                                            group_id=sg_public.attr_group_id,
                                            ip_protocol=protocl,
                                            cidr_ip=f"{my_home_ip}/32",
                                            to_port=port,
                                            from_port=port,
                                            description=f"{protocl.upper()} {port} from home IP")

        # SG INGRESS ENTRIES - ICMP - EXAMPLE
        # sg_in_icmp = ec2.CfnSecurityGroupIngress(self, id="SG_PUB_IN_ICMP",
        #                                          group_id=sg_public.attr_group_id,
        #                                          ip_protocol = "icmp",
        #                                          cidr_ip = f"{my_home_ip}/32",
        #                                          to_port = -1,
        #                                          from_port = -1,
        #                                          description = "ICMP FROM HOME")

        # SG EGRESS ENTRIES - AUTO-IMPLIED IF NOT CONFIGURED
        # sg_out_all = ec2.CfnSecurityGroupEgress(self, id="SG_PUB_OUT_ALL",
        #                                         group_id=sg_public.attr_group_id,
        #                                         ip_protocol="-1",
        #                                         cidr_ip="0.0.0.0/0")

        # PRIVATE SUBNET SG
        sg_private = ec2.CfnSecurityGroup(self, id="SG_PRIVATE",
                                         group_description="SG for the Private Subnet",
                                         group_name="SG_PRIVATE",
                                         vpc_id=vpc.vpc_id,
                                         tags=[core.CfnTag(key="Name", value="SG_Private")])

        sg_private.add_depends_on(sg_public)

        ports_priv = {'tcp':[22, 21, 53, 3368, 80],
                      'icmp':[-1]
                      }

        for protocl, ports_list in ports_priv.items():
            for port in ports_list:
                ec2.CfnSecurityGroupIngress(self, id=f"sg_priv_in_{protocl}_{port}",
                                            group_id=sg_private.attr_group_id,
                                            description=f"{protocl.upper()}:{port} from the public subnet only",
                                            ip_protocol=protocl,
                                            from_port=port,
                                            to_port=port,
                                            source_security_group_id=sg_public.ref)

        ### EC2 Instances ###
        # One in the public subnet
        webserver1 = ec2.CfnInstance(self, id="WebServer01",
                                     image_id="ami-0de9f803fcac87f46",
                                     instance_type="t2.micro",
                                     subnet_id=web_subnet.ref,
                                     key_name="proton_mail_kp",
                                     security_group_ids=[sg_public.ref],
                                     tags=[core.CfnTag(key="Name", value="WebServer01")])