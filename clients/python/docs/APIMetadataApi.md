# mcp_client.APIMetadataApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_api_version_metadata**](APIMetadataApi.md#get_api_version_metadata) | **GET** /api/version | Get API version information


# **get_api_version_metadata**
> APIVersionInfo get_api_version_metadata()

Get API version information

Returns API version metadata for client compatibility checking.

    **Versioning Strategy:**
    - **Semantic Versioning**: MAJOR.MINOR.PATCH
    - **URL Versioning**: `/api/v1`, `/api/v2`, etc.
    - **Header Negotiation**: `X-API-Version: 1.0` (optional)
    - **Deprecation Policy**: 6-month sunset period for deprecated versions

    **Breaking Changes:**
    - Removing fields from responses
    - Changing field types
    - Removing endpoints
    - Changing authentication methods

    **Non-Breaking Changes:**
    - Adding new endpoints
    - Adding new optional fields to requests
    - Adding new fields to responses
    - Adding new query parameters (optional)

    Use this endpoint to:
    - Check current API version
    - Determine if your client is compatible
    - Find out when deprecated versions will be removed
    - Locate API documentation

### Example


```python
import mcp_client
from mcp_client.models.api_version_info import APIVersionInfo
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
    api_instance = mcp_client.APIMetadataApi(api_client)

    try:
        # Get API version information
        api_response = api_instance.get_api_version_metadata()
        print("The response of APIMetadataApi->get_api_version_metadata:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling APIMetadataApi->get_api_version_metadata: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**APIVersionInfo**](APIVersionInfo.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | API version information |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
