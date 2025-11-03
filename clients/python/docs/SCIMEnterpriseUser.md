# SCIMEnterpriseUser

SCIM Enterprise User Extension (RFC 7643 Section 4.3)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**employee_number** | **str** |  | [optional]
**cost_center** | **str** |  | [optional]
**organization** | **str** |  | [optional]
**division** | **str** |  | [optional]
**department** | **str** |  | [optional]
**manager** | **Dict[str, str]** |  | [optional]

## Example

```python
from mcp_client.models.scim_enterprise_user import SCIMEnterpriseUser

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMEnterpriseUser from a JSON string
scim_enterprise_user_instance = SCIMEnterpriseUser.from_json(json)
# print the JSON string representation of the object
print(SCIMEnterpriseUser.to_json())

# convert the object into a dict
scim_enterprise_user_dict = scim_enterprise_user_instance.to_dict()
# create an instance of SCIMEnterpriseUser from a dict
scim_enterprise_user_from_dict = SCIMEnterpriseUser.from_dict(scim_enterprise_user_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
