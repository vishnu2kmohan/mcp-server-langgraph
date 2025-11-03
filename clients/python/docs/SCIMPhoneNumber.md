# SCIMPhoneNumber

SCIM phone number

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  | 
**type** | **str** |  | [optional] 
**primary** | **bool** |  | [optional] [default to False]

## Example

```python
from mcp_client.models.scim_phone_number import SCIMPhoneNumber

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMPhoneNumber from a JSON string
scim_phone_number_instance = SCIMPhoneNumber.from_json(json)
# print the JSON string representation of the object
print(SCIMPhoneNumber.to_json())

# convert the object into a dict
scim_phone_number_dict = scim_phone_number_instance.to_dict()
# create an instance of SCIMPhoneNumber from a dict
scim_phone_number_from_dict = SCIMPhoneNumber.from_dict(scim_phone_number_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


