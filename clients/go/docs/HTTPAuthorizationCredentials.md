# HTTPAuthorizationCredentials

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Scheme** | **string** |  |
**Credentials** | **string** |  |

## Methods

### NewHTTPAuthorizationCredentials

`func NewHTTPAuthorizationCredentials(scheme string, credentials string, ) *HTTPAuthorizationCredentials`

NewHTTPAuthorizationCredentials instantiates a new HTTPAuthorizationCredentials object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewHTTPAuthorizationCredentialsWithDefaults

`func NewHTTPAuthorizationCredentialsWithDefaults() *HTTPAuthorizationCredentials`

NewHTTPAuthorizationCredentialsWithDefaults instantiates a new HTTPAuthorizationCredentials object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetScheme

`func (o *HTTPAuthorizationCredentials) GetScheme() string`

GetScheme returns the Scheme field if non-nil, zero value otherwise.

### GetSchemeOk

`func (o *HTTPAuthorizationCredentials) GetSchemeOk() (*string, bool)`

GetSchemeOk returns a tuple with the Scheme field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScheme

`func (o *HTTPAuthorizationCredentials) SetScheme(v string)`

SetScheme sets Scheme field to given value.


### GetCredentials

`func (o *HTTPAuthorizationCredentials) GetCredentials() string`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *HTTPAuthorizationCredentials) GetCredentialsOk() (*string, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *HTTPAuthorizationCredentials) SetCredentials(v string)`

SetCredentials sets Credentials field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
