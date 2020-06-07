"""Replaces all data in the primary cloud DynamoDB table with data from a specified source."""
from boto3 import resource, client
from os import environ
from env_tools import apply_env

# Environment variables
apply_env()
aws_region = environ.get('AWS_REGION')
aws_access_key = environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = environ.get('AWS_SECRET_ACCESS_KEY')


def create_recipe_table(provided_resource):
    print(f"Creating Recipe table for {provided_resource} in {aws_region}")
    table = provided_resource.create_table(
        TableName="Recipe",
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType':       'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits':  5,
            'WriteCapacityUnits': 5
        }
    )

    # Wait until the table exists
    table.meta.client.get_waiter('table_exists').wait(TableName='Recipe')
    print("Table created")


def create_replacement_table(provided_resource):
    print(f"Creating Replacement table for {provided_resource}")
    table = provided_resource.create_table(
        TableName="Replacement",
        KeySchema=[
            {
                'AttributeName': 'scope',
                'KeyType':       'HASH'
            },
            {
                'AttributeName': 'old',
                'KeyType':       'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'scope',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'old',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits':  5,
            'WriteCapacityUnits': 5
        }
    )

    # Wait until the table exists
    table.meta.client.get_waiter('table_exists').wait(TableName='Replacement')
    print("Table created")


def purge_all_table_data(table, hash_name=None, range_name=None):
    """Deletes all items from the provided DynamoDB table."""
    data = table.scan()
    with table.batch_writer() as batch:
        for each in data['Items']:
            if range_name:
                batch.delete_item(
                    Key={
                        hash_name:  each[hash_name],
                        range_name: each[range_name]
                    }
                )
            else:
                batch.delete_item(
                    Key={
                        hash_name: each[hash_name]
                    }
                )


def copy_all_table_data(source_table, destination_table):
    """
    Reads all data from the source table, then writes to the destination table.
    Both tables must have the same schema.
    """
    data = source_table.scan()
    with destination_table.batch_writer() as batch:
        for each in data['Items']:
            batch.put_item(Item=each)


def display_all_table_data(table):
    """Prints a summary of data from the provided table."""
    data = table.scan()
    print(data, "\nItemized:")
    for each in data['Items']:
        print(each)


# Cloud connection (primary)
db_cloud_primary = resource('dynamodb',
                            region_name=aws_region,
                            aws_access_key_id=aws_access_key,
                            aws_secret_access_key=aws_secret_access_key)

# Local connection
db_local = resource('dynamodb',
                    region_name=aws_region,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_access_key,
                    endpoint_url='http://localhost:8008')
db_local_client = client('dynamodb',
                         region_name=aws_region,
                         aws_access_key_id=aws_access_key,
                         aws_secret_access_key=aws_secret_access_key,
                         endpoint_url='http://localhost:8008')

# Cloud connection (secondary)
db_cloud_secondary = resource('dynamodb',
                              region_name="us-east-2",
                              aws_access_key_id=aws_access_key,
                              aws_secret_access_key=aws_secret_access_key)
db_cloud_secondary_client = client('dynamodb',
                                   region_name="us-east-2",
                                   aws_access_key_id=aws_access_key,
                                   aws_secret_access_key=aws_secret_access_key)

# Create tables, if necessary
if 'Recipe' not in db_local_client.list_tables()['TableNames']:
    create_recipe_table(db_local)

if 'Replacement' not in db_local_client.list_tables()['TableNames']:
    create_replacement_table(db_local)

if 'Recipe' not in db_cloud_secondary_client.list_tables()['TableNames']:
    create_recipe_table(db_cloud_secondary)

if 'Replacement' not in db_cloud_secondary_client.list_tables()['TableNames']:
    create_replacement_table(db_cloud_secondary)

# Define local tables
recipe_table_local = db_local.Table('Recipe')
replacement_table_local = db_local.Table('Replacement')

# Define cloud tables
recipe_table_cloud_primary = db_cloud_primary.Table('Recipe')
replacement_table_cloud_primary = db_cloud_primary.Table('Replacement')

recipe_table_cloud_secondary = db_cloud_secondary.Table('Recipe')
replacement_table_cloud_secondary = db_cloud_secondary.Table('Replacement')

# Clear the primary cloud tables
print(f"Clearing primary cloud Recipe table ({aws_region})")
purge_all_table_data(recipe_table_cloud_primary, 'id')
print(f"Clearing primary cloud Replacement table ({aws_region})")
purge_all_table_data(replacement_table_cloud_primary, 'scope', 'old')
print("Done clearing tables.\n")

# Write data to the primary cloud from either local tables or the cloud secondary db
print("Writing to Primary tables")
copy_all_table_data(recipe_table_cloud_secondary, recipe_table_cloud_primary)
copy_all_table_data(replacement_table_cloud_secondary, replacement_table_cloud_primary)
print("Primary done\n")

print("Done writing to tables.")
