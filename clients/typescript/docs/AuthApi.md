# AuthApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**loginAuthLoginPost**](#loginauthloginpost) | **POST** /auth/login | Login|
|[**refreshTokenAuthRefreshPost**](#refreshtokenauthrefreshpost) | **POST** /auth/refresh | Refresh Token|

# **loginAuthLoginPost**
> LoginResponse loginAuthLoginPost(loginRequest)

Authenticate user and return JWT token  This endpoint accepts username and password, validates credentials, and returns a JWT token that can be used for subsequent tool calls.  The token should be included in the \'token\' field of all tool call requests.  Example:     POST /auth/login     {         \"username\": \"alice\",         \"password\": \"alice123\"     }      Response:     {         \"access_token\": \"eyJ...\",         \"token_type\": \"bearer\",         \"expires_in\": 3600,         \"user_id\": \"user:alice\",         \"username\": \"alice\",         \"roles\": [\"user\", \"premium\"]     }

### Example

```typescript
import {
    AuthApi,
    Configuration,
    LoginRequest
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new AuthApi(configuration);

let loginRequest: LoginRequest; //

const { status, data } = await apiInstance.loginAuthLoginPost(
    loginRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **loginRequest** | **LoginRequest**|  | |


### Return type

**LoginResponse**

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

# **refreshTokenAuthRefreshPost**
> RefreshTokenResponse refreshTokenAuthRefreshPost(refreshTokenRequest)

Refresh authentication token  Supports two refresh methods: 1. Keycloak: Uses refresh_token to get new access token 2. InMemory: Validates current token and issues new one  Example (Keycloak):     POST /auth/refresh     {         \"refresh_token\": \"eyJ...\"     }  Example (InMemory):     POST /auth/refresh     {         \"current_token\": \"eyJ...\"     }  Response:     {         \"access_token\": \"eyJ...\",         \"token_type\": \"bearer\",         \"expires_in\": 3600,         \"refresh_token\": \"eyJ...\"  // Keycloak only     }

### Example

```typescript
import {
    AuthApi,
    Configuration,
    RefreshTokenRequest
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new AuthApi(configuration);

let refreshTokenRequest: RefreshTokenRequest; //

const { status, data } = await apiInstance.refreshTokenAuthRefreshPost(
    refreshTokenRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **refreshTokenRequest** | **RefreshTokenRequest**|  | |


### Return type

**RefreshTokenResponse**

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

