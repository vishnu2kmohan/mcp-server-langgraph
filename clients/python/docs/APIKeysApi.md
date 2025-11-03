# mcp_client.APIKeysApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_api_key_api_v1_api_keys_post**](APIKeysApi.md#create_api_key_api_v1_api_keys_post) | **POST** /api/v1/api-keys/ | Create Api Key
[**list_api_keys_api_v1_api_keys_get**](APIKeysApi.md#list_api_keys_api_v1_api_keys_get) | **GET** /api/v1/api-keys/ | List Api Keys
[**revoke_api_key_api_v1_api_keys_key_id_delete**](APIKeysApi.md#revoke_api_key_api_v1_api_keys_key_id_delete) | **DELETE** /api/v1/api-keys/{key_id} | Revoke Api Key
[**rotate_api_key_api_v1_api_keys_key_id_rotate_post**](APIKeysApi.md#rotate_api_key_api_v1_api_keys_key_id_rotate_post) | **POST** /api/v1/api-keys/{key_id}/rotate | Rotate Api Key


# **create_api_key_api_v1_api_keys_post**
> CreateAPIKeyResponse create_api_key_api_v1_api_keys_post(body_create_api_key_api_v1_api_keys_post)

Create Api Key

Create a new API key for the current user

Creates a cryptographically secure API key with bcrypt hashing.
**Save the returned api_key securely** - it will not be shown again.

Maximum 5 keys per user. Revoke an existing key before creating more.

Example:
    ```json
    {
        "name": "Production API Key",
        "expires_days": 365
    }
    ```

### Example


```python
import mcp_client
from mcp_client.models.body_create_api_key_api_v1_api_keys_post import BodyCreateApiKeyApiV1ApiKeysPost
from mcp_client.models.create_api_key_response import CreateAPIKeyResponse
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
    api_instance = mcp_client.APIKeysApi(api_client)
    body_create_api_key_api_v1_api_keys_post = mcp_client.BodyCreateApiKeyApiV1ApiKeysPost() # BodyCreateApiKeyApiV1ApiKeysPost |

    try:
        # Create Api Key
        api_response = api_instance.create_api_key_api_v1_api_keys_post(body_create_api_key_api_v1_api_keys_post)
        print("The response of APIKeysApi->create_api_key_api_v1_api_keys_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->create_api_key_api_v1_api_keys_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body_create_api_key_api_v1_api_keys_post** | [**BodyCreateApiKeyApiV1ApiKeysPost**](BodyCreateApiKeyApiV1ApiKeysPost.md)|  |

### Return type

[**CreateAPIKeyResponse**](CreateAPIKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_api_keys_api_v1_api_keys_get**
> List[APIKeyResponse] list_api_keys_api_v1_api_keys_get(http_authorization_credentials=http_authorization_credentials)

List Api Keys

List all API keys for the current user

Returns metadata for all keys (name, created, expires, last_used).
Does not include the actual API keys.

### Example


```python
import mcp_client
from mcp_client.models.api_key_response import APIKeyResponse
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
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
    api_instance = mcp_client.APIKeysApi(api_client)
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # List Api Keys
        api_response = api_instance.list_api_keys_api_v1_api_keys_get(http_authorization_credentials=http_authorization_credentials)
        print("The response of APIKeysApi->list_api_keys_api_v1_api_keys_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->list_api_keys_api_v1_api_keys_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**List[APIKeyResponse]**](APIKeyResponse.md)

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

# **revoke_api_key_api_v1_api_keys_key_id_delete**
> revoke_api_key_api_v1_api_keys_key_id_delete(key_id, http_authorization_credentials=http_authorization_credentials)

Revoke Api Key

Revoke an API key

Permanently deletes the API key. This action cannot be undone.
Any clients using this key will immediately lose access.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
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
    api_instance = mcp_client.APIKeysApi(api_client)
    key_id = 'key_id_example' # str |
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Revoke Api Key
        api_instance.revoke_api_key_api_v1_api_keys_key_id_delete(key_id, http_authorization_credentials=http_authorization_credentials)
    except Exception as e:
        print("Exception when calling APIKeysApi->revoke_api_key_api_v1_api_keys_key_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **key_id** | **str**|  |
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**204** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **rotate_api_key_api_v1_api_keys_key_id_rotate_post**
> RotateAPIKeyResponse rotate_api_key_api_v1_api_keys_key_id_rotate_post(key_id, http_authorization_credentials=http_authorization_credentials)

Rotate Api Key

Rotate an API key

Generates a new API key while keeping the same key_id.
The old key is invalidated immediately.

**Save the new_api_key securely** - update your client configuration.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.rotate_api_key_response import RotateAPIKeyResponse
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
    api_instance = mcp_client.APIKeysApi(api_client)
    key_id = 'key_id_example' # str |
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Rotate Api Key
        api_response = api_instance.rotate_api_key_api_v1_api_keys_key_id_rotate_post(key_id, http_authorization_credentials=http_authorization_credentials)
        print("The response of APIKeysApi->rotate_api_key_api_v1_api_keys_key_id_rotate_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIKeysApi->rotate_api_key_api_v1_api_keys_key_id_rotate_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **key_id** | **str**|  |
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**RotateAPIKeyResponse**](RotateAPIKeyResponse.md)

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
