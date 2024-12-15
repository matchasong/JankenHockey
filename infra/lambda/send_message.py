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

    post_data = json.loads(event.get('body', '{}')).get('data')
    print(post_data)
    domain_name = event.get('requestContext', {}).get('domainName')
    stage = event.get('requestContext', {}).get('stage')

    items = connection_table.scan(ProjectionExpression='id').get('Items')
    if items is None:
        return {'statusCode': 500, 'body': 'no connection'}

    apigw_management = boto3.client('apigatewaymanagementapi',
                                    endpoint_url=F"https://{domain_name}/{stage}")
    for item in items:
        try:
            print(item)
            _ = apigw_management.post_to_connection(ConnectionId=item['id'], Data=post_data)
        except Exception as e:
            print(e)
            break

    print(f"END {os.path.basename(__file__)}")

    return {
        "statusCode": 200,
        "body": "send message ok",
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }
    }
