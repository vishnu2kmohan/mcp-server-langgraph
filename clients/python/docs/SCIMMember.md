# SCIMMember

SCIM group member

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | 
**ref** | **str** |  | [optional] 
**display** | **str** |  | [optional] 
**type** | **str** |  | [optional] 

## Example

```python
from mcp_client.models.scim_member import SCIMMember

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMMember from a JSON string
scim_member_instance = SCIMMember.from_json(json)
# print the JSON string representation of the object
print(SCIMMember.to_json())

# convert the object into a dict
scim_member_dict = scim_member_instance.to_dict()
# create an instance of SCIMMember from a dict
scim_member_from_dict = SCIMMember.from_dict(scim_member_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


