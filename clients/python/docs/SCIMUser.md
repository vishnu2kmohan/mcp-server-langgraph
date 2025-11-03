# SCIMUser

SCIM 2.0 User Resource  Core schema with optional Enterprise extension.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemas** | **List[Optional[str]]** |  | [optional] [default to [urn:ietf:params:scim:schemas:core:2.0:User]]
**id** | **str** |  | [optional] 
**external_id** | **str** |  | [optional] 
**user_name** | **str** |  | 
**name** | [**SCIMName**](SCIMName.md) |  | [optional] 
**display_name** | **str** |  | [optional] 
**nick_name** | **str** |  | [optional] 
**profile_url** | **str** |  | [optional] 
**title** | **str** |  | [optional] 
**user_type** | **str** |  | [optional] 
**preferred_language** | **str** |  | [optional] 
**locale** | **str** |  | [optional] 
**timezone** | **str** |  | [optional] 
**active** | **bool** |  | [optional] [default to True]
**password** | **str** |  | [optional] 
**emails** | [**List[SCIMEmail]**](SCIMEmail.md) |  | [optional] [default to []]
**phone_numbers** | [**List[SCIMPhoneNumber]**](SCIMPhoneNumber.md) |  | [optional] [default to []]
**addresses** | [**List[SCIMAddress]**](SCIMAddress.md) |  | [optional] [default to []]
**groups** | [**List[SCIMGroupMembership]**](SCIMGroupMembership.md) |  | [optional] [default to []]
**meta** | **Dict[str, object]** |  | [optional] 
**urn_ietf_params_scim_schemas_extension_enterprise_2_0_user** | [**SCIMEnterpriseUser**](SCIMEnterpriseUser.md) |  | [optional] 

## Example

```python
from mcp_client.models.scim_user import SCIMUser

# TODO update the JSON string below
json = "{}"
# create an instance of SCIMUser from a JSON string
scim_user_instance = SCIMUser.from_json(json)
# print the JSON string representation of the object
print(SCIMUser.to_json())

# convert the object into a dict
scim_user_dict = scim_user_instance.to_dict()
# create an instance of SCIMUser from a dict
scim_user_from_dict = SCIMUser.from_dict(scim_user_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


