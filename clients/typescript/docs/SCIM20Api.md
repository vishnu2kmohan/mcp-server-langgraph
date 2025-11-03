# SCIM20Api

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createGroupScimV2GroupsPost**](#creategroupscimv2groupspost) | **POST** /scim/v2/Groups | Create Group|
|[**createUserScimV2UsersPost**](#createuserscimv2userspost) | **POST** /scim/v2/Users | Create User|
|[**deleteUserScimV2UsersUserIdDelete**](#deleteuserscimv2usersuseriddelete) | **DELETE** /scim/v2/Users/{user_id} | Delete User|
|[**getGroupScimV2GroupsGroupIdGet**](#getgroupscimv2groupsgroupidget) | **GET** /scim/v2/Groups/{group_id} | Get Group|
|[**getUserScimV2UsersUserIdGet**](#getuserscimv2usersuseridget) | **GET** /scim/v2/Users/{user_id} | Get User|
|[**listUsersScimV2UsersGet**](#listusersscimv2usersget) | **GET** /scim/v2/Users | List Users|
|[**replaceUserScimV2UsersUserIdPut**](#replaceuserscimv2usersuseridput) | **PUT** /scim/v2/Users/{user_id} | Replace User|
|[**updateUserScimV2UsersUserIdPatch**](#updateuserscimv2usersuseridpatch) | **PATCH** /scim/v2/Users/{user_id} | Update User|

# **createGroupScimV2GroupsPost**
> SCIMGroup createGroupScimV2GroupsPost(bodyCreateGroupScimV2GroupsPost)

Create a new group (SCIM 2.0)  Example:     ```json     {         \"schemas\": [\"urn:ietf:params:scim:schemas:core:2.0:Group\"],         \"displayName\": \"Engineering\",         \"members\": [             {\"value\": \"user-id-123\", \"display\": \"Alice Smith\"}         ]     }     ```

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    BodyCreateGroupScimV2GroupsPost
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let bodyCreateGroupScimV2GroupsPost: BodyCreateGroupScimV2GroupsPost; //

const { status, data } = await apiInstance.createGroupScimV2GroupsPost(
    bodyCreateGroupScimV2GroupsPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyCreateGroupScimV2GroupsPost** | **BodyCreateGroupScimV2GroupsPost**|  | |


### Return type

**SCIMGroup**

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

# **createUserScimV2UsersPost**
> SCIMUser createUserScimV2UsersPost(bodyCreateUserScimV2UsersPost)

Create a new user (SCIM 2.0)  Provisions user in Keycloak and syncs roles to OpenFGA.  Example:     ```json     {         \"schemas\": [\"urn:ietf:params:scim:schemas:core:2.0:User\"],         \"userName\": \"alice@example.com\",         \"name\": {             \"givenName\": \"Alice\",             \"familyName\": \"Smith\"         },         \"emails\": [{             \"value\": \"alice@example.com\",             \"primary\": true         }],         \"active\": true     }     ```

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    BodyCreateUserScimV2UsersPost
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let bodyCreateUserScimV2UsersPost: BodyCreateUserScimV2UsersPost; //

const { status, data } = await apiInstance.createUserScimV2UsersPost(
    bodyCreateUserScimV2UsersPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyCreateUserScimV2UsersPost** | **BodyCreateUserScimV2UsersPost**|  | |


### Return type

**SCIMUser**

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

# **deleteUserScimV2UsersUserIdDelete**
> deleteUserScimV2UsersUserIdDelete()

Delete (deactivate) user (SCIM 2.0)  Deactivates user in Keycloak and removes OpenFGA tuples.

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let userId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.deleteUserScimV2UsersUserIdDelete(
    userId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **userId** | [**string**] |  | defaults to undefined|


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

# **getGroupScimV2GroupsGroupIdGet**
> SCIMGroup getGroupScimV2GroupsGroupIdGet()

Get group by ID (SCIM 2.0)

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let groupId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.getGroupScimV2GroupsGroupIdGet(
    groupId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **groupId** | [**string**] |  | defaults to undefined|


### Return type

**SCIMGroup**

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

# **getUserScimV2UsersUserIdGet**
> SCIMUser getUserScimV2UsersUserIdGet()

Get user by ID (SCIM 2.0)  Returns user in SCIM format.

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let userId: string; // (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.getUserScimV2UsersUserIdGet(
    userId,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **userId** | [**string**] |  | defaults to undefined|


### Return type

**SCIMUser**

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

# **listUsersScimV2UsersGet**
> SCIMListResponse listUsersScimV2UsersGet()

List/search users (SCIM 2.0)  Supports basic filtering (e.g., \'userName eq \"alice@example.com\"\').

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let filter: string; //SCIM filter expression (optional) (default to undefined)
let startIndex: number; //1-based start index (optional) (default to 1)
let count: number; //Number of results (optional) (default to 100)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.listUsersScimV2UsersGet(
    filter,
    startIndex,
    count,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **filter** | [**string**] | SCIM filter expression | (optional) defaults to undefined|
| **startIndex** | [**number**] | 1-based start index | (optional) defaults to 1|
| **count** | [**number**] | Number of results | (optional) defaults to 100|


### Return type

**SCIMListResponse**

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

# **replaceUserScimV2UsersUserIdPut**
> SCIMUser replaceUserScimV2UsersUserIdPut(bodyReplaceUserScimV2UsersUserIdPut)

Replace user (SCIM 2.0 PUT)  Replaces entire user resource.

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    BodyReplaceUserScimV2UsersUserIdPut
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let userId: string; // (default to undefined)
let bodyReplaceUserScimV2UsersUserIdPut: BodyReplaceUserScimV2UsersUserIdPut; //

const { status, data } = await apiInstance.replaceUserScimV2UsersUserIdPut(
    userId,
    bodyReplaceUserScimV2UsersUserIdPut
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyReplaceUserScimV2UsersUserIdPut** | **BodyReplaceUserScimV2UsersUserIdPut**|  | |
| **userId** | [**string**] |  | defaults to undefined|


### Return type

**SCIMUser**

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

# **updateUserScimV2UsersUserIdPatch**
> SCIMUser updateUserScimV2UsersUserIdPatch(bodyUpdateUserScimV2UsersUserIdPatch)

Update user with PATCH operations (SCIM 2.0)  Supports add, remove, replace operations.  Example:     ```json     {         \"schemas\": [\"urn:ietf:params:scim:api:messages:2.0:PatchOp\"],         \"Operations\": [             {                 \"op\": \"replace\",                 \"path\": \"active\",                 \"value\": false             }         ]     }     ```

### Example

```typescript
import {
    SCIM20Api,
    Configuration,
    BodyUpdateUserScimV2UsersUserIdPatch
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new SCIM20Api(configuration);

let userId: string; // (default to undefined)
let bodyUpdateUserScimV2UsersUserIdPatch: BodyUpdateUserScimV2UsersUserIdPatch; //

const { status, data } = await apiInstance.updateUserScimV2UsersUserIdPatch(
    userId,
    bodyUpdateUserScimV2UsersUserIdPatch
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyUpdateUserScimV2UsersUserIdPatch** | **BodyUpdateUserScimV2UsersUserIdPatch**|  | |
| **userId** | [**string**] |  | defaults to undefined|


### Return type

**SCIMUser**

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
