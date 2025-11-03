# BodyCreateGroupScimV2GroupsPost

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**GroupData** | **map[string]interface{}** |  | 
**Credentials** | Pointer to [**NullableHTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | [optional] 

## Methods

### NewBodyCreateGroupScimV2GroupsPost

`func NewBodyCreateGroupScimV2GroupsPost(groupData map[string]interface{}, ) *BodyCreateGroupScimV2GroupsPost`

NewBodyCreateGroupScimV2GroupsPost instantiates a new BodyCreateGroupScimV2GroupsPost object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewBodyCreateGroupScimV2GroupsPostWithDefaults

`func NewBodyCreateGroupScimV2GroupsPostWithDefaults() *BodyCreateGroupScimV2GroupsPost`

NewBodyCreateGroupScimV2GroupsPostWithDefaults instantiates a new BodyCreateGroupScimV2GroupsPost object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetGroupData

`func (o *BodyCreateGroupScimV2GroupsPost) GetGroupData() map[string]interface{}`

GetGroupData returns the GroupData field if non-nil, zero value otherwise.

### GetGroupDataOk

`func (o *BodyCreateGroupScimV2GroupsPost) GetGroupDataOk() (*map[string]interface{}, bool)`

GetGroupDataOk returns a tuple with the GroupData field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGroupData

`func (o *BodyCreateGroupScimV2GroupsPost) SetGroupData(v map[string]interface{})`

SetGroupData sets GroupData field to given value.


### GetCredentials

`func (o *BodyCreateGroupScimV2GroupsPost) GetCredentials() HTTPAuthorizationCredentials`

GetCredentials returns the Credentials field if non-nil, zero value otherwise.

### GetCredentialsOk

`func (o *BodyCreateGroupScimV2GroupsPost) GetCredentialsOk() (*HTTPAuthorizationCredentials, bool)`

GetCredentialsOk returns a tuple with the Credentials field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCredentials

`func (o *BodyCreateGroupScimV2GroupsPost) SetCredentials(v HTTPAuthorizationCredentials)`

SetCredentials sets Credentials field to given value.

### HasCredentials

`func (o *BodyCreateGroupScimV2GroupsPost) HasCredentials() bool`

HasCredentials returns a boolean if a field has been set.

### SetCredentialsNil

`func (o *BodyCreateGroupScimV2GroupsPost) SetCredentialsNil(b bool)`

 SetCredentialsNil sets the value for Credentials to be an explicit nil

### UnsetCredentials
`func (o *BodyCreateGroupScimV2GroupsPost) UnsetCredentials()`

UnsetCredentials ensures that no value is present for Credentials, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


