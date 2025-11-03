# SCIMGroup

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Schemas** | Pointer to **[]string** |  | [optional] [default to [urn:ietf:params:scim:schemas:core:2.0:Group]]
**Id** | Pointer to **NullableString** |  | [optional]
**DisplayName** | **string** |  |
**Members** | Pointer to [**[]SCIMMember**](SCIMMember.md) |  | [optional] [default to []]
**Meta** | Pointer to **map[string]interface{}** |  | [optional]

## Methods

### NewSCIMGroup

`func NewSCIMGroup(displayName string, ) *SCIMGroup`

NewSCIMGroup instantiates a new SCIMGroup object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMGroupWithDefaults

`func NewSCIMGroupWithDefaults() *SCIMGroup`

NewSCIMGroupWithDefaults instantiates a new SCIMGroup object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSchemas

`func (o *SCIMGroup) GetSchemas() []*string`

GetSchemas returns the Schemas field if non-nil, zero value otherwise.

### GetSchemasOk

`func (o *SCIMGroup) GetSchemasOk() (*[]*string, bool)`

GetSchemasOk returns a tuple with the Schemas field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSchemas

`func (o *SCIMGroup) SetSchemas(v []*string)`

SetSchemas sets Schemas field to given value.

### HasSchemas

`func (o *SCIMGroup) HasSchemas() bool`

HasSchemas returns a boolean if a field has been set.

### GetId

`func (o *SCIMGroup) GetId() string`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *SCIMGroup) GetIdOk() (*string, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *SCIMGroup) SetId(v string)`

SetId sets Id field to given value.

### HasId

`func (o *SCIMGroup) HasId() bool`

HasId returns a boolean if a field has been set.

### SetIdNil

`func (o *SCIMGroup) SetIdNil(b bool)`

 SetIdNil sets the value for Id to be an explicit nil

### UnsetId
`func (o *SCIMGroup) UnsetId()`

UnsetId ensures that no value is present for Id, not even an explicit nil
### GetDisplayName

`func (o *SCIMGroup) GetDisplayName() string`

GetDisplayName returns the DisplayName field if non-nil, zero value otherwise.

### GetDisplayNameOk

`func (o *SCIMGroup) GetDisplayNameOk() (*string, bool)`

GetDisplayNameOk returns a tuple with the DisplayName field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDisplayName

`func (o *SCIMGroup) SetDisplayName(v string)`

SetDisplayName sets DisplayName field to given value.


### GetMembers

`func (o *SCIMGroup) GetMembers() []SCIMMember`

GetMembers returns the Members field if non-nil, zero value otherwise.

### GetMembersOk

`func (o *SCIMGroup) GetMembersOk() (*[]SCIMMember, bool)`

GetMembersOk returns a tuple with the Members field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMembers

`func (o *SCIMGroup) SetMembers(v []SCIMMember)`

SetMembers sets Members field to given value.

### HasMembers

`func (o *SCIMGroup) HasMembers() bool`

HasMembers returns a boolean if a field has been set.

### GetMeta

`func (o *SCIMGroup) GetMeta() map[string]interface{}`

GetMeta returns the Meta field if non-nil, zero value otherwise.

### GetMetaOk

`func (o *SCIMGroup) GetMetaOk() (*map[string]interface{}, bool)`

GetMetaOk returns a tuple with the Meta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMeta

`func (o *SCIMGroup) SetMeta(v map[string]interface{})`

SetMeta sets Meta field to given value.

### HasMeta

`func (o *SCIMGroup) HasMeta() bool`

HasMeta returns a boolean if a field has been set.

### SetMetaNil

`func (o *SCIMGroup) SetMetaNil(b bool)`

 SetMetaNil sets the value for Meta to be an explicit nil

### UnsetMeta
`func (o *SCIMGroup) UnsetMeta()`

UnsetMeta ensures that no value is present for Meta, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
