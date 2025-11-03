# mcp_client.GDPRComplianceApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**delete_user_account_api_v1_users_me_delete**](GDPRComplianceApi.md#delete_user_account_api_v1_users_me_delete) | **DELETE** /api/v1/users/me | Delete User Account
[**export_user_data_api_v1_users_me_export_get**](GDPRComplianceApi.md#export_user_data_api_v1_users_me_export_get) | **GET** /api/v1/users/me/export | Export User Data
[**get_consent_status_api_v1_users_me_consent_get**](GDPRComplianceApi.md#get_consent_status_api_v1_users_me_consent_get) | **GET** /api/v1/users/me/consent | Get Consent Status
[**get_user_data_api_v1_users_me_data_get**](GDPRComplianceApi.md#get_user_data_api_v1_users_me_data_get) | **GET** /api/v1/users/me/data | Get User Data
[**update_consent_api_v1_users_me_consent_post**](GDPRComplianceApi.md#update_consent_api_v1_users_me_consent_post) | **POST** /api/v1/users/me/consent | Update Consent
[**update_user_profile_api_v1_users_me_patch**](GDPRComplianceApi.md#update_user_profile_api_v1_users_me_patch) | **PATCH** /api/v1/users/me | Update User Profile


# **delete_user_account_api_v1_users_me_delete**
> Dict[str, object] delete_user_account_api_v1_users_me_delete(confirm, http_authorization_credentials=http_authorization_credentials)

Delete User Account

Delete user account and all data (GDPR Article 17 - Right to Erasure)

**WARNING**: This is an irreversible operation that permanently deletes all user data.

**GDPR Article 17**: The data subject shall have the right to obtain from the
controller the erasure of personal data concerning him or her without undue delay.

**Query Parameters**:
- `confirm`: Must be set to `true` to confirm deletion

**What gets deleted**:
- User profile and account
- All sessions
- All conversations and messages
- All preferences and settings
- All authorization tuples

**What gets anonymized** (retained for compliance):
- Audit logs (user_id replaced with hash)

**Response**: Deletion result with details

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
    api_instance = mcp_client.GDPRComplianceApi(api_client)
    confirm = True # bool | Must be true to confirm account deletion
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Delete User Account
        api_response = api_instance.delete_user_account_api_v1_users_me_delete(confirm, http_authorization_credentials=http_authorization_credentials)
        print("The response of GDPRComplianceApi->delete_user_account_api_v1_users_me_delete:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GDPRComplianceApi->delete_user_account_api_v1_users_me_delete: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **confirm** | **bool**| Must be true to confirm account deletion |
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

**Dict[str, object]**

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

# **export_user_data_api_v1_users_me_export_get**
> object export_user_data_api_v1_users_me_export_get(format=format, http_authorization_credentials=http_authorization_credentials)

Export User Data

Export user data in portable format (GDPR Article 20 - Right to Data Portability)

**GDPR Article 20**: The data subject shall have the right to receive the personal
data concerning him or her in a structured, commonly used and machine-readable format.

**Query Parameters**:
- `format`: Export format (json or csv)

**Response**: File download in requested format

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
    api_instance = mcp_client.GDPRComplianceApi(api_client)
    format = 'json' # str | Export format: json or csv (optional) (default to 'json')
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Export User Data
        api_response = api_instance.export_user_data_api_v1_users_me_export_get(format=format, http_authorization_credentials=http_authorization_credentials)
        print("The response of GDPRComplianceApi->export_user_data_api_v1_users_me_export_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GDPRComplianceApi->export_user_data_api_v1_users_me_export_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **format** | **str**| Export format: json or csv | [optional] [default to &#39;json&#39;]
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

**object**

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

# **get_consent_status_api_v1_users_me_consent_get**
> ConsentResponse get_consent_status_api_v1_users_me_consent_get(http_authorization_credentials=http_authorization_credentials)

Get Consent Status

Get current consent status (GDPR Article 21 - Right to Object)

Returns all consent preferences for the authenticated user.

**Response**: Current consent status for all consent types

### Example


```python
import mcp_client
from mcp_client.models.consent_response import ConsentResponse
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
    api_instance = mcp_client.GDPRComplianceApi(api_client)
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Get Consent Status
        api_response = api_instance.get_consent_status_api_v1_users_me_consent_get(http_authorization_credentials=http_authorization_credentials)
        print("The response of GDPRComplianceApi->get_consent_status_api_v1_users_me_consent_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GDPRComplianceApi->get_consent_status_api_v1_users_me_consent_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**ConsentResponse**](ConsentResponse.md)

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

# **get_user_data_api_v1_users_me_data_get**
> UserDataExport get_user_data_api_v1_users_me_data_get(http_authorization_credentials=http_authorization_credentials)

Get User Data

Export all user data (GDPR Article 15 - Right to Access)

Returns all personal data associated with the authenticated user.

**GDPR Article 15**: The data subject shall have the right to obtain from the
controller confirmation as to whether or not personal data concerning him or
her are being processed, and access to the personal data.

**Response**: Complete JSON export of all user data including:
- User profile
- Sessions
- Conversations
- Preferences
- Audit log
- Consents

### Example


```python
import mcp_client
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials
from mcp_client.models.user_data_export import UserDataExport
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
    api_instance = mcp_client.GDPRComplianceApi(api_client)
    http_authorization_credentials = mcp_client.HTTPAuthorizationCredentials() # HTTPAuthorizationCredentials |  (optional)

    try:
        # Get User Data
        api_response = api_instance.get_user_data_api_v1_users_me_data_get(http_authorization_credentials=http_authorization_credentials)
        print("The response of GDPRComplianceApi->get_user_data_api_v1_users_me_data_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GDPRComplianceApi->get_user_data_api_v1_users_me_data_get: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **http_authorization_credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md)|  | [optional]

### Return type

[**UserDataExport**](UserDataExport.md)

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

# **update_consent_api_v1_users_me_consent_post**
> ConsentResponse update_consent_api_v1_users_me_consent_post(body_update_consent_api_v1_users_me_consent_post)

Update Consent

Update user consent preferences (GDPR Article 21 - Right to Object)

**GDPR Article 21**: The data subject shall have the right to object at any time
to processing of personal data concerning him or her.

**Request Body**: Consent type and whether it's granted

**Response**: Current consent status for all types

### Example


```python
import mcp_client
from mcp_client.models.body_update_consent_api_v1_users_me_consent_post import BodyUpdateConsentApiV1UsersMeConsentPost
from mcp_client.models.consent_response import ConsentResponse
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
    api_instance = mcp_client.GDPRComplianceApi(api_client)
    body_update_consent_api_v1_users_me_consent_post = mcp_client.BodyUpdateConsentApiV1UsersMeConsentPost() # BodyUpdateConsentApiV1UsersMeConsentPost |

    try:
        # Update Consent
        api_response = api_instance.update_consent_api_v1_users_me_consent_post(body_update_consent_api_v1_users_me_consent_post)
        print("The response of GDPRComplianceApi->update_consent_api_v1_users_me_consent_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GDPRComplianceApi->update_consent_api_v1_users_me_consent_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body_update_consent_api_v1_users_me_consent_post** | [**BodyUpdateConsentApiV1UsersMeConsentPost**](BodyUpdateConsentApiV1UsersMeConsentPost.md)|  |

### Return type

[**ConsentResponse**](ConsentResponse.md)

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

# **update_user_profile_api_v1_users_me_patch**
> Dict[str, object] update_user_profile_api_v1_users_me_patch(body_update_user_profile_api_v1_users_me_patch)

Update User Profile

Update user profile (GDPR Article 16 - Right to Rectification)

**GDPR Article 16**: The data subject shall have the right to obtain from the
controller without undue delay the rectification of inaccurate personal data
concerning him or her.

**Request Body**: Profile fields to update (only provided fields are updated)

**Response**: Updated user profile

### Example


```python
import mcp_client
from mcp_client.models.body_update_user_profile_api_v1_users_me_patch import BodyUpdateUserProfileApiV1UsersMePatch
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
    api_instance = mcp_client.GDPRComplianceApi(api_client)
    body_update_user_profile_api_v1_users_me_patch = mcp_client.BodyUpdateUserProfileApiV1UsersMePatch() # BodyUpdateUserProfileApiV1UsersMePatch |

    try:
        # Update User Profile
        api_response = api_instance.update_user_profile_api_v1_users_me_patch(body_update_user_profile_api_v1_users_me_patch)
        print("The response of GDPRComplianceApi->update_user_profile_api_v1_users_me_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling GDPRComplianceApi->update_user_profile_api_v1_users_me_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body_update_user_profile_api_v1_users_me_patch** | [**BodyUpdateUserProfileApiV1UsersMePatch**](BodyUpdateUserProfileApiV1UsersMePatch.md)|  |

### Return type

**Dict[str, object]**

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
