# BodyUpdateConsentApiV1UsersMeConsentPost

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Consent** | [**ConsentRecord**](ConsentRecord.md) |  | 
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Methods

### NewBodyUpdateConsentApiV1UsersMeConsentPost

`func NewBodyUpdateConsentApiV1UsersMeConsentPost(consent ConsentRecord, ) *BodyUpdateConsentApiV1UsersMeConsentPost`

NewBodyUpdateConsentApiV1UsersMeConsentPost instantiates a new BodyUpdateConsentApiV1UsersMeConsentPost object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyUpdateConsentApiV1UsersMeConsentPostWithDefaults

`func NewBodyUpdateConsentApiV1UsersMeConsentPostWithDefaults() *BodyUpdateConsentApiV1UsersMeConsentPost`

NewBodyUpdateConsentApiV1UsersMeConsentPostWithDefaults instantiates a new BodyUpdateConsentApiV1UsersMeConsentPost object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetConsent

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) GetConsent() ConsentRecord`

GetConsent returns the Consent field if non-nil, zero value otherwise.

### GetConsentOk

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) GetConsentOk() (*ConsentRecord, bool)`

GetConsentOk returns a tuple with the Consent field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsent

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) SetConsent(v ConsentRecord)`

SetConsent sets Consent field to given value.


### GetCredentials

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyUpdateConsentApiV1UsersMeConsentPost) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


