# SCIMGroup

SCIM 2.0 Group Resource

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **List[Optional[str]]** |  | [optional] [default to [urn:ietf:params:scim:schemas:core:2.0:Group]]
**id** | **str** |  | [optional]
**display_name** | **str** |  |
**members** | [**List[SCIMMember]**](SCIMMember.md) |  | [optional] [default to []]
**meta** | **Dict[str, object]** |  | [optional]

## Example

```python
from mcp_client.models.scim_group import SCIMGroup

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMGroup from a JSON string
scim_group_instance = SCIMGroup.from_json(json)
# print the JSON string representation of the object
print(SCIMGroup.to_json())

# convert the object into a dict
scim_group_dict = scim_group_instance.to_dict()
# create an instance of SCIMGroup from a dict
scim_group_from_dict = SCIMGroup.from_dict(scim_group_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
