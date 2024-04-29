import pulumi
from pulumi_azure_native import resources, network, compute
from pulumi_random import random_string
import pulumi_tls as tls
import pulumi_azure_native.dbforpostgresql as postgresql
import pulumi_azure_native.resources as resource
import base64


RESOURCE_NAME_PREFIX = "rsdfveve"
SQL_SERVER_USER = "dbadmin"
SQL_DB_NAME = "dtdb"
SQL_SERVER_PASSWORD = "asmfjcii495"
vm_name = "my-server"
vm_size = "Standard_A1_v2"
os_image = "Debian:debian-11:11:latest"
admin_username = "pulumiuser"
service_port = "80"
admin_password = "asmekdldir3453#"
os_image_publisher, os_image_offer, os_image_sku, os_image_version = os_image.split(":")

# Create an SSH key
ssh_key = tls.PrivateKey(
    "ssh-key",
    algorithm = "RSA",
    rsa_bits = 4096,
)
resource_group = resource.ResourceGroup(f"{RESOURCE_NAME_PREFIX}-rg")

# Create a virtual network
virtual_network = network.VirtualNetwork(
    "network",
    resource_group_name=resource_group.name,
    address_space=network.AddressSpaceArgs(
        address_prefixes=[
            "10.0.0.0/16",
        ],
    ),
    subnets=[
        network.SubnetArgs(
            name=f"{vm_name}-subnet",
            address_prefix="10.0.1.0/24",
        ),
    ],
)
# Use a random string to give the VM a unique DNS name
domain_name_label = random_string.RandomString(
    "domain-label",
    length=8,
    upper=False,
    special=False,
).result.apply(lambda result: f"{vm_name}-{result}")

# Create a public IP address for the VM
public_ip = network.PublicIPAddress(
    "public-ip",
    resource_group_name=resource_group.name,
    public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
    dns_settings=network.PublicIPAddressDnsSettingsArgs(
        domain_name_label=domain_name_label,
    ),
)

# Create a security group allowing inbound access over ports 80 (for HTTP) and 22 (for SSH)
security_group = network.NetworkSecurityGroup(
    "security-group",
    resource_group_name=resource_group.name,
    security_rules=[
        network.SecurityRuleArgs(
            name=f"{vm_name}-securityrule",
            priority=1000,
            direction=network.AccessRuleDirection.INBOUND,
            access="Allow",
            protocol="Tcp",
            source_port_range="*",
            source_address_prefix="*",
            destination_address_prefix="*",
            destination_port_ranges=[
                service_port,
                "22",
            ],
        ),
    ],
)

# Create a network interface with the virtual network, IP address, and security group
network_interface = network.NetworkInterface(
    "network-interface",
    resource_group_name=resource_group.name,
    network_security_group=network.NetworkSecurityGroupArgs(
        id=security_group.id,
    ),
    ip_configurations=[
        network.NetworkInterfaceIPConfigurationArgs(
            name=f"{vm_name}-ipconfiguration",
            private_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
            subnet=network.SubnetArgs(
                id=virtual_network.subnets.apply(lambda subnets: subnets[0].id),
            ),
            public_ip_address=network.PublicIPAddressArgs(
                id=public_ip.id,
            ),
        ),
    ],
)

# Define a script to be run when the VM starts up
init_script = f"""#!/bin/bash
    echo '<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Hello, world!</title>
    </head>
    <body>
        <h1>Hello, world! 👋</h1>
        <p>Deployed with 💜 by <a href="https://pulumi.com/">Pulumi</a>.</p>
    </body>
    </html>' > index.html
    sudo python3 -m http.server {service_port} &
    """

# Create the virtual machine
vm = compute.VirtualMachine(
    "vm",
    resource_group_name=resource_group.name,
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(
                id=network_interface.id,
                primary=True,
            )
        ]
    ),
    hardware_profile=compute.HardwareProfileArgs(
        vm_size=vm_size,
    ),
    os_profile=compute.OSProfileArgs(
        computer_name=vm_name,
        admin_username=admin_username,
        admin_password=admin_password,
        custom_data=base64.b64encode(bytes(init_script, "utf-8")).decode("utf-8"),
        linux_configuration=compute.LinuxConfigurationArgs(
            disable_password_authentication=False,
        ),
    ),
    storage_profile=compute.StorageProfileArgs(
        os_disk=compute.OSDiskArgs(
            name=f"{vm_name}-osdisk",
            create_option=compute.DiskCreateOption.FROM_IMAGE,
        ),
        image_reference=compute.ImageReferenceArgs(
            publisher=os_image_publisher,
            offer=os_image_offer,
            sku=os_image_sku,
            version=os_image_version,
        ),
    ),
)

# Once the machine is created, fetch its IP address and DNS hostname
vm_address = vm.id.apply(
    lambda id: network.get_public_ip_address_output(
        resource_group_name=resource_group.name,
        public_ip_address_name=public_ip.name,
    )
)


def create_sql_server(resource_group: resource.ResourceGroup) -> postgresql.Server:
    sql_server_name = f"{RESOURCE_NAME_PREFIX}-postgresql"
    sql_server = postgresql.Server(
        sql_server_name,
        server_name=sql_server_name,
        resource_group_name=resource_group.name,
        administrator_login=SQL_SERVER_USER,
        administrator_login_password=SQL_SERVER_PASSWORD,
        create_mode="Default",
        storage=postgresql.StorageArgs(storage_size_gb=32),
        backup=postgresql.BackupArgs(
            backup_retention_days=14, geo_redundant_backup="Disabled"
        ),
        sku=postgresql.SkuArgs(tier="Burstable", name="Standard_B1ms"),
        availability_zone="1",
        version="16",
    )
    return sql_server


def create_pg_database(
    resource_group: resource.ResourceGroup, sql_server: postgresql.Server
) -> postgresql.Database:
    pg_database = postgresql.Database(
        SQL_DB_NAME,
        charset="UTF8",
        collation="English_United States.1252",
        database_name=SQL_DB_NAME,
        resource_group_name=resource_group.name,
        server_name=sql_server.name,
    )
    return pg_database


sql_server = create_sql_server(resource_group)
create_pg_database(resource_group, sql_server)

# Export the VM's hostname, public IP address, HTTP URL, and SSH private key
pulumi.export(
    "ip",
    vm_address.ip_address
)
pulumi.export(
    "hostname",
    vm_address.dns_settings.apply(
        lambda settings: settings.fqdn
    )
)
pulumi.export(
    "url",
    vm_address.dns_settings.apply(
        lambda settings: f"http://{settings.fqdn}:{service_port}"
    ),
)
pulumi.export(
    "privatekey",
    ssh_key.private_key_openssh,
)
