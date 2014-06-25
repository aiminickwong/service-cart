# Written By: Scott McCarty
# Date: 06/2014
# Purpose: helper functions to assist in interaction with RHEV-M
# Concepts developed from: https://access.redhat.com/site/documentation/en-US/Red_Hat_Enterprise_Virtualization/3.2/html/Developer_Guide/Further_Python_SDK_Examples.html

# RHEV modules 
from ovirtsdk.api import API
from ovirtsdk.xml import params
from time import sleep as sleep
import sys
import os
import ConfigParser

# Read configuration files
locations = ConfigParser.ConfigParser()
locations.read(os.path.expanduser('~/.service-cart-locations.cfg'))
flavors = ConfigParser.ConfigParser()
flavors.read(os.path.expanduser('~/.service-cart-flavors.cfg'))

# Config Functions
def list_locations():
    for name in locations._sections:
            print name
    sys.exit()

# oVirt/RHEV Functions
def get_connection(location):
    api = API(  url="https://" + locations.get(location, "host"),
                username=locations.get(location, "username"),
                password=locations.get(location, "password"),
                ca_file=locations.get(location, "certificate")
                )

    print "Connected to %s successfully!" % api.get_product_info().name
    return api

def create_vm(location, flavor):
    # Connect to RHEV-M
    api = get_connection(location)

    # Add virtual machine
    vm = add_vm(api, location, flavor)

    # Add network
    nic = add_nic(api, vm, flavor)

    # Add cdrom
    add_cdrom(api, vm, flavor)

    # Add disk
    disk = add_disk(api, vm, location, flavor)

    # Wait for VM to be ready
    wait_for_disk(api, disk, "ok", 180)

    api.disconnect()

    return vm
 
def add_vm(api,  location, flavor):
    vm_name = flavor
    vm_memory = int(flavors.get(flavor, "memory"))
    vm_cluster = api.clusters.get(name=locations.get(location, "cluster_name"))
    vm_template = api.templates.get(name="Blank")
    vm_os = params.OperatingSystem(boot=[params.Boot(dev="hd")])

    vm_params = params.VM(name=vm_name, memory=vm_memory, cluster=vm_cluster, template=vm_template, os=vm_os)
    vm = api.vms.add(vm=vm_params)
    print "Virtual machine '%s' added." % vm_name
    return vm

def add_nic(api, vm, flavor):
    network_name = flavors.get(flavor, "network")
    nic_name = flavors.get(flavor, "nic")
    nic_interface = "virtio"
    nic_network = api.networks.get(name=network_name)
    nic_params = params.NIC(name=nic_name,interface=nic_interface,network=nic_network)
    nic = vm.nics.add(nic_params)
    print "Network interface '%s' added to '%s'." % (nic.get_name(), vm.get_name())
    return nic

def add_disk(api, vm, location, flavor):
    disk_size = int(flavors.get(flavor, "disk"))
    storage_domain = locations.get(location, "storage_domain")
    disk_type = "system"
    disk_interface = "virtio"
    disk_format = "cow"
    disk_bootable = True
    sd = params.StorageDomains(storage_domain=[api.storagedomains.get(name=storage_domain)])
    disk_params = params.Disk(storage_domains=sd,size=disk_size,type_=disk_type,interface=disk_interface,format=disk_format,bootable=disk_bootable)
    disk = vm.disks.add(disk_params)
    print "Disk '%s' added to '%s'." % (disk.get_name(), vm.get_name())
    return disk

def add_cdrom(api, vm, flavor):
    iso = flavors.get(flavor, "iso")
    sd = api.storagedomains.get(name="ISO")
    cd_iso = sd.files.get(name=iso)
    cd_params = params.CdRom(file=cd_iso)
    vm.cdroms.add(cd_params)
    print "Attached CD '%s' to '%s'." % iso, vm.get_name()

def wait_for_disk(api, disk, status, max_pause=60):
    disk_name = disk.get_name()
    pause = max_pause / 100
    total_pause = 0
    while str(status) != str(api.disks.get(disk_name).status.state):
        total_pause = total_pause + pause
        if total_pause < max_pause:
            print "Status: " + str(api.disks.get(disk_name).status.state)
            sleep(pause)
        else:
            print "Reached timeout: " + str(max_pause) + " Status: " + str(api.disks.get(disk_name).status.state)
            return

    print "Status: " + str(status)

def wait_for_vm(api, vm_name, status, max_pause=60):
    pause = max_pause / 100
    total_pause = 0
    while str(status) != str(api.vms.get(name=vm_name).status.state):
        total_pause = total_pause + pause
        if total_pause < max_pause:
            print "Status: " + str(api.vms.get(name=vm_name).status.state)
            sleep(pause)
        else:
            print "Reached timeout: " + str(max_pause) + " Status: " + str(api.vms.get(name=vm_name).status.state)
            return

    print "Status: " + str(status)

def kickstart_vm(location, flavor):

    api = get_connection(location)
    vm_name = flavors.get(flavor, "name")
    vm = api.vms.get(name=vm_name)

    # Set cdrom as the bootable device
    boot1 = params.Boot(dev="cdrom")
    boot2 = params.Boot(dev="hd")
    a = params.Action()
    a.vm = params.VM(os=params.OperatingSystem(boot=[boot1, boot2]))

    # Start VM, it will automatically kickstart because of the ISO
    vm.start(action=a)

    # Give the kickstart 4800 seconds to complete
    wait_for_vm(api, vm_name, "down", 4800)

    api.disconnect()

def create_template(location, flavor):

    api = get_connection(location)
    template_name = flavors.get(flavor, "name")
    vm_name = flavors.get(flavor, "name")
    storage_domain = locations.get(location, "storage_domain")
    vm = api.vms.get(name=vm_name)

    # Remove old template
    template = api.templates.get(template_name)
    if template:
        template.delete()

    # Create new template
    template =  api.templates.add(params.Template(name=template_name, vm=api.vms.get(vm_name), cluster=api.clusters.get(storage_domain)))
    wait_for_vm(api, vm_name, "down", 1800)

    # Delete original vm
    vm.delete()

    print "Template '%s' added." % template_name
    return template

