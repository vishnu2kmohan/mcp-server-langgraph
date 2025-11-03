# mcp_client.AuthApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**login_auth_login_post**](AuthApi.md#login_auth_login_post) | **POST** /auth/login | Login
[**refresh_token_auth_refresh_post**](AuthApi.md#refresh_token_auth_refresh_post) | **POST** /auth/refresh | Refresh Token


# **login_auth_login_post**
> LoginResponse login_auth_login_post(login_request)

Login

Authenticate user and return JWT token

This endpoint accepts username and password, validates credentials,
and returns a JWT token that can be used for subsequent tool calls.

The token should be included in the 'token' field of all tool call requests.

Example:
    POST /auth/login
    {
        "username": "alice",
        "password": "alice123"
    }

    Response:
    {
        "access_token": "eyJ...",
        "token_type": "bearer",
        "expires_in": 3600,
        "user_id": "user:alice",
        "username": "alice",
        "roles": ["user", "premium"]
    }

### Example


```python
import mcp_client
from mcp_client.models.login_request import LoginRequest
from mcp_client.models.login_response import LoginResponse
from mcp_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = mcp_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with mcp_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = mcp_client.AuthApi(api_client)
    login_request = mcp_client.LoginRequest() # LoginRequest | 

    try:
        # Login
        api_response = api_instance.login_auth_login_post(login_request)
        print("The response of AuthApi->login_auth_login_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AuthApi->login_auth_login_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **login_request** | [**LoginRequest**](LoginRequest.md)|  | 

### Return type

[**LoginResponse**](LoginResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **refresh_token_auth_refresh_post**
> RefreshTokenResponse refresh_token_auth_refresh_post(refresh_token_request)

Refresh Token

Refresh authentication token

Supports two refresh methods:
1. Keycloak: Uses refresh_token to get new access token
2. InMemory: Validates current token and issues new one

Example (Keycloak):
    POST /auth/refresh
    {
        "refresh_token": "eyJ..."
    }

Example (InMemory):
    POST /auth/refresh
    {
        "current_token": "eyJ..."
    }

Response:
    {
        "access_token": "eyJ...",
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": "eyJ..."  // Keycloak only
    }

### Example


```python
import mcp_client
from mcp_client.models.refresh_token_request import RefreshTokenRequest
from mcp_client.models.refresh_token_response import RefreshTokenResponse
from mcp_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = mcp_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with mcp_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = mcp_client.AuthApi(api_client)
    refresh_token_request = mcp_client.RefreshTokenRequest() # RefreshTokenRequest | 

    try:
        # Refresh Token
        api_response = api_instance.refresh_token_auth_refresh_post(refresh_token_request)
        print("The response of AuthApi->refresh_token_auth_refresh_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AuthApi->refresh_token_auth_refresh_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **refresh_token_request** | [**RefreshTokenRequest**](RefreshTokenRequest.md)|  | 

### Return type

[**RefreshTokenResponse**](RefreshTokenResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

