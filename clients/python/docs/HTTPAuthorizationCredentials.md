# HTTPAuthorizationCredentials

The HTTP authorization credentials in the result of using `HTTPBearer` or `HTTPDigest` in a dependency.  The HTTP authorization header value is split by the first space.  The first part is the `scheme`, the second part is the `credentials`.  For example, in an HTTP Bearer token scheme, the client will send a header like:  ``` Authorization: Bearer deadbeef12346 ```  In this case:  * `scheme` will have the value `\"Bearer\"` * `credentials` will have the value `\"deadbeef12346\"`

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**scheme** | **str** |  | 
**credentials** | **str** |  | 

## Example

```python
from mcp_client.models.http_authorization_credentials import HTTPAuthorizationCredentials

# TODO update the JSON string below
json = "{}"
# create an instance of HTTPAuthorizationCredentials from a JSON string
http_authorization_credentials_instance = HTTPAuthorizationCredentials.from_json(json)
# print the JSON string representation of the object
print(HTTPAuthorizationCredentials.to_json())

# convert the object into a dict
http_authorization_credentials_dict = http_authorization_credentials_instance.to_dict()
# create an instance of HTTPAuthorizationCredentials from a dict
http_authorization_credentials_from_dict = HTTPAuthorizationCredentials.from_dict(http_authorization_credentials_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


