import pulumi
from pulumi_azure_native import storage, resources, compute, network, dbforpostgresql
import random
import string

# Function to generate a random password
def generate_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(length))

config = pulumi.Config()
company_name = config.require("companyName")
selected_plan = config.require("plan")
resource_group_name = f"{company_name}resources"
storage_account_name = f"{company_name.lower()}storage"
container_name = f'{company_name}container'
sql_server_user = f"{company_name}admin"
admin_user = f"{company_name}admin"
admin_password = generate_password(16)
sql_server_password = generate_password(16)

if selected_plan == "plan1":
    selected_vm_size = "Standard_D4as_v5"
    selected_vm_storage_size = 256
    postgresql_sku_name = "Standard_D2ads_v5"
    postgresql_disk_gb = 128
    postgresql_tier = "GeneralPurpose"
else:
    pulumi.log.error("Invalid plan selected. Please select either 'plan1' or 'plan2'.")
    pulumi.quit()


# Create an Azure Resource Group
resource_group = resources.ResourceGroup(resource_group_name)

# Create a Virtual Network
vnet = network.VirtualNetwork(f'{company_name}vnet',
    resource_group_name=resource_group.name,
    location=resource_group.location,
    address_space={
        'address_prefixes': ['10.0.0.0/16']
    }
)

# Create a Subnet
subnet = network.Subnet(f'{company_name}subnet',
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix='10.0.1.0/24'
)

# Create a Public IP address
public_ip = network.PublicIPAddress(f'{company_name}publicip',
    resource_group_name=resource_group.name,
    location=resource_group.location,
    public_ip_allocation_method='Static'
)

# Create a Network Interface
network_interface = network.NetworkInterface(f'{company_name}nic',
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[{
        'name': 'ipconfig',
        'subnet': {'id': subnet.id},
        'public_ip_address': {'id': public_ip.id}
    }]
)

# Create an Ubuntu Virtual Machine
ubuntu_vm = compute.VirtualMachine(f'{company_name}vm',
    resource_group_name=resource_group.name,
    location=resource_group.location,
    hardware_profile={
        'vm_size': selected_vm_size
    },
    storage_profile={
        'image_reference': {
            'publisher': 'Canonical',
            'offer': 'UbuntuServer',
            'sku': '18.04-LTS',
            'version': 'latest'
        },
        'os_disk': {
            'create_option': 'FromImage',
            'disk_size_gb': selected_vm_storage_size
        }
    },
    os_profile={
        'computer_name': f'{company_name}-ubuntuvm',
        'admin_username': admin_user,
        'admin_password': admin_password,  # Storing password securely
        'linux_configuration': {
            'disable_password_authentication': False
        }
    },
    network_profile={
        'network_interfaces': [{'id': network_interface.id}],
    },
)

# Create a PostgreSQL server
sql_server_name = f"{company_name}postgresql"
sql_server = dbforpostgresql.Server(
    sql_server_name,
    server_name=sql_server_name,
    resource_group_name=resource_group.name,
    administrator_login=sql_server_user,
    administrator_login_password=sql_server_password,
    create_mode="Default",
    storage=dbforpostgresql.StorageArgs(storage_size_gb=postgresql_disk_gb),
    backup=dbforpostgresql.BackupArgs(
        backup_retention_days=14, geo_redundant_backup="Disabled"
    ),
    sku=dbforpostgresql.SkuArgs(tier=postgresql_tier, name=postgresql_sku_name),
    availability_zone="1",
    version="16",
)

# Create a firewall rule to allow access from all IP addresses (0.0.0.0 - 255.255.255.255)
firewall_rule = dbforpostgresql.FirewallRule(
    f'{company_name}allow-all',
    resource_group_name=resource_group.name,
    server_name=sql_server.name,
    firewall_rule_name=f"{company_name}AllowAll",
    start_ip_address="0.0.0.0",
    end_ip_address="255.255.255.255"
)

# Create an Azure resource (Storage Account)
account = storage.StorageAccount(
    storage_account_name,
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(
        name=storage.SkuName.STANDARD_LRS,
    ),
    kind=storage.Kind.STORAGE_V2,
)

# Create an Azure resource (container)
container = storage.BlobContainer(
    container_name,
    account_name=storage_account.name,
    container_name=container_name,
    resource_group_name=resource_group.name,
    public_access=storage.PublicAccess.NONE
)

# Export the primary key of the Storage Account
primary_key = (
    pulumi.Output.all(resource_group.name, account.name)
    .apply(
        lambda args: storage.list_storage_account_keys(
            resource_group_name=args[0], account_name=args[1]
        )
    )
    .apply(lambda accountKeys: accountKeys.keys[0].value)
)

# Export the outputs
pulumi.export('vm_name', ubuntu_vm.name)
pulumi.export('vm_ip_address', public_ip.ip_address)
pulumi.export('vm_username', admin_user)
pulumi.export('vm_password', admin_password)
echo "---------------------------------------"
pulumi.export("potgresql_name", sql_server.name)
pulumi.export("potgresql_password", sql_server_password)
echo "---------------------------------------"
pulumi.export("storage_account_name", storage_account_name)
pulumi.export("container name", container.name)
pulumi.export("primary_storage_key", primary_key)
echo "---------------------------------------"
