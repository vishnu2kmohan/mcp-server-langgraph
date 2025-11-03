# CreateAPIKeyRequest

Request to create a new API key

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Human-readable name for the API key |
**expires_days** | **int** | Days until expiration (default: 365) | [optional] [default to 365]

## Example

```python
from mcp_client.models.create_api_key_request import CreateAPIKeyRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAPIKeyRequest from a JSON string
create_api_key_request_instance = CreateAPIKeyRequest.from_json(json)
# print the JSON string representation of the object
print(CreateAPIKeyRequest.to_json())

# convert the object into a dict
create_api_key_request_dict = create_api_key_request_instance.to_dict()
# create an instance of CreateAPIKeyRequest from a dict
create_api_key_request_from_dict = CreateAPIKeyRequest.from_dict(create_api_key_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
