"""Replaces all data in local DynamoDB tables with data from the cloud database."""
import boto3
from config import Config


def purge_all_table_data(table, hash_name=None, range_name=None):
    """Deletes all items from the provided DynamoDB table."""
    data = table.scan()
    with table.batch_writer() as batch:
        for each in data['Items']:
            if range_name:
                batch.delete_item(
                    Key={
                        hash_name: each[hash_name],
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


# Local connection
db_local = boto3.resource('dynamodb',
                          region_name=Config.aws_region,
                          aws_access_key_id=Config.aws_access_key,
                          aws_secret_access_key=Config.aws_secret_access_key,
                          endpoint_url='http://localhost:8008')

# Cloud connection
db_cloud = boto3.resource('dynamodb',
                          region_name=Config.aws_region,
                          aws_access_key_id=Config.aws_access_key,
                          aws_secret_access_key=Config.aws_secret_access_key)

# Define local tables
recipe_table_local = db_local.Table('Recipe')
replacement_table_local = db_local.Table('Replacement')

# Define cloud tables
recipe_table_cloud = db_cloud.Table('Recipe')
replacement_table_cloud = db_cloud.Table('Replacement')

# Clear local tables
purge_all_table_data(recipe_table_local, 'id')
purge_all_table_data(replacement_table_local, 'scope', 'old')

# Write data from cloud to local
copy_all_table_data(recipe_table_cloud, recipe_table_local)
copy_all_table_data(replacement_table_cloud, replacement_table_local)
