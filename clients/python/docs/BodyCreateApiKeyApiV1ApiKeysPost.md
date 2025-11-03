# BodyCreateApiKeyApiV1ApiKeysPost


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**request** | [**CreateAPIKeyRequest**](CreateAPIKeyRequest.md) |  |
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Example

```python
from mcp_client.models.body_create_api_key_api_v1_api_keys_post import BodyCreateApiKeyApiV1ApiKeysPost

# TODO update the JSON string below
json = "{}"
# create an instance of BodyCreateApiKeyApiV1ApiKeysPost from a JSON string
body_create_api_key_api_v1_api_keys_post_instance = BodyCreateApiKeyApiV1ApiKeysPost.from_json(json)
# print the JSON string representation of the object
print(BodyCreateApiKeyApiV1ApiKeysPost.to_json())

# convert the object into a dict
body_create_api_key_api_v1_api_keys_post_dict = body_create_api_key_api_v1_api_keys_post_instance.to_dict()
# create an instance of BodyCreateApiKeyApiV1ApiKeysPost from a dict
body_create_api_key_api_v1_api_keys_post_from_dict = BodyCreateApiKeyApiV1ApiKeysPost.from_dict(body_create_api_key_api_v1_api_keys_post_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
