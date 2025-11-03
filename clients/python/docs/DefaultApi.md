# mcp_client.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**handle_message_message_post**](DefaultApi.md#handle_message_message_post) | **POST** /message | Handle Message
[**list_resources_resources_get**](DefaultApi.md#list_resources_resources_get) | **GET** /resources | List Resources
[**list_tools_tools_get**](DefaultApi.md#list_tools_tools_get) | **GET** /tools | List Tools
[**root_get**](DefaultApi.md#root_get) | **GET** / | Root


# **handle_message_message_post**
> object handle_message_message_post()

Handle Message

Handle MCP messages via StreamableHTTP POST

This is the main endpoint for MCP protocol messages.
Supports both regular and streaming responses.

### Example


```python
import mcp_client
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
    api_instance = mcp_client.DefaultApi(api_client)

    try:
        # Handle Message
        api_response = api_instance.handle_message_message_post()
        print("The response of DefaultApi->handle_message_message_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->handle_message_message_post: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_resources_resources_get**
> Dict[str, object] list_resources_resources_get()

List Resources

List available resources (convenience endpoint)

### Example


```python
import mcp_client
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
    api_instance = mcp_client.DefaultApi(api_client)

    try:
        # List Resources
        api_response = api_instance.list_resources_resources_get()
        print("The response of DefaultApi->list_resources_resources_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->list_resources_resources_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_tools_tools_get**
> Dict[str, object] list_tools_tools_get()

List Tools

List available tools (convenience endpoint)

### Example


```python
import mcp_client
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
    api_instance = mcp_client.DefaultApi(api_client)

    try:
        # List Tools
        api_response = api_instance.list_tools_tools_get()
        print("The response of DefaultApi->list_tools_tools_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->list_tools_tools_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **root_get**
> Dict[str, object] root_get()

Root

Root endpoint with server info

### Example


```python
import mcp_client
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
    api_instance = mcp_client.DefaultApi(api_client)

    try:
        # Root
        api_response = api_instance.root_get()
        print("The response of DefaultApi->root_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->root_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**Dict[str, object]**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**401** | Unauthorized - Invalid or missing authentication token |  -  |
**403** | Forbidden - Insufficient permissions |  -  |
**429** | Too Many Requests - Rate limit exceeded |  -  |
**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)
