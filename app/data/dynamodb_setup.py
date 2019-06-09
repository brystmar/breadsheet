from app.data.breadsheet_data import recipes, replacements
from config import Config
import boto3

client = boto3.client('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
                      aws_secret_access_key=Config.aws_secret_access_key)

table_name = 'Recipe_python_test1'

try:
    test = int('fail')
    response = client.create_table(
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
            "ReadCapacityUnits":  1,
            "WriteCapacityUnits": 1
        },
        Tags=[
            {
                "Key":   "project",
                "Value": "breadsheet"
            }
        ]
    )

except Exception as e:
    pass

db = boto3.resource('dynamodb', region_name=Config.aws_region, aws_access_key_id=Config.aws_access_key_id,
                    aws_secret_access_key=Config.aws_secret_access_key)
table = db.Table(table_name)
r1 = {
        "id":         "7",
        "name":       "No-Knead Brioche",
        "author":     "ATK/Cook's",
        "source":     "Cook's Illustrated",
        "difficulty": "Medium",
        "date_added": "2019-05-19",
        "start_time": "2019-05-19 09:00:00",
        "steps":      [
            {
                "number":    1,
                "text":      "Whisk together ingredients, cover, and let stand 10 minutes.",
                "then_wait": 600,
                "comment":   "\\N"
            },

            {
                "number":    2,
                "text":      "Fold #1, then cover and let rise.",
                "then_wait": 1800,
                "comment":   "4 total folds, 30m between."
            },

            {
                "number":    3,
                "text":      "Fold #2, then cover and let rise.",
                "then_wait": 1800,
                "comment":   "\\N"
            },

            {
                "number":    4,
                "text":      "Fold #3, then cover and let rise.",
                "then_wait": 1800,
                "comment":   "\\N"
            },

            {
                "number":    5,
                "text":      "Fold #4, then cover tightly with plastic wrap and refrigerate.",
                "then_wait": 57600,
                "comment":   "16 to 48 hours"
            },

            {
                "number":    6,
                "text":      "Divide & shape",
                "then_wait": 300,
                "comment":   "Let rest for 5m"
            },

            {
                "number":    7,
                "text":      "Re-shape in baking pans; cover for second rise.",
                "then_wait": 3600,
                "comment":   "1\u00bd to 2hrs (minus 30m to preheat)"
            },

            {
                "number":    8,
                "text":      "Pre-heat oven (with baking stone/steel) to 350\u00b0F",
                "then_wait": 1800,
                "comment":   "\\N"
            },

            {
                "number":    9,
                "text":      "Brush loaves with egg wash",
                "then_wait": 0,
                "comment":   "\\N"
            },

            {
                "number":    10,
                "text":      "Bake to 190\u00b0F internal temp, rotating halfway through",
                "then_wait": 2100,
                "comment":   "35 to 45 minutes"
            },

            {
                "number":    11,
                "text":      "Remove pans from oven, place on wire rack",
                "then_wait": 300,
                "comment":   "\\N"
            },

            {
                "number":    12,
                "text":      "Remove loaves from pans, let cool",
                "then_wait": 7200,
                "comment":   "\\N"
            }
        ]
    }

write_response = table.put_item(Item=r1)

print(write_response)
