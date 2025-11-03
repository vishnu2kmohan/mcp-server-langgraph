# CreateAPIKeyResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**KeyId** | **string** |  |
**Name** | **string** |  |
**Created** | **string** |  |
**ExpiresAt** | **string** |  |
**LastUsed** | Pointer to **NullableString** |  | [optional]
**ApiKey** | **string** | API key (save securely, won&#39;t be shown again) |
**Message** | Pointer to **string** |  | [optional] [default to "API key created successfully. Save it securely - it will not be shown again."]

## Methods

### NewCreateAPIKeyResponse

`func NewCreateAPIKeyResponse(keyId string, name string, created string, expiresAt string, apiKey string, ) *CreateAPIKeyResponse`

NewCreateAPIKeyResponse instantiates a new CreateAPIKeyResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCreateAPIKeyResponseWithDefaults

`func NewCreateAPIKeyResponseWithDefaults() *CreateAPIKeyResponse`

NewCreateAPIKeyResponseWithDefaults instantiates a new CreateAPIKeyResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetKeyId

`func (o *CreateAPIKeyResponse) GetKeyId() string`

GetKeyId returns the KeyId field if non-nil, zero value otherwise.

### GetKeyIdOk

`func (o *CreateAPIKeyResponse) GetKeyIdOk() (*string, bool)`

GetKeyIdOk returns a tuple with the KeyId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetKeyId

`func (o *CreateAPIKeyResponse) SetKeyId(v string)`

SetKeyId sets KeyId field to given value.


### GetName

`func (o *CreateAPIKeyResponse) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *CreateAPIKeyResponse) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *CreateAPIKeyResponse) SetName(v string)`

SetName sets Name field to given value.


### GetCreated

`func (o *CreateAPIKeyResponse) GetCreated() string`

GetCreated returns the Created field if non-nil, zero value otherwise.

### GetCreatedOk

`func (o *CreateAPIKeyResponse) GetCreatedOk() (*string, bool)`

GetCreatedOk returns a tuple with the Created field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreated

`func (o *CreateAPIKeyResponse) SetCreated(v string)`

SetCreated sets Created field to given value.


### GetExpiresAt

`func (o *CreateAPIKeyResponse) GetExpiresAt() string`

GetExpiresAt returns the ExpiresAt field if non-nil, zero value otherwise.

### GetExpiresAtOk

`func (o *CreateAPIKeyResponse) GetExpiresAtOk() (*string, bool)`

GetExpiresAtOk returns a tuple with the ExpiresAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExpiresAt

`func (o *CreateAPIKeyResponse) SetExpiresAt(v string)`

SetExpiresAt sets ExpiresAt field to given value.


### GetLastUsed

`func (o *CreateAPIKeyResponse) GetLastUsed() string`

GetLastUsed returns the LastUsed field if non-nil, zero value otherwise.

### GetLastUsedOk

`func (o *CreateAPIKeyResponse) GetLastUsedOk() (*string, bool)`

GetLastUsedOk returns a tuple with the LastUsed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastUsed

`func (o *CreateAPIKeyResponse) SetLastUsed(v string)`

SetLastUsed sets LastUsed field to given value.

### HasLastUsed

`func (o *CreateAPIKeyResponse) HasLastUsed() bool`

HasLastUsed returns a boolean if a field has been set.

### SetLastUsedNil

`func (o *CreateAPIKeyResponse) SetLastUsedNil(b bool)`

 SetLastUsedNil sets the value for LastUsed to be an explicit nil

### UnsetLastUsed
`func (o *CreateAPIKeyResponse) UnsetLastUsed()`

UnsetLastUsed ensures that no value is present for LastUsed, not even an explicit nil
### GetApiKey

`func (o *CreateAPIKeyResponse) GetApiKey() string`

GetApiKey returns the ApiKey field if non-nil, zero value otherwise.

### GetApiKeyOk

`func (o *CreateAPIKeyResponse) GetApiKeyOk() (*string, bool)`

GetApiKeyOk returns a tuple with the ApiKey field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetApiKey

`func (o *CreateAPIKeyResponse) SetApiKey(v string)`

SetApiKey sets ApiKey field to given value.


### GetMessage

`func (o *CreateAPIKeyResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *CreateAPIKeyResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *CreateAPIKeyResponse) SetMessage(v string)`

SetMessage sets Message field to given value.

### HasMessage

`func (o *CreateAPIKeyResponse) HasMessage() bool`

HasMessage returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
