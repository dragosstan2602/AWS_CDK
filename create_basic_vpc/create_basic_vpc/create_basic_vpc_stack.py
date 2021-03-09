from aws_cdk import core
from aws_cdk import aws_ec2 as ec2


class CreateBasicVpcStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create an empty VPC
        # If you don't specify any other resources EXCEPT the VPC, there's a standard template applied
        vpc = ec2.Vpc(self, "MyVPC",
                      nat_gateways=0,
                      cidr="192.168.0.0/20",
                      max_azs=1,
                      subnet_configuration=[], )

        # A couple of subnets
        app_subnet = ec2.CfnSubnet(self, "Application",
                                   vpc_id=vpc.vpc_id,
                                   availability_zone="eu-central-1a",
                                   cidr_block="192.168.1.0/24",
                                   map_public_ip_on_launch=False,
                                   tags=[core.CfnTag(key="Name", value="Application")])

        web_subnet = ec2.CfnSubnet(self, "WebHost",
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
                                     tags=[core.CfnTag(key="Name", value="Public_RT")])

        # How to associate a gateway to a VPC (IGW in this case - for VGW use vpn_gateway_id=blablabla)
        ec2.CfnVPCGatewayAttachment(self, id="IGW_Assoc",
                                    vpc_id=vpc.vpc_id,
                                    internet_gateway_id=igw.ref)

        # Add a route to a route table
        default_route = ec2.CfnRoute(self, id="DefaultRoute",
                                     route_table_id=public_rt.ref,
                                     destination_cidr_block="0.0.0.0/0",
                                     gateway_id=igw.ref)