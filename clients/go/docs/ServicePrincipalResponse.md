# ServicePrincipalResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ServiceId** | **string** |  | 
**Name** | **string** |  | 
**Description** | **string** |  | 
**AuthenticationMode** | **string** |  | 
**AssociatedUserId** | **NullableString** |  | 
**OwnerUserId** | **NullableString** |  | 
**InheritPermissions** | **bool** |  | 
**Enabled** | **bool** |  | 
**CreatedAt** | **NullableString** |  | 

## Methods

### NewServicePrincipalResponse

`func NewServicePrincipalResponse(serviceId string, name string, description string, authenticationMode string, associatedUserId NullableString, ownerUserId NullableString, inheritPermissions bool, enabled bool, createdAt NullableString, ) *ServicePrincipalResponse`

NewServicePrincipalResponse instantiates a new ServicePrincipalResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewServicePrincipalResponseWithDefaults

`func NewServicePrincipalResponseWithDefaults() *ServicePrincipalResponse`

NewServicePrincipalResponseWithDefaults instantiates a new ServicePrincipalResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetServiceId

`func (o *ServicePrincipalResponse) GetServiceId() string`

GetServiceId returns the ServiceId field if non-nil, zero value otherwise.

### GetServiceIdOk

`func (o *ServicePrincipalResponse) GetServiceIdOk() (*string, bool)`

GetServiceIdOk returns a tuple with the ServiceId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetServiceId

`func (o *ServicePrincipalResponse) SetServiceId(v string)`

SetServiceId sets ServiceId field to given value.


### GetName

`func (o *ServicePrincipalResponse) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *ServicePrincipalResponse) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *ServicePrincipalResponse) SetName(v string)`

SetName sets Name field to given value.


### GetDescription

`func (o *ServicePrincipalResponse) GetDescription() string`

GetDescription returns the Description field if non-nil, zero value otherwise.

### GetDescriptionOk

`func (o *ServicePrincipalResponse) GetDescriptionOk() (*string, bool)`

GetDescriptionOk returns a tuple with the Description field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDescription

`func (o *ServicePrincipalResponse) SetDescription(v string)`

SetDescription sets Description field to given value.


### GetAuthenticationMode

`func (o *ServicePrincipalResponse) GetAuthenticationMode() string`

GetAuthenticationMode returns the AuthenticationMode field if non-nil, zero value otherwise.

### GetAuthenticationModeOk

`func (o *ServicePrincipalResponse) GetAuthenticationModeOk() (*string, bool)`

GetAuthenticationModeOk returns a tuple with the AuthenticationMode field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthenticationMode

`func (o *ServicePrincipalResponse) SetAuthenticationMode(v string)`

SetAuthenticationMode sets AuthenticationMode field to given value.


### GetAssociatedUserId

`func (o *ServicePrincipalResponse) GetAssociatedUserId() string`

GetAssociatedUserId returns the AssociatedUserId field if non-nil, zero value otherwise.

### GetAssociatedUserIdOk

`func (o *ServicePrincipalResponse) GetAssociatedUserIdOk() (*string, bool)`

GetAssociatedUserIdOk returns a tuple with the AssociatedUserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAssociatedUserId

`func (o *ServicePrincipalResponse) SetAssociatedUserId(v string)`

SetAssociatedUserId sets AssociatedUserId field to given value.


### SetAssociatedUserIdNil

`func (o *ServicePrincipalResponse) SetAssociatedUserIdNil(b bool)`

 SetAssociatedUserIdNil sets the value for AssociatedUserId to be an explicit nil

### UnsetAssociatedUserId
`func (o *ServicePrincipalResponse) UnsetAssociatedUserId()`

UnsetAssociatedUserId ensures that no value is present for AssociatedUserId, not even an explicit nil
### GetOwnerUserId

`func (o *ServicePrincipalResponse) GetOwnerUserId() string`

GetOwnerUserId returns the OwnerUserId field if non-nil, zero value otherwise.

### GetOwnerUserIdOk

`func (o *ServicePrincipalResponse) GetOwnerUserIdOk() (*string, bool)`

GetOwnerUserIdOk returns a tuple with the OwnerUserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOwnerUserId

`func (o *ServicePrincipalResponse) SetOwnerUserId(v string)`

SetOwnerUserId sets OwnerUserId field to given value.


### SetOwnerUserIdNil

`func (o *ServicePrincipalResponse) SetOwnerUserIdNil(b bool)`

 SetOwnerUserIdNil sets the value for OwnerUserId to be an explicit nil

### UnsetOwnerUserId
`func (o *ServicePrincipalResponse) UnsetOwnerUserId()`

UnsetOwnerUserId ensures that no value is present for OwnerUserId, not even an explicit nil
### GetInheritPermissions

`func (o *ServicePrincipalResponse) GetInheritPermissions() bool`

GetInheritPermissions returns the InheritPermissions field if non-nil, zero value otherwise.

### GetInheritPermissionsOk

`func (o *ServicePrincipalResponse) GetInheritPermissionsOk() (*bool, bool)`

GetInheritPermissionsOk returns a tuple with the InheritPermissions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetInheritPermissions

`func (o *ServicePrincipalResponse) SetInheritPermissions(v bool)`

SetInheritPermissions sets InheritPermissions field to given value.


### GetEnabled

`func (o *ServicePrincipalResponse) GetEnabled() bool`

GetEnabled returns the Enabled field if non-nil, zero value otherwise.

### GetEnabledOk

`func (o *ServicePrincipalResponse) GetEnabledOk() (*bool, bool)`

GetEnabledOk returns a tuple with the Enabled field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEnabled

`func (o *ServicePrincipalResponse) SetEnabled(v bool)`

SetEnabled sets Enabled field to given value.


### GetCreatedAt

`func (o *ServicePrincipalResponse) GetCreatedAt() string`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *ServicePrincipalResponse) GetCreatedAtOk() (*string, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *ServicePrincipalResponse) SetCreatedAt(v string)`

SetCreatedAt sets CreatedAt field to given value.


### SetCreatedAtNil

`func (o *ServicePrincipalResponse) SetCreatedAtNil(b bool)`

 SetCreatedAtNil sets the value for CreatedAt to be an explicit nil

### UnsetCreatedAt
`func (o *ServicePrincipalResponse) UnsetCreatedAt()`

UnsetCreatedAt ensures that no value is present for CreatedAt, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


