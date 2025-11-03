# BodyUpdateUserProfileApiV1UsersMePatch

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ProfileUpdate** | [**UserProfileUpdate**](UserProfileUpdate.md) |  | 
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Methods

### NewBodyUpdateUserProfileApiV1UsersMePatch

`func NewBodyUpdateUserProfileApiV1UsersMePatch(profileUpdate UserProfileUpdate, ) *BodyUpdateUserProfileApiV1UsersMePatch`

NewBodyUpdateUserProfileApiV1UsersMePatch instantiates a new BodyUpdateUserProfileApiV1UsersMePatch object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyUpdateUserProfileApiV1UsersMePatchWithDefaults

`func NewBodyUpdateUserProfileApiV1UsersMePatchWithDefaults() *BodyUpdateUserProfileApiV1UsersMePatch`

NewBodyUpdateUserProfileApiV1UsersMePatchWithDefaults instantiates a new BodyUpdateUserProfileApiV1UsersMePatch object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProfileUpdate

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) GetProfileUpdate() UserProfileUpdate`

GetProfileUpdate returns the ProfileUpdate field if non-nil, zero value otherwise.

### GetProfileUpdateOk

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) GetProfileUpdateOk() (*UserProfileUpdate, bool)`

GetProfileUpdateOk returns a tuple with the ProfileUpdate field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProfileUpdate

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) SetProfileUpdate(v UserProfileUpdate)`

SetProfileUpdate sets ProfileUpdate field to given value.


### GetCredentials

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyUpdateUserProfileApiV1UsersMePatch) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyUpdateUserProfileApiV1UsersMePatch) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


