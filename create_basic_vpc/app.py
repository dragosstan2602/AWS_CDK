#!/usr/bin/env python3

from aws_cdk import core

from create_basic_vpc.create_basic_vpc_stack import CreateBasicVpcStack


app = core.App()
CreateBasicVpcStack(app, "create-basic-vpc")

app.synth()
