# SCIMName

SCIM user name

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**formatted** | **str** |  | [optional]
**family_name** | **str** |  | [optional]
**given_name** | **str** |  | [optional]
**middle_name** | **str** |  | [optional]
**honorific_prefix** | **str** |  | [optional]
**honorific_suffix** | **str** |  | [optional]

## Example

```python
from mcp_client.models.scim_name import SCIMName

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMName from a JSON string
scim_name_instance = SCIMName.from_json(json)
# print the JSON string representation of the object
print(SCIMName.to_json())

# convert the object into a dict
scim_name_dict = scim_name_instance.to_dict()
# create an instance of SCIMName from a dict
scim_name_from_dict = SCIMName.from_dict(scim_name_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
