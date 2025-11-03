# CreateServicePrincipalRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** | Human-readable name for the service |
**Description** | **string** | Purpose/description of the service |
**AuthenticationMode** | Pointer to **string** | Authentication mode: &#39;client_credentials&#39; or &#39;service_account_user&#39; | [optional] [default to "client_credentials"]
**AssociatedUserId** | Pointer to **NullableString** |  | [optional]
**InheritPermissions** | Pointer to **bool** | Whether to inherit permissions from associated user | [optional] [default to false]

## Methods

### NewCreateServicePrincipalRequest

`func NewCreateServicePrincipalRequest(name string, description string, ) *CreateServicePrincipalRequest`

NewCreateServicePrincipalRequest instantiates a new CreateServicePrincipalRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewCreateServicePrincipalRequestWithDefaults

`func NewCreateServicePrincipalRequestWithDefaults() *CreateServicePrincipalRequest`

NewCreateServicePrincipalRequestWithDefaults instantiates a new CreateServicePrincipalRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *CreateServicePrincipalRequest) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *CreateServicePrincipalRequest) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *CreateServicePrincipalRequest) SetName(v string)`

SetName sets Name field to given value.


### GetDescription

`func (o *CreateServicePrincipalRequest) GetDescription() string`

GetDescription returns the Description field if non-nil, zero value otherwise.

### GetDescriptionOk

`func (o *CreateServicePrincipalRequest) GetDescriptionOk() (*string, bool)`

GetDescriptionOk returns a tuple with the Description field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDescription

`func (o *CreateServicePrincipalRequest) SetDescription(v string)`

SetDescription sets Description field to given value.


### GetAuthenticationMode

`func (o *CreateServicePrincipalRequest) GetAuthenticationMode() string`

GetAuthenticationMode returns the AuthenticationMode field if non-nil, zero value otherwise.

### GetAuthenticationModeOk

`func (o *CreateServicePrincipalRequest) GetAuthenticationModeOk() (*string, bool)`

GetAuthenticationModeOk returns a tuple with the AuthenticationMode field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthenticationMode

`func (o *CreateServicePrincipalRequest) SetAuthenticationMode(v string)`

SetAuthenticationMode sets AuthenticationMode field to given value.

### HasAuthenticationMode

`func (o *CreateServicePrincipalRequest) HasAuthenticationMode() bool`

HasAuthenticationMode returns a boolean if a field has been set.

### GetAssociatedUserId

`func (o *CreateServicePrincipalRequest) GetAssociatedUserId() string`

GetAssociatedUserId returns the AssociatedUserId field if non-nil, zero value otherwise.

### GetAssociatedUserIdOk

`func (o *CreateServicePrincipalRequest) GetAssociatedUserIdOk() (*string, bool)`

GetAssociatedUserIdOk returns a tuple with the AssociatedUserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAssociatedUserId

`func (o *CreateServicePrincipalRequest) SetAssociatedUserId(v string)`

SetAssociatedUserId sets AssociatedUserId field to given value.

### HasAssociatedUserId

`func (o *CreateServicePrincipalRequest) HasAssociatedUserId() bool`

HasAssociatedUserId returns a boolean if a field has been set.

### SetAssociatedUserIdNil

`func (o *CreateServicePrincipalRequest) SetAssociatedUserIdNil(b bool)`

 SetAssociatedUserIdNil sets the value for AssociatedUserId to be an explicit nil

### UnsetAssociatedUserId
`func (o *CreateServicePrincipalRequest) UnsetAssociatedUserId()`

UnsetAssociatedUserId ensures that no value is present for AssociatedUserId, not even an explicit nil
### GetInheritPermissions

`func (o *CreateServicePrincipalRequest) GetInheritPermissions() bool`

GetInheritPermissions returns the InheritPermissions field if non-nil, zero value otherwise.

### GetInheritPermissionsOk

`func (o *CreateServicePrincipalRequest) GetInheritPermissionsOk() (*bool, bool)`

GetInheritPermissionsOk returns a tuple with the InheritPermissions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInheritPermissions

`func (o *CreateServicePrincipalRequest) SetInheritPermissions(v bool)`

SetInheritPermissions sets InheritPermissions field to given value.

### HasInheritPermissions

`func (o *CreateServicePrincipalRequest) HasInheritPermissions() bool`

HasInheritPermissions returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
