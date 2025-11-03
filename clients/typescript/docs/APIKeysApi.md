# APIKeysApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createApiKeyApiV1ApiKeysPost**](#createapikeyapiv1apikeyspost) | **POST** /api/v1/api-keys/ | Create Api Key|
|[**listApiKeysApiV1ApiKeysGet**](#listapikeysapiv1apikeysget) | **GET** /api/v1/api-keys/ | List Api Keys|
|[**revokeApiKeyApiV1ApiKeysKeyIdDelete**](#revokeapikeyapiv1apikeyskeyiddelete) | **DELETE** /api/v1/api-keys/{key_id} | Revoke Api Key|
|[**rotateApiKeyApiV1ApiKeysKeyIdRotatePost**](#rotateapikeyapiv1apikeyskeyidrotatepost) | **POST** /api/v1/api-keys/{key_id}/rotate | Rotate Api Key|

# **createApiKeyApiV1ApiKeysPost**
> CreateAPIKeyResponse createApiKeyApiV1ApiKeysPost(bodyCreateApiKeyApiV1ApiKeysPost)

Create a new API key for the current user  Creates a cryptographically secure API key with bcrypt hashing. **Save the returned api_key securely** - it will not be shown again.  Maximum 5 keys per user. Revoke an existing key before creating more.  Example:     ```json     {         \"name\": \"Production API Key\",         \"expires_days\": 365     }     ```

### Example

```typescript
import {
    APIKeysApi,
    Configuration,
    BodyCreateApiKeyApiV1ApiKeysPost
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let bodyCreateApiKeyApiV1ApiKeysPost: BodyCreateApiKeyApiV1ApiKeysPost; //

const { status, data } = await apiInstance.createApiKeyApiV1ApiKeysPost(
    bodyCreateApiKeyApiV1ApiKeysPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyCreateApiKeyApiV1ApiKeysPost** | **BodyCreateApiKeyApiV1ApiKeysPost**|  | |


### Return type

**CreateAPIKeyResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**401** | Unauthorized - Invalid or missing authentication token |  -  |
|**403** | Forbidden - Insufficient permissions |  -  |
|**429** | Too Many Requests - Rate limit exceeded |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **listApiKeysApiV1ApiKeysGet**
> Array<APIKeyResponse> listApiKeysApiV1ApiKeysGet()

List all API keys for the current user  Returns metadata for all keys (name, created, expires, last_used). Does not include the actual API keys.

### Example

```typescript
import {
    APIKeysApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.listApiKeysApiV1ApiKeysGet(
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |


### Return type

**Array<APIKeyResponse>**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**401** | Unauthorized - Invalid or missing authentication token |  -  |
|**403** | Forbidden - Insufficient permissions |  -  |
|**429** | Too Many Requests - Rate limit exceeded |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **revokeApiKeyApiV1ApiKeysKeyIdDelete**
> revokeApiKeyApiV1ApiKeysKeyIdDelete()

Revoke an API key  Permanently deletes the API key. This action cannot be undone. Any clients using this key will immediately lose access.

### Example

```typescript
import {
    APIKeysApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let keyId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.revokeApiKeyApiV1ApiKeysKeyIdDelete(
    keyId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **keyId** | [**string**] |  | defaults to undefined|


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
|**204** | Successful Response |  -  |
|**401** | Unauthorized - Invalid or missing authentication token |  -  |
|**403** | Forbidden - Insufficient permissions |  -  |
|**429** | Too Many Requests - Rate limit exceeded |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **rotateApiKeyApiV1ApiKeysKeyIdRotatePost**
> RotateAPIKeyResponse rotateApiKeyApiV1ApiKeysKeyIdRotatePost()

Rotate an API key  Generates a new API key while keeping the same key_id. The old key is invalidated immediately.  **Save the new_api_key securely** - update your client configuration.

### Example

```typescript
import {
    APIKeysApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new APIKeysApi(configuration);

let keyId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.rotateApiKeyApiV1ApiKeysKeyIdRotatePost(
    keyId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **keyId** | [**string**] |  | defaults to undefined|


### Return type

**RotateAPIKeyResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**401** | Unauthorized - Invalid or missing authentication token |  -  |
|**403** | Forbidden - Insufficient permissions |  -  |
|**429** | Too Many Requests - Rate limit exceeded |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

