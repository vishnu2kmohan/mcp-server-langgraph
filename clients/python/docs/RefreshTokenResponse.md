# RefreshTokenResponse

Token refresh response

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**access_token** | **str** | New JWT access token | 
**token_type** | **str** | Token type | [optional] [default to 'bearer']
**expires_in** | **int** | Token expiration in seconds | 
**refresh_token** | **str** |  | [optional] 

## Example

```python
from mcp_client.models.refresh_token_response import RefreshTokenResponse

# TODO update the JSON string below
json = "{}"
# create an instance of RefreshTokenResponse from a JSON string
refresh_token_response_instance = RefreshTokenResponse.from_json(json)
# print the JSON string representation of the object
print(RefreshTokenResponse.to_json())

# convert the object into a dict
refresh_token_response_dict = refresh_token_response_instance.to_dict()
# create an instance of RefreshTokenResponse from a dict
refresh_token_response_from_dict = RefreshTokenResponse.from_dict(refresh_token_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


