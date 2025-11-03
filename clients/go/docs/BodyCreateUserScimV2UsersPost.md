# BodyCreateUserScimV2UsersPost

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**UserData** | **map[string]interface{}** |  |
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Methods

### NewBodyCreateUserScimV2UsersPost

`func NewBodyCreateUserScimV2UsersPost(userData map[string]interface{}, ) *BodyCreateUserScimV2UsersPost`

NewBodyCreateUserScimV2UsersPost instantiates a new BodyCreateUserScimV2UsersPost object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyCreateUserScimV2UsersPostWithDefaults

`func NewBodyCreateUserScimV2UsersPostWithDefaults() *BodyCreateUserScimV2UsersPost`

NewBodyCreateUserScimV2UsersPostWithDefaults instantiates a new BodyCreateUserScimV2UsersPost object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetUserData

`func (o *BodyCreateUserScimV2UsersPost) GetUserData() map[string]interface{}`

GetUserData returns the UserData field if non-nil, zero value otherwise.

### GetUserDataOk

`func (o *BodyCreateUserScimV2UsersPost) GetUserDataOk() (*map[string]interface{}, bool)`

GetUserDataOk returns a tuple with the UserData field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserData

`func (o *BodyCreateUserScimV2UsersPost) SetUserData(v map[string]interface{})`

SetUserData sets UserData field to given value.


### GetCredentials

`func (o *BodyCreateUserScimV2UsersPost) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyCreateUserScimV2UsersPost) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyCreateUserScimV2UsersPost) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyCreateUserScimV2UsersPost) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyCreateUserScimV2UsersPost) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyCreateUserScimV2UsersPost) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
