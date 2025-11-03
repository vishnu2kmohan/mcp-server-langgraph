# SCIMPatchOperation

SCIM PATCH operation

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**op** | [**SCIMPatchOp**](SCIMPatchOp.md) |  | 
**path** | **str** |  | [optional] 
**value** | **object** |  | [optional] 

## Example

```python
from mcp_client.models.scim_patch_operation import SCIMPatchOperation

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMPatchOperation from a JSON string
scim_patch_operation_instance = SCIMPatchOperation.from_json(json)
# print the JSON string representation of the object
print(SCIMPatchOperation.to_json())

# convert the object into a dict
scim_patch_operation_dict = scim_patch_operation_instance.to_dict()
# create an instance of SCIMPatchOperation from a dict
scim_patch_operation_from_dict = SCIMPatchOperation.from_dict(scim_patch_operation_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


