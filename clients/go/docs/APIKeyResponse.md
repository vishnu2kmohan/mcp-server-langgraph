# APIKeyResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**KeyId** | **string** |  |
**Name** | **string** |  |
**Created** | **string** |  |
**ExpiresAt** | **string** |  |
**LastUsed** | Pointer to **NullableString** |  | [optional]

## Methods

### NewAPIKeyResponse

`func NewAPIKeyResponse(keyId string, name string, created string, expiresAt string, ) *APIKeyResponse`

NewAPIKeyResponse instantiates a new APIKeyResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewAPIKeyResponseWithDefaults

`func NewAPIKeyResponseWithDefaults() *APIKeyResponse`

NewAPIKeyResponseWithDefaults instantiates a new APIKeyResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetKeyId

`func (o *APIKeyResponse) GetKeyId() string`

GetKeyId returns the KeyId field if non-nil, zero value otherwise.

### GetKeyIdOk

`func (o *APIKeyResponse) GetKeyIdOk() (*string, bool)`

GetKeyIdOk returns a tuple with the KeyId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetKeyId

`func (o *APIKeyResponse) SetKeyId(v string)`

SetKeyId sets KeyId field to given value.


### GetName

`func (o *APIKeyResponse) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *APIKeyResponse) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *APIKeyResponse) SetName(v string)`

SetName sets Name field to given value.


### GetCreated

`func (o *APIKeyResponse) GetCreated() string`

GetCreated returns the Created field if non-nil, zero value otherwise.

### GetCreatedOk

`func (o *APIKeyResponse) GetCreatedOk() (*string, bool)`

GetCreatedOk returns a tuple with the Created field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreated

`func (o *APIKeyResponse) SetCreated(v string)`

SetCreated sets Created field to given value.


### GetExpiresAt

`func (o *APIKeyResponse) GetExpiresAt() string`

GetExpiresAt returns the ExpiresAt field if non-nil, zero value otherwise.

### GetExpiresAtOk

`func (o *APIKeyResponse) GetExpiresAtOk() (*string, bool)`

GetExpiresAtOk returns a tuple with the ExpiresAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExpiresAt

`func (o *APIKeyResponse) SetExpiresAt(v string)`

SetExpiresAt sets ExpiresAt field to given value.


### GetLastUsed

`func (o *APIKeyResponse) GetLastUsed() string`

GetLastUsed returns the LastUsed field if non-nil, zero value otherwise.

### GetLastUsedOk

`func (o *APIKeyResponse) GetLastUsedOk() (*string, bool)`

GetLastUsedOk returns a tuple with the LastUsed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastUsed

`func (o *APIKeyResponse) SetLastUsed(v string)`

SetLastUsed sets LastUsed field to given value.

### HasLastUsed

`func (o *APIKeyResponse) HasLastUsed() bool`

HasLastUsed returns a boolean if a field has been set.

### SetLastUsedNil

`func (o *APIKeyResponse) SetLastUsedNil(b bool)`

 SetLastUsedNil sets the value for LastUsed to be an explicit nil

### UnsetLastUsed
`func (o *APIKeyResponse) UnsetLastUsed()`

UnsetLastUsed ensures that no value is present for LastUsed, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
