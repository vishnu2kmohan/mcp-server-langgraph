# mcp_server_langgraph_client.McpApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**handle_message_message_post**](McpApi.md#handle_message_message_post) | **POST** /message | Handle Message
[**list_resources_resources_get**](McpApi.md#list_resources_resources_get) | **GET** /resources | List Resources
[**list_tools_tools_get**](McpApi.md#list_tools_tools_get) | **GET** /tools | List Tools
[**root_get**](McpApi.md#root_get) | **GET** / | Root


# **handle_message_message_post**
> object handle_message_message_post()

Handle Message

Handle MCP messages via StreamableHTTP POST

This is the main endpoint for MCP protocol messages.
Supports both regular and streaming responses.

### Example


```python
import mcp_server_langgraph_client
from mcp_server_langgraph_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = mcp_server_langgraph_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with mcp_server_langgraph_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = mcp_server_langgraph_client.McpApi(api_client)

    try:
        # Handle Message
        api_response = api_instance.handle_message_message_post()
        print("The response of McpApi->handle_message_message_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling McpApi->handle_message_message_post: %s\n" % e)
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
> object list_resources_resources_get()

List Resources

List available resources (convenience endpoint)

### Example


```python
import mcp_server_langgraph_client
from mcp_server_langgraph_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = mcp_server_langgraph_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with mcp_server_langgraph_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = mcp_server_langgraph_client.McpApi(api_client)

    try:
        # List Resources
        api_response = api_instance.list_resources_resources_get()
        print("The response of McpApi->list_resources_resources_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling McpApi->list_resources_resources_get: %s\n" % e)
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

# **list_tools_tools_get**
> object list_tools_tools_get()

List Tools

List available tools (convenience endpoint)

### Example


```python
import mcp_server_langgraph_client
from mcp_server_langgraph_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = mcp_server_langgraph_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with mcp_server_langgraph_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = mcp_server_langgraph_client.McpApi(api_client)

    try:
        # List Tools
        api_response = api_instance.list_tools_tools_get()
        print("The response of McpApi->list_tools_tools_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling McpApi->list_tools_tools_get: %s\n" % e)
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

# **root_get**
> object root_get()

Root

Root endpoint with server info

### Example


```python
import mcp_server_langgraph_client
from mcp_server_langgraph_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = mcp_server_langgraph_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with mcp_server_langgraph_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = mcp_server_langgraph_client.McpApi(api_client)

    try:
        # Root
        api_response = api_instance.root_get()
        print("The response of McpApi->root_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling McpApi->root_get: %s\n" % e)
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
