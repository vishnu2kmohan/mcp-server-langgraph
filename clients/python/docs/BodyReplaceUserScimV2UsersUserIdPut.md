# BodyReplaceUserScimV2UsersUserIdPut


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_data** | **Dict[str, object]** |  |
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Example

```python
from mcp_client.models.body_replace_user_scim_v2_users_user_id_put import BodyReplaceUserScimV2UsersUserIdPut

# TODO update the JSON string below
json = "{}"
# create an instance of BodyReplaceUserScimV2UsersUserIdPut from a JSON string
body_replace_user_scim_v2_users_user_id_put_instance = BodyReplaceUserScimV2UsersUserIdPut.from_json(json)
# print the JSON string representation of the object
print(BodyReplaceUserScimV2UsersUserIdPut.to_json())

# convert the object into a dict
body_replace_user_scim_v2_users_user_id_put_dict = body_replace_user_scim_v2_users_user_id_put_instance.to_dict()
# create an instance of BodyReplaceUserScimV2UsersUserIdPut from a dict
body_replace_user_scim_v2_users_user_id_put_from_dict = BodyReplaceUserScimV2UsersUserIdPut.from_dict(body_replace_user_scim_v2_users_user_id_put_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
