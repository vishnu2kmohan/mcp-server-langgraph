# ServicePrincipalsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**associateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost**](#associateserviceprincipalwithuserapiv1serviceprincipalsserviceidassociateuserpost) | **POST** /api/v1/service-principals/{service_id}/associate-user | Associate Service Principal With User|
|[**createServicePrincipalApiV1ServicePrincipalsPost**](#createserviceprincipalapiv1serviceprincipalspost) | **POST** /api/v1/service-principals/ | Create Service Principal|
|[**deleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete**](#deleteserviceprincipalapiv1serviceprincipalsserviceiddelete) | **DELETE** /api/v1/service-principals/{service_id} | Delete Service Principal|
|[**getServicePrincipalApiV1ServicePrincipalsServiceIdGet**](#getserviceprincipalapiv1serviceprincipalsserviceidget) | **GET** /api/v1/service-principals/{service_id} | Get Service Principal|
|[**listServicePrincipalsApiV1ServicePrincipalsGet**](#listserviceprincipalsapiv1serviceprincipalsget) | **GET** /api/v1/service-principals/ | List Service Principals|
|[**rotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost**](#rotateserviceprincipalsecretapiv1serviceprincipalsserviceidrotatesecretpost) | **POST** /api/v1/service-principals/{service_id}/rotate-secret | Rotate Service Principal Secret|

# **associateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost**
> ServicePrincipalResponse associateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost()

Associate service principal with a user for permission inheritance  Links a service principal to a user, optionally enabling permission inheritance. When inherit_permissions is true, the service principal can act on behalf of the user and inherit all their permissions.

### Example

```typescript
import {
    ServicePrincipalsApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new ServicePrincipalsApi(configuration);

let serviceId: string; // (default to undefined)
let userId: string; // (default to undefined)
let inheritPermissions: boolean; // (optional) (default to true)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.associateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost(
    serviceId,
    userId,
    inheritPermissions,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **serviceId** | [**string**] |  | defaults to undefined|
| **userId** | [**string**] |  | defaults to undefined|
| **inheritPermissions** | [**boolean**] |  | (optional) defaults to true|


### Return type

**ServicePrincipalResponse**

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

# **createServicePrincipalApiV1ServicePrincipalsPost**
> CreateServicePrincipalResponse createServicePrincipalApiV1ServicePrincipalsPost(bodyCreateServicePrincipalApiV1ServicePrincipalsPost)

Create a new service principal  Creates a service principal with the specified authentication mode. The calling user becomes the owner of the service principal.  Returns the created service principal with credentials (client_secret). **Save the client_secret securely** - it will not be shown again.  Example:     ```json     {         \"name\": \"Batch ETL Job\",         \"description\": \"Nightly data processing\",         \"authentication_mode\": \"client_credentials\",         \"associated_user_id\": \"user:alice\",         \"inherit_permissions\": true     }     ```

### Example

```typescript
import {
    ServicePrincipalsApi,
    Configuration,
    BodyCreateServicePrincipalApiV1ServicePrincipalsPost
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new ServicePrincipalsApi(configuration);

let bodyCreateServicePrincipalApiV1ServicePrincipalsPost: BodyCreateServicePrincipalApiV1ServicePrincipalsPost; //

const { status, data } = await apiInstance.createServicePrincipalApiV1ServicePrincipalsPost(
    bodyCreateServicePrincipalApiV1ServicePrincipalsPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyCreateServicePrincipalApiV1ServicePrincipalsPost** | **BodyCreateServicePrincipalApiV1ServicePrincipalsPost**|  | |


### Return type

**CreateServicePrincipalResponse**

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

# **deleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete**
> deleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete()

Delete a service principal  Permanently deletes the service principal from Keycloak and OpenFGA. This action cannot be undone.

### Example

```typescript
import {
    ServicePrincipalsApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new ServicePrincipalsApi(configuration);

let serviceId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.deleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete(
    serviceId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **serviceId** | [**string**] |  | defaults to undefined|


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

# **getServicePrincipalApiV1ServicePrincipalsServiceIdGet**
> ServicePrincipalResponse getServicePrincipalApiV1ServicePrincipalsServiceIdGet()

Get details of a specific service principal  Returns service principal details if the current user is the owner.

### Example

```typescript
import {
    ServicePrincipalsApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new ServicePrincipalsApi(configuration);

let serviceId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.getServicePrincipalApiV1ServicePrincipalsServiceIdGet(
    serviceId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **serviceId** | [**string**] |  | defaults to undefined|


### Return type

**ServicePrincipalResponse**

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

# **listServicePrincipalsApiV1ServicePrincipalsGet**
> Array<ServicePrincipalResponse> listServicePrincipalsApiV1ServicePrincipalsGet()

List service principals owned by the current user  Returns all service principals where the current user is the owner. Does not include client secrets.

### Example

```typescript
import {
    ServicePrincipalsApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new ServicePrincipalsApi(configuration);

let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.listServicePrincipalsApiV1ServicePrincipalsGet(
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |


### Return type

**Array<ServicePrincipalResponse>**

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

# **rotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost**
> RotateSecretResponse rotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost()

Rotate service principal secret  Generates a new client secret for the service principal. The old secret will be invalidated immediately.  **Save the new client_secret securely** - update your service configuration before the old secret expires.

### Example

```typescript
import {
    ServicePrincipalsApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new ServicePrincipalsApi(configuration);

let serviceId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.rotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost(
    serviceId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **serviceId** | [**string**] |  | defaults to undefined|


### Return type

**RotateSecretResponse**

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

