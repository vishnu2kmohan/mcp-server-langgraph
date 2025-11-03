# BodyCreateServicePrincipalApiV1ServicePrincipalsPost


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**request** | [**CreateServicePrincipalRequest**](CreateServicePrincipalRequest.md) |  | 
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Example

```python
from mcp_client.models.body_create_service_principal_api_v1_service_principals_post import BodyCreateServicePrincipalApiV1ServicePrincipalsPost

# TODO update the JSON string below
json = "{}"
# create an instance of BodyCreateServicePrincipalApiV1ServicePrincipalsPost from a JSON string
body_create_service_principal_api_v1_service_principals_post_instance = BodyCreateServicePrincipalApiV1ServicePrincipalsPost.from_json(json)
# print the JSON string representation of the object
print(BodyCreateServicePrincipalApiV1ServicePrincipalsPost.to_json())

# convert the object into a dict
body_create_service_principal_api_v1_service_principals_post_dict = body_create_service_principal_api_v1_service_principals_post_instance.to_dict()
# create an instance of BodyCreateServicePrincipalApiV1ServicePrincipalsPost from a dict
body_create_service_principal_api_v1_service_principals_post_from_dict = BodyCreateServicePrincipalApiV1ServicePrincipalsPost.from_dict(body_create_service_principal_api_v1_service_principals_post_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


