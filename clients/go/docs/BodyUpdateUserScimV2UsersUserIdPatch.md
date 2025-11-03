# BodyUpdateUserScimV2UsersUserIdPatch

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**PatchRequest** | [**SCIMPatchRequest**](SCIMPatchRequest.md) |  | 
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Methods

### NewBodyUpdateUserScimV2UsersUserIdPatch

`func NewBodyUpdateUserScimV2UsersUserIdPatch(patchRequest SCIMPatchRequest, ) *BodyUpdateUserScimV2UsersUserIdPatch`

NewBodyUpdateUserScimV2UsersUserIdPatch instantiates a new BodyUpdateUserScimV2UsersUserIdPatch object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyUpdateUserScimV2UsersUserIdPatchWithDefaults

`func NewBodyUpdateUserScimV2UsersUserIdPatchWithDefaults() *BodyUpdateUserScimV2UsersUserIdPatch`

NewBodyUpdateUserScimV2UsersUserIdPatchWithDefaults instantiates a new BodyUpdateUserScimV2UsersUserIdPatch object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetPatchRequest

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) GetPatchRequest() SCIMPatchRequest`

GetPatchRequest returns the PatchRequest field if non-nil, zero value otherwise.

### GetPatchRequestOk

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) GetPatchRequestOk() (*SCIMPatchRequest, bool)`

GetPatchRequestOk returns a tuple with the PatchRequest field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPatchRequest

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) SetPatchRequest(v SCIMPatchRequest)`

SetPatchRequest sets PatchRequest field to given value.


### GetCredentials

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyUpdateUserScimV2UsersUserIdPatch) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyUpdateUserScimV2UsersUserIdPatch) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


