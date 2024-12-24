import asyncio
import json
import os
import time

import aiohttp
import boto3

CONNECTION_TABLE_NAME = "Connection"

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)

# API Gateway Management APIに接続
api_endpoint = os.environ.get('API_ENDPOINT')
stage = os.environ.get('STAGE')
url = F"{api_endpoint}/{stage}".replace('wss', 'https')
apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=F"{url}")


async def process_http_request(url, connection_id, data):
    endpoint_url = f"{url}/@connections/{connection_id}"
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint_url, json=data) as response:
            print(f"response: {response.status}")
            print(f"response: {await response.text()}")


async def async_send_message(post_data, item):
    """
    async_send_message
    """
    await process_http_request(url, item['id'], post_data)
    # await asyncio.to_thread(apigw_management.post_to_connection(ConnectionId=item['id'], Data=post_data))


async def async_main(tasks):
    """
    async_main
    """
    await asyncio.gather(*tasks, return_exceptions=True)


def handler(event, context):
    """
    handler
    """
    start_time = time.perf_counter()
    print(f"START {os.path.basename(__file__)}")
    print(f"stage: {stage}, api_endpoint: {api_endpoint}, {url}")
    print(f"event: {event}")

    post_data = json.loads(event.get('body', '{}')).get('data')
    print(f"post_data: {post_data} time: {time.perf_counter() - start_time}")

    items = connection_table.scan(ProjectionExpression='id').get('Items')
    if items is None:
        return {'statusCode': 500, 'body': 'no connection'}

    print(f"items:{items} time: {time.perf_counter() - start_time}")

    tasks = [async_send_message(post_data, item) for item in items]
    asyncio.run(async_main(tasks), debug=True)

    print(f"async_main called time: {time.perf_counter() - start_time}")

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