from app.data.breadsheet_data import recipes, replacements
from config import Config
from datetime import datetime
import boto3


def calculate_recipe_length(recipe):
    """Add/update the recipe's length (in seconds) by summing the length of each step."""
    length = 0
    for step in recipe['steps']:
        length += step['then_wait']

    recipe['length'] = length
    print(f"Recipe length: {length}")
    return recipe


def create_recipe_table(db, table_name):
    try:
        print(f"{datetime.now()} Creating table {table_name}...")
        table_response = db.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": "id",
                    "KeyType":       "HASH"  # HASH = partition key, RANGE = sort key
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "id",
                    "AttributeType": "S"
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits":  2,
                "WriteCapacityUnits": 2
            },
            Tags=[
                {
                    "Key":   "project",
                    "Value": "breadsheet"
                }
            ]
        )

        # Pause until the table is created
        table_response.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"{datetime.now()} Table {table_name} created successfully!")
        print(table_response)

    except Exception as e:
        print(f"{datetime.now()} Failed to create {table_name}.")
        print(f"{datetime.now()} Exception info: {e}")


def add_recipe_data(recipes, table):
    errors = []
    count = 0
    for recipe in recipes:
        print(f"{datetime.now()} {recipe['id']}, {recipe['name']}, steps: {len(recipe['steps'])}")
        recipe = calculate_recipe_length(recipe)
        write_response = table.put_item(Item=recipe)
        print(f"{datetime.now()} {write_response}")

        if write_response['ResponseMetadata']['HTTPStatusCode'] != 200:
            errors.append(write_response['ResponseMetadata'])
        count += 1

    print(f"Finished adding {count} objects with {len(errors)} errors.")


def create_replacement_table(db, table_name):
    try:
        print(f"{datetime.now()} Creating table {table_name}...")
        table_response = db.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    "AttributeName": "scope",
                    "KeyType":       "HASH"  # HASH = partition key, RANGE = sort key
                },
                {
                    "AttributeName": "old",
                    "KeyType":       "RANGE"
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "scope",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "old",
                    "AttributeType": "S"
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits":  2,
                "WriteCapacityUnits": 2
            },
            Tags=[
                {
                    "Key":   "project",
                    "Value": "breadsheet"
                }
            ]
        )

        # Pause until the table is created
        table_response.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"{datetime.now()} Table {table_name} created successfully!")
        print(table_response, '\n')

    except Exception as e:
        print(f"{datetime.now()} Failed to create {table_name}.")
        print(f"{datetime.now()} Exception info: {e}")


def add_replacement_data(data, table):
    print(f"Writing data to {table}")
    errors = []
    count = 0
    for d in data:
        write_response = table.put_item(Item=d)
        print(f"{datetime.now()} Finished writing {d['scope']} with write_response: {write_response}")
        if write_response['ResponseMetadata']['HTTPStatusCode'] != 200:
            errors.append(write_response['ResponseMetadata'])
        count += 1

    print(f"Finished adding {count} objects with {len(errors)} errors.")

# db = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
#                     aws_secret_access_key=Config.aws_secret_access_key)
#
# table_name = 'Recipe'
# create_recipe_table(db, table_name)
# add_recipe_data(recipes, db.Table(table_name))
#
# table_name = 'Replacement'
# create_replacement_table(db, table_name)
# add_replacement_data(replacements, db.Table(table_name))
