# CreateServicePrincipalRequest

Request to create a new service principal

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Human-readable name for the service |
**description** | **str** | Purpose/description of the service |
**authentication_mode** | **str** | Authentication mode: &#39;client_credentials&#39; or &#39;service_account_user&#39; | [optional] [default to 'client_credentials']
**associated_user_id** | **str** |  | [optional]
**inherit_permissions** | **bool** | Whether to inherit permissions from associated user | [optional] [default to False]

## Example

```python
from mcp_client.models.create_service_principal_request import CreateServicePrincipalRequest

# TODO update the JSON string below
json = "{}"
# create an instance of CreateServicePrincipalRequest from a JSON string
create_service_principal_request_instance = CreateServicePrincipalRequest.from_json(json)
# print the JSON string representation of the object
print(CreateServicePrincipalRequest.to_json())

# convert the object into a dict
create_service_principal_request_dict = create_service_principal_request_instance.to_dict()
# create an instance of CreateServicePrincipalRequest from a dict
create_service_principal_request_from_dict = CreateServicePrincipalRequest.from_dict(create_service_principal_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
