# SCIMAddress

SCIM address

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**formatted** | **str** |  | [optional] 
**street_address** | **str** |  | [optional] 
**locality** | **str** |  | [optional] 
**region** | **str** |  | [optional] 
**postal_code** | **str** |  | [optional] 
**country** | **str** |  | [optional] 
**type** | **str** |  | [optional] 
**primary** | **bool** |  | [optional] [default to False]

## Example

```python
from mcp_client.models.scim_address import SCIMAddress

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMAddress from a JSON string
scim_address_instance = SCIMAddress.from_json(json)
# print the JSON string representation of the object
print(SCIMAddress.to_json())

# convert the object into a dict
scim_address_dict = scim_address_instance.to_dict()
# create an instance of SCIMAddress from a dict
scim_address_from_dict = SCIMAddress.from_dict(scim_address_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


