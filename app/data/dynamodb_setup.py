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


table_name = 'Recipe'

try:
    # test = int('fail')
    client = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
                            aws_secret_access_key=Config.aws_secret_access_key)
    print(f"{datetime.now()} Creating table {table_name}...")
    table_response = client.create_table(
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

    # Wait until the table exists.
    table_response.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    print(f"{datetime.now()} Table {table_name} created successfully!")
    print(table_response)

except Exception as e:
    print(f"{datetime.now()} Failed to create {table_name}.")
    print(f"{datetime.now()} Exception info: {e}")
    quit()

db = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
                    aws_secret_access_key=Config.aws_secret_access_key)
table = db.Table(table_name)

for recipe in recipes:
    print(f"{datetime.now()} {recipe['id']}, {recipe['name']}, steps: {len(recipe['steps'])}")
    recipe = calculate_recipe_length(recipe)
    write_response = table.put_item(Item=recipe)
    print(f"{datetime.now()} {write_response}")

