import asyncio
import os
import time

import boto3

# API Gateway Management APIに接続
api_endpoint = os.environ.get('API_ENDPOINT')
stage = os.environ.get('STAGE')
url = F"{api_endpoint}/{stage}".replace('wss', 'https')
apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=F"{url}")


async def async_send_message(post_data, item):
    """
    async_send_message
    """
    await asyncio.to_thread(apigw_management.post_to_connection(ConnectionId=item['id'], Data=post_data))


async def async_main(tasks):
    """
    async_main
    """
    await asyncio.gather(*tasks)


def handler(event, context):
    """
    handler
    """
    start_time = time.perf_counter()
    print(f"START {os.path.basename(__file__)}")
    print(f"stage: {stage}, api_endpoint: {api_endpoint}, {url}")
    print(f"event: {event}")

    post_data = event.get("data")
    print(f"post_data: {post_data} time: {start_time - time.perf_counter()}")

    items = event.get("items")
    print(f"items: {post_data} time: {start_time - time.perf_counter()}")

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