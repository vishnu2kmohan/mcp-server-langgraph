# SCIMPatchRequest

SCIM PATCH request

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **List[str]** |  | [optional] [default to [urn:ietf:params:scim:api:messages:2.0:PatchOp]]
**operations** | [**List[SCIMPatchOperation]**](SCIMPatchOperation.md) |  | 

## Example

```python
from mcp_client.models.scim_patch_request import SCIMPatchRequest

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMPatchRequest from a JSON string
scim_patch_request_instance = SCIMPatchRequest.from_json(json)
# print the JSON string representation of the object
print(SCIMPatchRequest.to_json())

# convert the object into a dict
scim_patch_request_dict = scim_patch_request_instance.to_dict()
# create an instance of SCIMPatchRequest from a dict
scim_patch_request_from_dict = SCIMPatchRequest.from_dict(scim_patch_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


