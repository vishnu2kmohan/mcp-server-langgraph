# BodyReplaceUserScimV2UsersUserIdPut

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**UserData** | **map[string]interface{}** |  | 
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Methods

### NewBodyReplaceUserScimV2UsersUserIdPut

`func NewBodyReplaceUserScimV2UsersUserIdPut(userData map[string]interface{}, ) *BodyReplaceUserScimV2UsersUserIdPut`

NewBodyReplaceUserScimV2UsersUserIdPut instantiates a new BodyReplaceUserScimV2UsersUserIdPut object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyReplaceUserScimV2UsersUserIdPutWithDefaults

`func NewBodyReplaceUserScimV2UsersUserIdPutWithDefaults() *BodyReplaceUserScimV2UsersUserIdPut`

NewBodyReplaceUserScimV2UsersUserIdPutWithDefaults instantiates a new BodyReplaceUserScimV2UsersUserIdPut object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetUserData

`func (o *BodyReplaceUserScimV2UsersUserIdPut) GetUserData() map[string]interface{}`

GetUserData returns the UserData field if non-nil, zero value otherwise.

### GetUserDataOk

`func (o *BodyReplaceUserScimV2UsersUserIdPut) GetUserDataOk() (*map[string]interface{}, bool)`

GetUserDataOk returns a tuple with the UserData field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserData

`func (o *BodyReplaceUserScimV2UsersUserIdPut) SetUserData(v map[string]interface{})`

SetUserData sets UserData field to given value.


### GetCredentials

`func (o *BodyReplaceUserScimV2UsersUserIdPut) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyReplaceUserScimV2UsersUserIdPut) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyReplaceUserScimV2UsersUserIdPut) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyReplaceUserScimV2UsersUserIdPut) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyReplaceUserScimV2UsersUserIdPut) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyReplaceUserScimV2UsersUserIdPut) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


