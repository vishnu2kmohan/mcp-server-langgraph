# CreateAPIKeyResponse

Response when creating API key (includes the key itself)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**key_id** | **str** |  | 
**name** | **str** |  | 
**created** | **str** |  | 
**expires_at** | **str** |  | 
**last_used** | **str** |  | [optional] 
**api_key** | **str** | API key (save securely, won&#39;t be shown again) | 
**message** | **str** |  | [optional] [default to 'API key created successfully. Save it securely - it will not be shown again.']

## Example

```python
from mcp_client.models.create_api_key_response import CreateAPIKeyResponse

# TODO update the JSON string below
json = "{}"
# create an instance of CreateAPIKeyResponse from a JSON string
create_api_key_response_instance = CreateAPIKeyResponse.from_json(json)
# print the JSON string representation of the object
print(CreateAPIKeyResponse.to_json())

# convert the object into a dict
create_api_key_response_dict = create_api_key_response_instance.to_dict()
# create an instance of CreateAPIKeyResponse from a dict
create_api_key_response_from_dict = CreateAPIKeyResponse.from_dict(create_api_key_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


