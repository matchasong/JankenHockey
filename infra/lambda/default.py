import json
import os
import time

import boto3


CONNECTION_TABLE_NAME = "Connection"
SEND_MESSAGE_LAMBDA_NAME = "JankenHockeySendMessageFunction"

# Dynamodbテーブルクライアント
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)

# lambdaクライアント
lambda_client = boto3.client('lambda')


def handler(event, context):
    """
    handler

    defaultパスに対応したLambda関数
    """
    start_time = time.perf_counter()
    print(f"START {os.path.basename(__file__)}")
    print(f"event: {event}")

    post_data = json.loads(event.get('body', '{}')).get('data')
    print(f"post_data: {post_data} time: {time.perf_counter() - start_time}")

    items = connection_table.scan(ProjectionExpression='id').get('Items')
    if items is None:
        return {'statusCode': 500, 'body': 'no connection'}

    print(f"items:{items} time: {time.perf_counter() - start_time}")

    payload = {
        "data": post_data,
        "items": items
    }

    lambda_client.invoke(
        FunctionName='target-function-name',
        InvocationType='Event',
        Payload=json.dumps(payload)
    )

    print(f"subprocess lambda invoked time: {time.perf_counter() - start_time}")

    print(f"END {os.path.basename(__file__)} time: {time.perf_counter() - start_time}")
    return {
        "statusCode": 200,
        "body": "send message ok",
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }
    }