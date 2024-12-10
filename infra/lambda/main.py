import json

import boto3

HISTORY_TABLE_NAME = "GameHistory"

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
hisotry_table = dynamodb.Table(HISTORY_TABLE_NAME)


def handler(event, context):
    """
    handler
    """
    return {
        "statusCode": 200,
        "body": json.dumps("Hello from Lambda!"),
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }
    }
