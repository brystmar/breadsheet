import boto3
from app.data.build_dynamodb_tables import create_recipe_table, create_replacement_table
from config import Config

db_cloud = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
                          aws_secret_access_key=Config.aws_secret_access_key)

db_local = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
                          aws_secret_access_key=Config.aws_secret_access_key, endpoint_url='http://localhost:8008')

# print(f"Replacement response: {create_replacement_table(db_local, 'Replacement')}")
# print("\n\n")
# print(f"Recipe response: {create_recipe_table(db_local, 'Recipe')}")


recipes = db_cloud.Table('Recipe').scan()['Items']
# replacements = db_cloud.Table('Replacement').scan()['Items']


# for r in replacements:
#     print(r)
#     write_response = db_local.Table('Replacement').put_item(Item=r)
#
#     if write_response['ResponseMetadata']['HTTPStatusCode'] != 200:
#         print(r)
#         print(write_response)
#         print('\n')

for r in recipes:
    write_response = db_local.Table('Recipe').put_item(Item=r)

    if write_response['ResponseMetadata']['HTTPStatusCode'] != 200:
        print(r)
        print(write_response)
        print('\n')
