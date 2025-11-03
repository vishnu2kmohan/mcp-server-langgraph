# GDPRComplianceApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**deleteUserAccountApiV1UsersMeDelete**](#deleteuseraccountapiv1usersmedelete) | **DELETE** /api/v1/users/me | Delete User Account|
|[**exportUserDataApiV1UsersMeExportGet**](#exportuserdataapiv1usersmeexportget) | **GET** /api/v1/users/me/export | Export User Data|
|[**getConsentStatusApiV1UsersMeConsentGet**](#getconsentstatusapiv1usersmeconsentget) | **GET** /api/v1/users/me/consent | Get Consent Status|
|[**getUserDataApiV1UsersMeDataGet**](#getuserdataapiv1usersmedataget) | **GET** /api/v1/users/me/data | Get User Data|
|[**updateConsentApiV1UsersMeConsentPost**](#updateconsentapiv1usersmeconsentpost) | **POST** /api/v1/users/me/consent | Update Consent|
|[**updateUserProfileApiV1UsersMePatch**](#updateuserprofileapiv1usersmepatch) | **PATCH** /api/v1/users/me | Update User Profile|

# **deleteUserAccountApiV1UsersMeDelete**
> { [key: string]: any; } deleteUserAccountApiV1UsersMeDelete()

Delete user account and all data (GDPR Article 17 - Right to Erasure)  **WARNING**: This is an irreversible operation that permanently deletes all user data.  **GDPR Article 17**: The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay.  **Query Parameters**: - `confirm`: Must be set to `true` to confirm deletion  **What gets deleted**: - User profile and account - All sessions - All conversations and messages - All preferences and settings - All authorization tuples  **What gets anonymized** (retained for compliance): - Audit logs (user_id replaced with hash)  **Response**: Deletion result with details

### Example

```typescript
import {
    GDPRComplianceApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new GDPRComplianceApi(configuration);

let confirm: boolean; //Must be true to confirm account deletion (default to undefined)
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.deleteUserAccountApiV1UsersMeDelete(
    confirm,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **confirm** | [**boolean**] | Must be true to confirm account deletion | defaults to undefined|


### Return type

**{ [key: string]: any; }**

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

# **exportUserDataApiV1UsersMeExportGet**
> any exportUserDataApiV1UsersMeExportGet()

Export user data in portable format (GDPR Article 20 - Right to Data Portability)  **GDPR Article 20**: The data subject shall have the right to receive the personal data concerning him or her in a structured, commonly used and machine-readable format.  **Query Parameters**: - `format`: Export format (json or csv)  **Response**: File download in requested format

### Example

```typescript
import {
    GDPRComplianceApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new GDPRComplianceApi(configuration);

let format: string; //Export format: json or csv (optional) (default to 'json')
let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.exportUserDataApiV1UsersMeExportGet(
    format,
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |
| **format** | [**string**] | Export format: json or csv | (optional) defaults to 'json'|


### Return type

**any**

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

# **getConsentStatusApiV1UsersMeConsentGet**
> ConsentResponse getConsentStatusApiV1UsersMeConsentGet()

Get current consent status (GDPR Article 21 - Right to Object)  Returns all consent preferences for the authenticated user.  **Response**: Current consent status for all consent types

### Example

```typescript
import {
    GDPRComplianceApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new GDPRComplianceApi(configuration);

let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.getConsentStatusApiV1UsersMeConsentGet(
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |


### Return type

**ConsentResponse**

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

# **getUserDataApiV1UsersMeDataGet**
> UserDataExport getUserDataApiV1UsersMeDataGet()

Export all user data (GDPR Article 15 - Right to Access)  Returns all personal data associated with the authenticated user.  **GDPR Article 15**: The data subject shall have the right to obtain from the controller confirmation as to whether or not personal data concerning him or her are being processed, and access to the personal data.  **Response**: Complete JSON export of all user data including: - User profile - Sessions - Conversations - Preferences - Audit log - Consents

### Example

```typescript
import {
    GDPRComplianceApi,
    Configuration,
    HTTPAuthorizationCredentials
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new GDPRComplianceApi(configuration);

let hTTPAuthorizationCredentials: HTTPAuthorizationCredentials; // (optional)

const { status, data } = await apiInstance.getUserDataApiV1UsersMeDataGet(
    hTTPAuthorizationCredentials
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **hTTPAuthorizationCredentials** | **HTTPAuthorizationCredentials**|  | |


### Return type

**UserDataExport**

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

# **updateConsentApiV1UsersMeConsentPost**
> ConsentResponse updateConsentApiV1UsersMeConsentPost(bodyUpdateConsentApiV1UsersMeConsentPost)

Update user consent preferences (GDPR Article 21 - Right to Object)  **GDPR Article 21**: The data subject shall have the right to object at any time to processing of personal data concerning him or her.  **Request Body**: Consent type and whether it\'s granted  **Response**: Current consent status for all types

### Example

```typescript
import {
    GDPRComplianceApi,
    Configuration,
    BodyUpdateConsentApiV1UsersMeConsentPost
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new GDPRComplianceApi(configuration);

let bodyUpdateConsentApiV1UsersMeConsentPost: BodyUpdateConsentApiV1UsersMeConsentPost; //

const { status, data } = await apiInstance.updateConsentApiV1UsersMeConsentPost(
    bodyUpdateConsentApiV1UsersMeConsentPost
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyUpdateConsentApiV1UsersMeConsentPost** | **BodyUpdateConsentApiV1UsersMeConsentPost**|  | |


### Return type

**ConsentResponse**

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

# **updateUserProfileApiV1UsersMePatch**
> { [key: string]: any; } updateUserProfileApiV1UsersMePatch(bodyUpdateUserProfileApiV1UsersMePatch)

Update user profile (GDPR Article 16 - Right to Rectification)  **GDPR Article 16**: The data subject shall have the right to obtain from the controller without undue delay the rectification of inaccurate personal data concerning him or her.  **Request Body**: Profile fields to update (only provided fields are updated)  **Response**: Updated user profile

### Example

```typescript
import {
    GDPRComplianceApi,
    Configuration,
    BodyUpdateUserProfileApiV1UsersMePatch
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new GDPRComplianceApi(configuration);

let bodyUpdateUserProfileApiV1UsersMePatch: BodyUpdateUserProfileApiV1UsersMePatch; //

const { status, data } = await apiInstance.updateUserProfileApiV1UsersMePatch(
    bodyUpdateUserProfileApiV1UsersMePatch
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **bodyUpdateUserProfileApiV1UsersMePatch** | **BodyUpdateUserProfileApiV1UsersMePatch**|  | |


### Return type

**{ [key: string]: any; }**

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

