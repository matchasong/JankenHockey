import json
import logging
import os

import boto3
from botocore.exceptions import ClientError


# Cognito client
cognito_client = boto3.client("cognito-idp")

# Response headers
RESPONSE_HEADERS = {"Content-Type": "application/json"}

# logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


def handler(event, context):
    """handler
    Lambda関数(JankenHockeyLoginFunction)のhandler
    トップ画面にてAPI Gateway経由で呼び出される。
    ログインおよびサインアップ処理を行う。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(結果メッセージ)
        成功時にはtoken(AccessToken)およびidTokenを返す。
    """
    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"Login event: {event}")

    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action")  # "login" or "signup"
        username = body.get("username", "").strip()
        password = body.get("password", "")

        if not username or not password:
            logger.warning(
                f"Validation error: Missing username ({bool(username)}) or password ({bool(password)})"
            )
            return {
                "statusCode": 400,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "システムエラーが発生しました"}),
            }

        user_pool_id = os.environ.get("USER_POOL_ID")
        client_id = os.environ.get("CLIENT_ID")

        if not user_pool_id or not client_id:
            logger.warning(
                f"Configuration error: USER_POOL_ID ({bool(user_pool_id)}) or CLIENT_ID ({bool(client_id)}) missing"
            )
            return {
                "statusCode": 500,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "システムエラーが発生しました"}),
            }

        if action == "signup":
            return handle_signup(username, password, user_pool_id, client_id)
        elif action == "login":
            return handle_login(username, password, user_pool_id, client_id)
        else:
            return {
                "statusCode": 400,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps(
                    {"error": "Invalid action. Use 'login' or 'signup'"}
                ),
            }

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps({"error": "システムエラーが発生しました"}),
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps({"error": "システムエラーが発生しました"}),
        }


def handle_signup(username, password, user_pool_id, client_id):
    """
    Handle user signup
    """
    try:
        # Check if user already exists
        try:
            cognito_client.admin_get_user(UserPoolId=user_pool_id, Username=username)
            # User exists, try to login instead
            return handle_login(username, password, user_pool_id, client_id)
        except ClientError as e:
            if e.response["Error"]["Code"] != "UserNotFoundException":
                raise e

        # Create new user
        cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            TemporaryPassword=password,
            MessageAction="SUPPRESS",  # Don't send welcome email
        )

        # Set permanent password
        cognito_client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True,
        )

        logger.info(f"User created successfully: {username}")

        # Now login the user
        return handle_login(username, password, user_pool_id, client_id)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.warning(f"Signup error: {error_code} - {error_message}")

        if error_code == "InvalidPasswordException":
            logger.warning(f"Signup InvalidPasswordException: {error_message}")
            return {
                "statusCode": 400,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "システムエラーが発生しました"}),
            }
        else:
            logger.error(f"Signup other error: {error_code} - {error_message}")
            return {
                "statusCode": 400,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "システムエラーが発生しました"}),
            }


def handle_login(username, password, user_pool_id, client_id):
    """
    Handle user login
    """
    try:
        response = cognito_client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        auth_result = response.get("AuthenticationResult")
        if not auth_result:
            logger.error("Authentication failed: No AuthenticationResult in response")
            return {
                "statusCode": 401,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "Authentication failed"}),
            }

        logger.info(f"User logged in successfully: {username}")

        logger.info(f"END {os.path.basename(__file__)}")

        return {
            "statusCode": 200,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps(
                {
                    "message": "Login successful",
                    "token": auth_result[
                        "AccessToken"
                    ],  # Web Socket用にAccessTokenを返す
                    "idToken": auth_result["IdToken"],  # API Gateway用にIdTokenを返す
                    "username": username,
                }
            ),
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.warning(f"Login error: {error_code} - {error_message}")

        if error_code in ["NotAuthorizedException", "UserNotFoundException"]:
            return {
                "statusCode": 401,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "Invalid username or password"}),
            }
        else:
            logger.error(f"Login other error: {error_code} - {error_message}")
            return {
                "statusCode": 400,
                "headers": RESPONSE_HEADERS,
                "body": json.dumps({"error": "システムエラーが発生しました"}),
            }
