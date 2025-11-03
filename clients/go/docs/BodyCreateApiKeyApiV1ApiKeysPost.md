# BodyCreateApiKeyApiV1ApiKeysPost

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Request** | [**CreateAPIKeyRequest**](CreateAPIKeyRequest.md) |  |
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional]

## Methods

### NewBodyCreateApiKeyApiV1ApiKeysPost

`func NewBodyCreateApiKeyApiV1ApiKeysPost(request CreateAPIKeyRequest, ) *BodyCreateApiKeyApiV1ApiKeysPost`

NewBodyCreateApiKeyApiV1ApiKeysPost instantiates a new BodyCreateApiKeyApiV1ApiKeysPost object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyCreateApiKeyApiV1ApiKeysPostWithDefaults

`func NewBodyCreateApiKeyApiV1ApiKeysPostWithDefaults() *BodyCreateApiKeyApiV1ApiKeysPost`

NewBodyCreateApiKeyApiV1ApiKeysPostWithDefaults instantiates a new BodyCreateApiKeyApiV1ApiKeysPost object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetRequest

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) GetRequest() CreateAPIKeyRequest`

GetRequest returns the Request field if non-nil, zero value otherwise.

### GetRequestOk

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) GetRequestOk() (*CreateAPIKeyRequest, bool)`

GetRequestOk returns a tuple with the Request field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRequest

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) SetRequest(v CreateAPIKeyRequest)`

SetRequest sets Request field to given value.


### GetCredentials

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyCreateApiKeyApiV1ApiKeysPost) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyCreateApiKeyApiV1ApiKeysPost) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
