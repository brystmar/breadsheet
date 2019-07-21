import boto3
from config import Config

db_local = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key,
                          aws_secret_access_key=Config.aws_secret_access_key, endpoint_url='http://localhost:8008')

table = db_local.create_table(
    TableName='Recipe',
    KeySchema=[
        {
            'AttributeName': 'id',
            'KeyType': 'HASH'
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'id',
            'AttributeType': 'S'
        }
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 2,
        'WriteCapacityUnits': 2
    },
    Tags=[
        {
            "Key": "project",
            "Value": "breadsheet"
        }
    ]
)

# Wait until the table exists
table.meta.client.get_waiter('table_exists').wait(TableName='Recipe')

print("Recipe table", table)

table2 = db_local.create_table(
    TableName='Replacement',
    KeySchema=[
        {
            'AttributeName': 'scope',
            'KeyType': 'HASH'
        },
        {
            'AttributeName': 'old',
            'KeyType': 'RANGE'
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
        'ReadCapacityUnits': 2,
        'WriteCapacityUnits': 2
    },
    Tags=[
        {
            "Key": "project",
            "Value": "breadsheet"
        }
    ]
)

# Wait until the table exists
table2.meta.client.get_waiter('table_exists').wait(TableName='Replacement')

print("Replacement table", table2)
