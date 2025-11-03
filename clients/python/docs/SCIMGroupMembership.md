# SCIMGroupMembership

SCIM group membership

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  |
**ref** | **str** |  | [optional]
**display** | **str** |  | [optional]
**type** | **str** |  | [optional]

## Example

```python
from mcp_client.models.scim_group_membership import SCIMGroupMembership

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMGroupMembership from a JSON string
scim_group_membership_instance = SCIMGroupMembership.from_json(json)
# print the JSON string representation of the object
print(SCIMGroupMembership.to_json())

# convert the object into a dict
scim_group_membership_dict = scim_group_membership_instance.to_dict()
# create an instance of SCIMGroupMembership from a dict
scim_group_membership_from_dict = SCIMGroupMembership.from_dict(scim_group_membership_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
