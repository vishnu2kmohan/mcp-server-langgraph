# SCIMEmail

SCIM email address

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**value** | **str** |  |
**type** | **str** |  | [optional]
**primary** | **bool** |  | [optional] [default to False]

## Example

```python
from mcp_client.models.scim_email import SCIMEmail

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMEmail from a JSON string
scim_email_instance = SCIMEmail.from_json(json)
# print the JSON string representation of the object
print(SCIMEmail.to_json())

# convert the object into a dict
scim_email_dict = scim_email_instance.to_dict()
# create an instance of SCIMEmail from a dict
scim_email_from_dict = SCIMEmail.from_dict(scim_email_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
