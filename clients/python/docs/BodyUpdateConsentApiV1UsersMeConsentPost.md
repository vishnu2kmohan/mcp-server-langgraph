# BodyUpdateConsentApiV1UsersMeConsentPost


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**consent** | [**ConsentRecord**](ConsentRecord.md) |  |
**credentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Example

```python
from mcp_client.models.body_update_consent_api_v1_users_me_consent_post import BodyUpdateConsentApiV1UsersMeConsentPost

# TODO update the JSON string below
json = "{}"
# create an instance of BodyUpdateConsentApiV1UsersMeConsentPost from a JSON string
body_update_consent_api_v1_users_me_consent_post_instance = BodyUpdateConsentApiV1UsersMeConsentPost.from_json(json)
# print the JSON string representation of the object
print(BodyUpdateConsentApiV1UsersMeConsentPost.to_json())

# convert the object into a dict
body_update_consent_api_v1_users_me_consent_post_dict = body_update_consent_api_v1_users_me_consent_post_instance.to_dict()
# create an instance of BodyUpdateConsentApiV1UsersMeConsentPost from a dict
body_update_consent_api_v1_users_me_consent_post_from_dict = BodyUpdateConsentApiV1UsersMeConsentPost.from_dict(body_update_consent_api_v1_users_me_consent_post_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
