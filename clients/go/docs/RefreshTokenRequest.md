# RefreshTokenRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**RefreshToken** | Pointer to **NullableString** |  | [optional] 
**CurrentToken** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewRefreshTokenRequest

`func NewRefreshTokenRequest() *RefreshTokenRequest`

NewRefreshTokenRequest instantiates a new RefreshTokenRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewRefreshTokenRequestWithDefaults

`func NewRefreshTokenRequestWithDefaults() *RefreshTokenRequest`

NewRefreshTokenRequestWithDefaults instantiates a new RefreshTokenRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetRefreshToken

`func (o *RefreshTokenRequest) GetRefreshToken() string`

GetRefreshToken returns the RefreshToken field if non-nil, zero value otherwise.

### GetRefreshTokenOk

`func (o *RefreshTokenRequest) GetRefreshTokenOk() (*string, bool)`

GetRefreshTokenOk returns a tuple with the RefreshToken field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetRefreshToken

`func (o *RefreshTokenRequest) SetRefreshToken(v string)`

SetRefreshToken sets RefreshToken field to given value.

### HasRefreshToken

`func (o *RefreshTokenRequest) HasRefreshToken() bool`

HasRefreshToken returns a boolean if a field has been set.

### SetRefreshTokenNil

`func (o *RefreshTokenRequest) SetRefreshTokenNil(b bool)`

 SetRefreshTokenNil sets the value for RefreshToken to be an explicit nil

### UnsetRefreshToken
`func (o *RefreshTokenRequest) UnsetRefreshToken()`

UnsetRefreshToken ensures that no value is present for RefreshToken, not even an explicit nil
### GetCurrentToken

`func (o *RefreshTokenRequest) GetCurrentToken() string`

GetCurrentToken returns the CurrentToken field if non-nil, zero value otherwise.

### GetCurrentTokenOk

`func (o *RefreshTokenRequest) GetCurrentTokenOk() (*string, bool)`

GetCurrentTokenOk returns a tuple with the CurrentToken field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCurrentToken

`func (o *RefreshTokenRequest) SetCurrentToken(v string)`

SetCurrentToken sets CurrentToken field to given value.

### HasCurrentToken

`func (o *RefreshTokenRequest) HasCurrentToken() bool`

HasCurrentToken returns a boolean if a field has been set.

### SetCurrentTokenNil

`func (o *RefreshTokenRequest) SetCurrentTokenNil(b bool)`

 SetCurrentTokenNil sets the value for CurrentToken to be an explicit nil

### UnsetCurrentToken
`func (o *RefreshTokenRequest) UnsetCurrentToken()`

UnsetCurrentToken ensures that no value is present for CurrentToken, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


