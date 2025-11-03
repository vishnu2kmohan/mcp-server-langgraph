# mcp_client.SCIM20Api

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_group_scim_v2_groups_post**](SCIM20Api.md#create_group_scim_v2_groups_post) | **POST** /scim/v2/Groups | Create Group
[**create_user_scim_v2_users_post**](SCIM20Api.md#create_user_scim_v2_users_post) | **POST** /scim/v2/Users | Create User
[**delete_user_scim_v2_users_user_id_delete**](SCIM20Api.md#delete_user_scim_v2_users_user_id_delete) | **DELETE** /scim/v2/Users/{user_id} | Delete User
[**get_group_scim_v2_groups_group_id_get**](SCIM20Api.md#get_group_scim_v2_groups_group_id_get) | **GET** /scim/v2/Groups/{group_id} | Get Group
[**get_user_scim_v2_users_user_id_get**](SCIM20Api.md#get_user_scim_v2_users_user_id_get) | **GET** /scim/v2/Users/{user_id} | Get User
[**list_users_scim_v2_users_get**](SCIM20Api.md#list_users_scim_v2_users_get) | **GET** /scim/v2/Users | List Users
[**replace_user_scim_v2_users_user_id_put**](SCIM20Api.md#replace_user_scim_v2_users_user_id_put) | **PUT** /scim/v2/Users/{user_id} | Replace User
[**update_user_scim_v2_users_user_id_patch**](SCIM20Api.md#update_user_scim_v2_users_user_id_patch) | **PATCH** /scim/v2/Users/{user_id} | Update User


# **create_group_scim_v2_groups_post**
> SCIMGroup create_group_scim_v2_groups_post(body_create_group_scim_v2_groups_post)

Create Group

Create a new group (SCIM 2.0)

Example:
    ```json
    {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": "Engineering",
        "members": [
            {"value": "user-id-123", "display": "Alice Smith"}
        ]
    }
    ```

### Example


```python
import mcp_client
from mcp_client.models.body_create_group_scim_v2_groups_post import BodyCreateGroupScimV2GroupsPost
from mcp_client.models.scim_group import SCIMGroup
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
    api_instance = mcp_client.SCIM20Api(api_client)
    body_create_group_scim_v2_groups_post = mcp_client.BodyCreateGroupScimV2GroupsPost() # BodyCreateGroupScimV2GroupsPost |

    try:
        # Create Group
        api_response = api_instance.create_group_scim_v2_groups_post(body_create_group_scim_v2_groups_post)
        print("The response of SCIM20Api->create_group_scim_v2_groups_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->create_group_scim_v2_groups_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body_create_group_scim_v2_groups_post** | [**BodyCreateGroupScimV2GroupsPost**](BodyCreateGroupScimV2GroupsPost.md)|  |

### Return type

[**SCIMGroup**](SCIMGroup.md)

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

# **create_user_scim_v2_users_post**
> SCIMUser create_user_scim_v2_users_post(body_create_user_scim_v2_users_post)

Create User

Create a new user (SCIM 2.0)

Provisions user in Keycloak and syncs roles to OpenFGA.

Example:
    ```json
    {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "alice@example.com",
        "name": {
            "givenName": "Alice",
            "familyName": "Smith"
        },
        "emails": [{
            "value": "alice@example.com",
            "primary": true
        }],
        "active": true
    }
    ```

### Example


```python
import mcp_client
from mcp_client.models.body_create_user_scim_v2_users_post import BodyCreateUserScimV2UsersPost
from mcp_client.models.scim_user import SCIMUser
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
    api_instance = mcp_client.SCIM20Api(api_client)
    body_create_user_scim_v2_users_post = mcp_client.BodyCreateUserScimV2UsersPost() # BodyCreateUserScimV2UsersPost |

    try:
        # Create User
        api_response = api_instance.create_user_scim_v2_users_post(body_create_user_scim_v2_users_post)
        print("The response of SCIM20Api->create_user_scim_v2_users_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->create_user_scim_v2_users_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body_create_user_scim_v2_users_post** | [**BodyCreateUserScimV2UsersPost**](BodyCreateUserScimV2UsersPost.md)|  |

### Return type

[**SCIMUser**](SCIMUser.md)

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

# **delete_user_scim_v2_users_user_id_delete**
> delete_user_scim_v2_users_user_id_delete(user_id, http_authorization_credentials=http_authorization_credentials)

Delete User

Delete (deactivate) user (SCIM 2.0)

Deactivates user in Keycloak and removes OpenFGA tuples.

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
    api_instance = mcp_client.SCIM20Api(api_client)
    user_id = 'user_id_example' # str |
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Delete User
        api_instance.delete_user_scim_v2_users_user_id_delete(user_id, http_authorization_credentials=http_authorization_credentials)
    except Exception as e:
        print("Exception when calling SCIM20Api->delete_user_scim_v2_users_user_id_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**|  |
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

# **get_group_scim_v2_groups_group_id_get**
> SCIMGroup get_group_scim_v2_groups_group_id_get(group_id, http_authorization_credentials=http_authorization_credentials)

Get Group

Get group by ID (SCIM 2.0)

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.scim_group import SCIMGroup
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
    api_instance = mcp_client.SCIM20Api(api_client)
    group_id = 'group_id_example' # str |
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Get Group
        api_response = api_instance.get_group_scim_v2_groups_group_id_get(group_id, http_authorization_credentials=http_authorization_credentials)
        print("The response of SCIM20Api->get_group_scim_v2_groups_group_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->get_group_scim_v2_groups_group_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **group_id** | **str**|  |
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**SCIMGroup**](SCIMGroup.md)

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

# **get_user_scim_v2_users_user_id_get**
> SCIMUser get_user_scim_v2_users_user_id_get(user_id, http_authorization_credentials=http_authorization_credentials)

Get User

Get user by ID (SCIM 2.0)

Returns user in SCIM format.

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.scim_user import SCIMUser
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
    api_instance = mcp_client.SCIM20Api(api_client)
    user_id = 'user_id_example' # str |
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Get User
        api_response = api_instance.get_user_scim_v2_users_user_id_get(user_id, http_authorization_credentials=http_authorization_credentials)
        print("The response of SCIM20Api->get_user_scim_v2_users_user_id_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->get_user_scim_v2_users_user_id_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**|  |
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**SCIMUser**](SCIMUser.md)

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

# **list_users_scim_v2_users_get**
> SCIMListResponse list_users_scim_v2_users_get(filter=filter, start_index=start_index, count=count, http_authorization_credentials=http_authorization_credentials)

List Users

List/search users (SCIM 2.0)

Supports basic filtering (e.g., 'userName eq "alice@example.com"').

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.scim_list_response import SCIMListResponse
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
    api_instance = mcp_client.SCIM20Api(api_client)
    filter = 'filter_example' # str | SCIM filter expression (optional)
    start_index = 1 # int | 1-based start index (optional) (default to 1)
    count = 100 # int | Number of results (optional) (default to 100)
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # List Users
        api_response = api_instance.list_users_scim_v2_users_get(filter=filter, start_index=start_index, count=count, http_authorization_credentials=http_authorization_credentials)
        print("The response of SCIM20Api->list_users_scim_v2_users_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->list_users_scim_v2_users_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filter** | **str**| SCIM filter expression | [optional]
 **start_index** | **int**| 1-based start index | [optional] [default to 1]
 **count** | **int**| Number of results | [optional] [default to 100]
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**SCIMListResponse**](SCIMListResponse.md)

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

# **replace_user_scim_v2_users_user_id_put**
> SCIMUser replace_user_scim_v2_users_user_id_put(user_id, body_replace_user_scim_v2_users_user_id_put)

Replace User

Replace user (SCIM 2.0 PUT)

Replaces entire user resource.

### Example


```python
import mcp_client
from mcp_client.models.body_replace_user_scim_v2_users_user_id_put import BodyReplaceUserScimV2UsersUserIdPut
from mcp_client.models.scim_user import SCIMUser
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
    api_instance = mcp_client.SCIM20Api(api_client)
    user_id = 'user_id_example' # str |
    body_replace_user_scim_v2_users_user_id_put = mcp_client.BodyReplaceUserScimV2UsersUserIdPut() # BodyReplaceUserScimV2UsersUserIdPut |

    try:
        # Replace User
        api_response = api_instance.replace_user_scim_v2_users_user_id_put(user_id, body_replace_user_scim_v2_users_user_id_put)
        print("The response of SCIM20Api->replace_user_scim_v2_users_user_id_put:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->replace_user_scim_v2_users_user_id_put: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**|  |
 **body_replace_user_scim_v2_users_user_id_put** | [**BodyReplaceUserScimV2UsersUserIdPut**](BodyReplaceUserScimV2UsersUserIdPut.md)|  |

### Return type

[**SCIMUser**](SCIMUser.md)

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

# **update_user_scim_v2_users_user_id_patch**
> SCIMUser update_user_scim_v2_users_user_id_patch(user_id, body_update_user_scim_v2_users_user_id_patch)

Update User

Update user with PATCH operations (SCIM 2.0)

Supports add, remove, replace operations.

Example:
    ```json
    {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "active",
                "value": false
            }
        ]
    }
    ```

### Example


```python
import mcp_client
from mcp_client.models.body_update_user_scim_v2_users_user_id_patch import BodyUpdateUserScimV2UsersUserIdPatch
from mcp_client.models.scim_user import SCIMUser
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
    api_instance = mcp_client.SCIM20Api(api_client)
    user_id = 'user_id_example' # str |
    body_update_user_scim_v2_users_user_id_patch = mcp_client.BodyUpdateUserScimV2UsersUserIdPatch() # BodyUpdateUserScimV2UsersUserIdPatch |

    try:
        # Update User
        api_response = api_instance.update_user_scim_v2_users_user_id_patch(user_id, body_update_user_scim_v2_users_user_id_patch)
        print("The response of SCIM20Api->update_user_scim_v2_users_user_id_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SCIM20Api->update_user_scim_v2_users_user_id_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **user_id** | **str**|  |
 **body_update_user_scim_v2_users_user_id_patch** | [**BodyUpdateUserScimV2UsersUserIdPatch**](BodyUpdateUserScimV2UsersUserIdPatch.md)|  |

### Return type

[**SCIMUser**](SCIMUser.md)

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
