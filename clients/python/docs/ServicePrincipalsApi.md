# mcp_client.ServicePrincipalsApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post**](ServicePrincipalsApi.md#associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post) | **POST** /api/v1/service-principals/{service_id}/associate-user | Associate Service Principal With User
[**create_service_principal_api_v1_service_principals_post**](ServicePrincipalsApi.md#create_service_principal_api_v1_service_principals_post) | **POST** /api/v1/service-principals/ | Create Service Principal
[**delete_service_principal_api_v1_service_principals_service_id_delete**](ServicePrincipalsApi.md#delete_service_principal_api_v1_service_principals_service_id_delete) | **DELETE** /api/v1/service-principals/{service_id} | Delete Service Principal
[**get_service_principal_api_v1_service_principals_service_id_get**](ServicePrincipalsApi.md#get_service_principal_api_v1_service_principals_service_id_get) | **GET** /api/v1/service-principals/{service_id} | Get Service Principal
[**list_service_principals_api_v1_service_principals_get**](ServicePrincipalsApi.md#list_service_principals_api_v1_service_principals_get) | **GET** /api/v1/service-principals/ | List Service Principals
[**rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post**](ServicePrincipalsApi.md#rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post) | **POST** /api/v1/service-principals/{service_id}/rotate-secret | Rotate Service Principal Secret


# **associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post**
> ServicePrincipalResponse associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post(service_id, user_id, inherit_permissions=inherit_permissions, http_authorization_credentials=http_authorization_credentials)

Associate Service Principal With User

Associate service principal with a user for permission inheritance

Links a service principal to a user, optionally enabling permission inheritance.
When inherit_permissions is true, the service principal can act on behalf of
the user and inherit all their permissions.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.service_principal_response import ServicePrincipalResponse
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
    api_instance = mcp_client.ServicePrincipalsApi(api_client)
    service_id = 'service_id_example' # str | 
    user_id = 'user_id_example' # str | 
    inherit_permissions = True # bool |  (optional) (default to True)
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Associate Service Principal With User
        api_response = api_instance.associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post(service_id, user_id, inherit_permissions=inherit_permissions, http_authorization_credentials=http_authorization_credentials)
        print("The response of ServicePrincipalsApi->associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ServicePrincipalsApi->associate_service_principal_with_user_api_v1_service_principals_service_id_associate_user_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_id** | **str**|  | 
 **user_id** | **str**|  | 
 **inherit_permissions** | **bool**|  | [optional] [default to True]
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional] 

### Return type

[**ServicePrincipalResponse**](ServicePrincipalResponse.md)

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

# **create_service_principal_api_v1_service_principals_post**
> CreateServicePrincipalResponse create_service_principal_api_v1_service_principals_post(body_create_service_principal_api_v1_service_principals_post)

Create Service Principal

Create a new service principal

Creates a service principal with the specified authentication mode.
The calling user becomes the owner of the service principal.

Returns the created service principal with credentials (client_secret).
**Save the client_secret securely** - it will not be shown again.

Example:
    ```json
    {
        "name": "Batch ETL Job",
        "description": "Nightly data processing",
        "authentication_mode": "client_credentials",
        "associated_user_id": "user:alice",
        "inherit_permissions": true
    }
    ```

### Example


```python
import mcp_client
from mcp_client.models.body_create_service_principal_api_v1_service_principals_post import BodyCreateServicePrincipalApiV1ServicePrincipalsPost
from mcp_client.models.create_service_principal_response import CreateServicePrincipalResponse
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
    api_instance = mcp_client.ServicePrincipalsApi(api_client)
    body_create_service_principal_api_v1_service_principals_post = mcp_client.BodyCreateServicePrincipalApiV1ServicePrincipalsPost() # BodyCreateServicePrincipalApiV1ServicePrincipalsPost | 

    try:
        # Create Service Principal
        api_response = api_instance.create_service_principal_api_v1_service_principals_post(body_create_service_principal_api_v1_service_principals_post)
        print("The response of ServicePrincipalsApi->create_service_principal_api_v1_service_principals_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ServicePrincipalsApi->create_service_principal_api_v1_service_principals_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body_create_service_principal_api_v1_service_principals_post** | [**BodyCreateServicePrincipalApiV1ServicePrincipalsPost**](BodyCreateServicePrincipalApiV1ServicePrincipalsPost.md)|  | 

### Return type

[**CreateServicePrincipalResponse**](CreateServicePrincipalResponse.md)

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

# **delete_service_principal_api_v1_service_principals_service_id_delete**
> delete_service_principal_api_v1_service_principals_service_id_delete(service_id, http_authorization_credentials=http_authorization_credentials)

Delete Service Principal

Delete a service principal

Permanently deletes the service principal from Keycloak and OpenFGA.
This action cannot be undone.

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
    api_instance = mcp_client.ServicePrincipalsApi(api_client)
    service_id = 'service_id_example' # str | 
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Delete Service Principal
        api_instance.delete_service_principal_api_v1_service_principals_service_id_delete(service_id, http_authorization_credentials=http_authorization_credentials)
    except Exception as e:
        print("Exception when calling ServicePrincipalsApi->delete_service_principal_api_v1_service_principals_service_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_id** | **str**|  | 
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

# **get_service_principal_api_v1_service_principals_service_id_get**
> ServicePrincipalResponse get_service_principal_api_v1_service_principals_service_id_get(service_id, http_authorization_credentials=http_authorization_credentials)

Get Service Principal

Get details of a specific service principal

Returns service principal details if the current user is the owner.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.service_principal_response import ServicePrincipalResponse
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
    api_instance = mcp_client.ServicePrincipalsApi(api_client)
    service_id = 'service_id_example' # str | 
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Get Service Principal
        api_response = api_instance.get_service_principal_api_v1_service_principals_service_id_get(service_id, http_authorization_credentials=http_authorization_credentials)
        print("The response of ServicePrincipalsApi->get_service_principal_api_v1_service_principals_service_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ServicePrincipalsApi->get_service_principal_api_v1_service_principals_service_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_id** | **str**|  | 
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional] 

### Return type

[**ServicePrincipalResponse**](ServicePrincipalResponse.md)

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

# **list_service_principals_api_v1_service_principals_get**
> List[ServicePrincipalResponse] list_service_principals_api_v1_service_principals_get(http_authorization_credentials=http_authorization_credentials)

List Service Principals

List service principals owned by the current user

Returns all service principals where the current user is the owner.
Does not include client secrets.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.service_principal_response import ServicePrincipalResponse
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
    api_instance = mcp_client.ServicePrincipalsApi(api_client)
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # List Service Principals
        api_response = api_instance.list_service_principals_api_v1_service_principals_get(http_authorization_credentials=http_authorization_credentials)
        print("The response of ServicePrincipalsApi->list_service_principals_api_v1_service_principals_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ServicePrincipalsApi->list_service_principals_api_v1_service_principals_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional] 

### Return type

[**List[ServicePrincipalResponse]**](ServicePrincipalResponse.md)

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

# **rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post**
> RotateSecretResponse rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post(service_id, http_authorization_credentials=http_authorization_credentials)

Rotate Service Principal Secret

Rotate service principal secret

Generates a new client secret for the service principal.
The old secret will be invalidated immediately.

**Save the new client_secret securely** - update your service configuration
before the old secret expires.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.rotate_secret_response import RotateSecretResponse
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
    api_instance = mcp_client.ServicePrincipalsApi(api_client)
    service_id = 'service_id_example' # str | 
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Rotate Service Principal Secret
        api_response = api_instance.rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post(service_id, http_authorization_credentials=http_authorization_credentials)
        print("The response of ServicePrincipalsApi->rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling ServicePrincipalsApi->rotate_service_principal_secret_api_v1_service_principals_service_id_rotate_secret_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service_id** | **str**|  | 
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional] 

### Return type

[**RotateSecretResponse**](RotateSecretResponse.md)

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

