# APIMetadataApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getApiVersionMetadata**](#getapiversionmetadata) | **GET** /api/version | Get API version information|

# **getApiVersionMetadata**
> APIVersionInfo getApiVersionMetadata()

Returns API version metadata for client compatibility checking.      **Versioning Strategy:**     - **Semantic Versioning**: MAJOR.MINOR.PATCH     - **URL Versioning**: `/api/v1`, `/api/v2`, etc.     - **Header Negotiation**: `X-API-Version: 1.0` (optional)     - **Deprecation Policy**: 6-month sunset period for deprecated versions      **Breaking Changes:**     - Removing fields from responses     - Changing field types     - Removing endpoints     - Changing authentication methods      **Non-Breaking Changes:**     - Adding new endpoints     - Adding new optional fields to requests     - Adding new fields to responses     - Adding new query parameters (optional)      Use this endpoint to:     - Check current API version     - Determine if your client is compatible     - Find out when deprecated versions will be removed     - Locate API documentation

### Example

```typescript
import {
    APIMetadataApi,
    Configuration
} from 'mcp-client';

const configuration = new Configuration();
const apiInstance = new APIMetadataApi(configuration);

const { status, data } = await apiInstance.getApiVersionMetadata();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**APIVersionInfo**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | API version information |  -  |
|**401** | Unauthorized - Invalid or missing authentication token |  -  |
|**403** | Forbidden - Insufficient permissions |  -  |
|**429** | Too Many Requests - Rate limit exceeded |  -  |
|**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

