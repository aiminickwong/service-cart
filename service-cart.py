#!/usr/bin/env python
#
# Written by: Scott McCarty
# Date: 06/2014
# Description: Test RHEV-M API

# RHEV modules
from ovirtsdk.api import API
from ovirtsdk.xml import params
from sys import path
import sys
import os
import ConfigParser

# Local modules
path.append("./lib")
from rhevlib import helpers

try:

    flavor = "rhel7-template-small"
    location = "austin"

    # Create virtual machine
    vm = helpers.create_vm(location, flavor)

    # Start VM, kickstart, and wait for shutdown
    helpers.kickstart_vm(location, flavor)

    # Create a template
    helpers.create_template(location, flavor)

except Exception as ex:
    print "Unexpected error: %s" % ex

