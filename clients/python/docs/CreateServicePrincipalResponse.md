# CreateServicePrincipalResponse

Response when creating service principal (includes secret)

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
**client_secret** | **str** | Client secret (save securely, won&#39;t be shown again) | 
**message** | **str** |  | [optional] [default to 'Service principal created successfully. Save the client_secret securely.']

## Example

```python
from mcp_client.models.create_service_principal_response import CreateServicePrincipalResponse

# TODO update the JSON string below
json = "{}"
# create an instance of CreateServicePrincipalResponse from a JSON string
create_service_principal_response_instance = CreateServicePrincipalResponse.from_json(json)
# print the JSON string representation of the object
print(CreateServicePrincipalResponse.to_json())

# convert the object into a dict
create_service_principal_response_dict = create_service_principal_response_instance.to_dict()
# create an instance of CreateServicePrincipalResponse from a dict
create_service_principal_response_from_dict = CreateServicePrincipalResponse.from_dict(create_service_principal_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


