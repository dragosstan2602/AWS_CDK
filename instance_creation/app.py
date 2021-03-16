#!/usr/bin/env python3

from aws_cdk import core

from instance_creation.instance_creation_stack import InstanceCreationStack


app = core.App()
InstanceCreationStack(app, "instance-creation")

app.synth()
