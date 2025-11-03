# BodyCreateServicePrincipalApiV1ServicePrincipalsPost

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Request** | [**CreateServicePrincipalRequest**](CreateServicePrincipalRequest.md) |  | 
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Methods

### NewBodyCreateServicePrincipalApiV1ServicePrincipalsPost

`func NewBodyCreateServicePrincipalApiV1ServicePrincipalsPost(request CreateServicePrincipalRequest, ) *BodyCreateServicePrincipalApiV1ServicePrincipalsPost`

NewBodyCreateServicePrincipalApiV1ServicePrincipalsPost instantiates a new BodyCreateServicePrincipalApiV1ServicePrincipalsPost object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyCreateServicePrincipalApiV1ServicePrincipalsPostWithDefaults

`func NewBodyCreateServicePrincipalApiV1ServicePrincipalsPostWithDefaults() *BodyCreateServicePrincipalApiV1ServicePrincipalsPost`

NewBodyCreateServicePrincipalApiV1ServicePrincipalsPostWithDefaults instantiates a new BodyCreateServicePrincipalApiV1ServicePrincipalsPost object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetRequest

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) GetRequest() CreateServicePrincipalRequest`

GetRequest returns the Request field if non-nil, zero value otherwise.

### GetRequestOk

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) GetRequestOk() (*CreateServicePrincipalRequest, bool)`

GetRequestOk returns a tuple with the Request field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRequest

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) SetRequest(v CreateServicePrincipalRequest)`

SetRequest sets Request field to given value.


### GetCredentials

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyCreateServicePrincipalApiV1ServicePrincipalsPost) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


