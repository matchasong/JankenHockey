import json
import os

import boto3

CONNECTION_TABLE_NAME = "Connection"

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)


def handler(event, context):
    """
    handler
    """
    print(f"START {os.path.basename(__file__)}")
    print(f"event: {event}")

    connection_id = event.get('requestContext', {}).get('connectionId')
    print(f"connection_id: {connection_id}")

    result = connection_table.delete_item(Key={'id': connection_id})
    print(f"result: {result}")
    
    print(f"END {os.path.basename(__file__)}")

    return {
        "statusCode": 200,
        "body": "disconnect ok",
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }
    }
