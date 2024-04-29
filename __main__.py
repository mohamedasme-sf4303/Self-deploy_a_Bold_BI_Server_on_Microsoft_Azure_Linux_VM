import pulumi_azure_native.dbforpostgresql as postgresql
import pulumi_azure_native.resources as resource
from pulumi import Config, Output, export

CONFIG = Config()
RESOURCE_NAME_PREFIX = "ascid"
SQL_SERVER_USER = "dbadmin"
SQL_DB_NAME = "dtdb"
SQL_SERVER_PASSWORD = "cjecuygwdcc34we"

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
        database_name=SQL_DB_NAME,
        resource_group_name=resource_group.name,
        server_name=sql_server.name,
    )
    return pg_database

resource_group = resource.ResourceGroup(f"{RESOURCE_NAME_PREFIX}-rg",
  location="eastus"
)
sql_server = create_sql_server(resource_group)
create_pg_database(resource_group, sql_server)
