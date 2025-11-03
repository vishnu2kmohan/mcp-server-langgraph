# RotateSecretResponse

Response when rotating service principal secret

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**service_id** | **str** |  | 
**client_secret** | **str** | New client secret | 
**message** | **str** |  | [optional] [default to 'Secret rotated successfully. Update your service configuration.']

## Example

```python
from mcp_client.models.rotate_secret_response import RotateSecretResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RotateSecretResponse from a JSON string
rotate_secret_response_instance = RotateSecretResponse.from_json(json)
# print the JSON string representation of the object
print(RotateSecretResponse.to_json())

# convert the object into a dict
rotate_secret_response_dict = rotate_secret_response_instance.to_dict()
# create an instance of RotateSecretResponse from a dict
rotate_secret_response_from_dict = RotateSecretResponse.from_dict(rotate_secret_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


