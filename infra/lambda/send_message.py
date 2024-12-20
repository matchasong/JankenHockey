import json
import os
import time

import boto3

CONNECTION_TABLE_NAME = "Connection"

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)

# API Gateway Management APIに接続
api_endpoint = os.environ.get('API_ENDPOINT')
stage = os.environ.get('STAGE')
apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=F"{api_endpoint}/{stage}")


def handler(event, context):
    """
    handler
    """
    start_time = time.perf_counter()
    print(f"START {os.path.basename(__file__)}")
    print(f"event: {event}")

    post_data = json.loads(event.get('body', '{}')).get('data')
    print(f"post_data: {post_data} time: {start_time - time.perf_counter()}")

    items = connection_table.scan(ProjectionExpression='id').get('Items')
    if items is None:
        return {'statusCode': 500, 'body': 'no connection'}

    print(f"items:{items} time: {start_time - time.perf_counter()}")

    for item in items:
        try:
            print(item)
            _ = apigw_management.post_to_connection(ConnectionId=item['id'], Data=post_data)
            print(f"apigw_called time: {start_time - time.perf_counter()}")
        except Exception as e:
            print(e)
            break

    end_time = time.perf_counter()
    print(f"END {os.path.basename(__file__)} {end_time - start_time}")

    return {
        "statusCode": 200,
        "body": "send message ok",
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }
    }
