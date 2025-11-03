# ServicePrincipalResponse

Response containing service principal details

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**service_id** | **str** |  | 
**name** | **str** |  | 
**description** | **str** |  | 
**authentication_mode** | **str** |  | 
**associated_user_id** | **str** |  | 
**owner_user_id** | **str** |  | 
**inherit_permissions** | **bool** |  | 
**enabled** | **bool** |  | 
**created_at** | **str** |  | 

## Example

```python
from mcp_client.models.service_principal_response import ServicePrincipalResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ServicePrincipalResponse from a JSON string
service_principal_response_instance = ServicePrincipalResponse.from_json(json)
# print the JSON string representation of the object
print(ServicePrincipalResponse.to_json())

# convert the object into a dict
service_principal_response_dict = service_principal_response_instance.to_dict()
# create an instance of ServicePrincipalResponse from a dict
service_principal_response_from_dict = ServicePrincipalResponse.from_dict(service_principal_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


