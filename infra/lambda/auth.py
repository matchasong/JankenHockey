import os
import jwt
import logging
from jwt.algorithms import RSAAlgorithm
import json
import time

import requests
import boto3


# logger setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


# JWKSキャッシュ（グローバル変数でキャッシュ）
_jwks_cache = {}
_cache_expiry = 0


def get_jwks():
    """CognitoのJWKSを取得（キャッシュ機能付き）"""
    global _jwks_cache, _cache_expiry

    current_time = time.time()
    if current_time < _cache_expiry and _jwks_cache:
        logger.info("Using cached JWKS")
        return _jwks_cache

    logger.info("cached JWKS is expired. Fetching new JWKS from Cognito")

    # JWKS取得
    region = os.environ["AWS_REGION"]
    user_pool_id = os.environ["USER_POOL_ID"]
    jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"

    try:
        logger.info(f"Fetching JWKS from {jwks_url}")
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        logger.info(f"Fetching JWKS from {jwks_url} succeeded")

        jwks = response.json()

        # キャッシュ更新（1時間）
        _jwks_cache = jwks
        _cache_expiry = current_time + 3600

        return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {str(e)}")
        if _jwks_cache:  # 古いキャッシュがあれば使用
            logger.warning("Using old cached JWKS due to fetch failure")
            return _jwks_cache
        raise


def get_public_key(token):
    """JWTトークンから公開鍵を取得"""
    try:
        # JWTヘッダーからkidを取得
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header["kid"]

        # JWKSから該当のキーを検索
        jwks = get_jwks()
        for key in jwks["keys"]:
            if key["kid"] == kid:
                return RSAAlgorithm.from_jwk(json.dumps(key))

        raise ValueError(f"Unable to find a signing key that matches: '{kid}'")

    except Exception as e:
        logger.error(f"Error getting public key: {str(e)}")
        raise


def handler(event, context):
    """
    Lambdaオーソライザーのhandler
    API Gateway(WebSocket)経由で呼び出され、CognitoのJWTトークンを検証し、
    検証OKであればAPI呼び出しを許可するIAMポリシーを生成する。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: IAMポリシー
    """
    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    try:
        # 情報の取得
        # Get token from query string
        token = event.get("queryStringParameters", {}).get("token")
        if not token:
            logger.error("No token provided")
            raise Exception("Unauthorized")

        # Get Cognito User Pool info
        user_pool_id = os.environ.get("USER_POOL_ID")
        client_id = os.environ.get("CLIENT_ID")

        if not user_pool_id or not client_id:
            logger.error("Missing USER_POOL_ID or CLIENT_ID")
            raise Exception("Internal Error")

        # トークン検証
        # 署名用の公開鍵取得
        public_key = get_public_key(token)

        # デコード
        decoded_token = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=f"https://cognito-idp.{boto3.Session().region_name}.amazonaws.com/{user_pool_id}",
            options={
                "verify_signature": True,  # 署名検証ON
                "verify_aud": False,  # オーディエンス検証 -> Cognito User Poolのaccess tokenはaudがないためFalse
                "verify_iss": True,  # 発行者検証
                "verify_exp": True,  # 有効期限検証
            },
        )

        logger.debug(f"Decoded token: {decoded_token}")

        logger.info(f"Token decoded successfully for user: {decoded_token.get('sub')}")

        # Policyの作成
        # contextに渡す情報
        user_context = {
            "userId": decoded_token["sub"],
            "username": decoded_token.get("username", ""),
            "email": decoded_token.get("email", ""),
            "tokenUse": decoded_token.get("token_use", "access"),
        }

        logger.debug(f"User context: {user_context}")
        logger.info(f"END {os.path.basename(__file__)}")

        return generate_policy(
            principal_id=decoded_token["sub"],
            effect="Allow",
            resource=event["methodArn"],
            context=user_context,
        )

    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        # Return deny policy
        deny = generate_policy("user", "Deny", event.get("methodArn", "*"))
        return deny


def generate_policy(principal_id, effect, resource, context=None):
    """
    Generate IAM policy for API Gateway
    """
    policy = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}
            ],
        },
    }

    if context:
        # contextの値は文字列である必要がある
        policy["context"] = {k: str(v) for k, v in context.items()}

    logger.debug(f"Generated policy: {policy}")

    return policy
