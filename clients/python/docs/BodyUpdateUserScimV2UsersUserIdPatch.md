# BodyUpdateUserScimV2UsersUserIdPatch


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**patch_request** | [**SCIMPatchRequest**](SCIMPatchRequest.md) |  |
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Example

```python
from mcp_client.models.body_update_user_scim_v2_users_user_id_patch import BodyUpdateUserScimV2UsersUserIdPatch

# TODO update the JSON string below
json = "{}"
# create an instance of BodyUpdateUserScimV2UsersUserIdPatch from a JSON string
body_update_user_scim_v2_users_user_id_patch_instance = BodyUpdateUserScimV2UsersUserIdPatch.from_json(json)
# print the JSON string representation of the object
print(BodyUpdateUserScimV2UsersUserIdPatch.to_json())

# convert the object into a dict
body_update_user_scim_v2_users_user_id_patch_dict = body_update_user_scim_v2_users_user_id_patch_instance.to_dict()
# create an instance of BodyUpdateUserScimV2UsersUserIdPatch from a dict
body_update_user_scim_v2_users_user_id_patch_from_dict = BodyUpdateUserScimV2UsersUserIdPatch.from_dict(body_update_user_scim_v2_users_user_id_patch_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
