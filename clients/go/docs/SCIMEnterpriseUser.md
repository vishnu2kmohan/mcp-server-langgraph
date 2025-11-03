# SCIMEnterpriseUser

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**EmployeeNumber** | Pointer to **NullableString** |  | [optional]
**CostCenter** | Pointer to **NullableString** |  | [optional]
**Organization** | Pointer to **NullableString** |  | [optional]
**Division** | Pointer to **NullableString** |  | [optional]
**Department** | Pointer to **NullableString** |  | [optional]
**Manager** | Pointer to **map[string]string** |  | [optional]

## Methods

### NewSCIMEnterpriseUser

`func NewSCIMEnterpriseUser() *SCIMEnterpriseUser`

NewSCIMEnterpriseUser instantiates a new SCIMEnterpriseUser object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSCIMEnterpriseUserWithDefaults

`func NewSCIMEnterpriseUserWithDefaults() *SCIMEnterpriseUser`

NewSCIMEnterpriseUserWithDefaults instantiates a new SCIMEnterpriseUser object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetEmployeeNumber

`func (o *SCIMEnterpriseUser) GetEmployeeNumber() string`

GetEmployeeNumber returns the EmployeeNumber field if non-nil, zero value otherwise.

### GetEmployeeNumberOk

`func (o *SCIMEnterpriseUser) GetEmployeeNumberOk() (*string, bool)`

GetEmployeeNumberOk returns a tuple with the EmployeeNumber field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEmployeeNumber

`func (o *SCIMEnterpriseUser) SetEmployeeNumber(v string)`

SetEmployeeNumber sets EmployeeNumber field to given value.

### HasEmployeeNumber

`func (o *SCIMEnterpriseUser) HasEmployeeNumber() bool`

HasEmployeeNumber returns a boolean if a field has been set.

### SetEmployeeNumberNil

`func (o *SCIMEnterpriseUser) SetEmployeeNumberNil(b bool)`

 SetEmployeeNumberNil sets the value for EmployeeNumber to be an explicit nil

### UnsetEmployeeNumber
`func (o *SCIMEnterpriseUser) UnsetEmployeeNumber()`

UnsetEmployeeNumber ensures that no value is present for EmployeeNumber, not even an explicit nil
### GetCostCenter

`func (o *SCIMEnterpriseUser) GetCostCenter() string`

GetCostCenter returns the CostCenter field if non-nil, zero value otherwise.

### GetCostCenterOk

`func (o *SCIMEnterpriseUser) GetCostCenterOk() (*string, bool)`

GetCostCenterOk returns a tuple with the CostCenter field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCostCenter

`func (o *SCIMEnterpriseUser) SetCostCenter(v string)`

SetCostCenter sets CostCenter field to given value.

### HasCostCenter

`func (o *SCIMEnterpriseUser) HasCostCenter() bool`

HasCostCenter returns a boolean if a field has been set.

### SetCostCenterNil

`func (o *SCIMEnterpriseUser) SetCostCenterNil(b bool)`

 SetCostCenterNil sets the value for CostCenter to be an explicit nil

### UnsetCostCenter
`func (o *SCIMEnterpriseUser) UnsetCostCenter()`

UnsetCostCenter ensures that no value is present for CostCenter, not even an explicit nil
### GetOrganization

`func (o *SCIMEnterpriseUser) GetOrganization() string`

GetOrganization returns the Organization field if non-nil, zero value otherwise.

### GetOrganizationOk

`func (o *SCIMEnterpriseUser) GetOrganizationOk() (*string, bool)`

GetOrganizationOk returns a tuple with the Organization field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOrganization

`func (o *SCIMEnterpriseUser) SetOrganization(v string)`

SetOrganization sets Organization field to given value.

### HasOrganization

`func (o *SCIMEnterpriseUser) HasOrganization() bool`

HasOrganization returns a boolean if a field has been set.

### SetOrganizationNil

`func (o *SCIMEnterpriseUser) SetOrganizationNil(b bool)`

 SetOrganizationNil sets the value for Organization to be an explicit nil

### UnsetOrganization
`func (o *SCIMEnterpriseUser) UnsetOrganization()`

UnsetOrganization ensures that no value is present for Organization, not even an explicit nil
### GetDivision

`func (o *SCIMEnterpriseUser) GetDivision() string`

GetDivision returns the Division field if non-nil, zero value otherwise.

### GetDivisionOk

`func (o *SCIMEnterpriseUser) GetDivisionOk() (*string, bool)`

GetDivisionOk returns a tuple with the Division field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDivision

`func (o *SCIMEnterpriseUser) SetDivision(v string)`

SetDivision sets Division field to given value.

### HasDivision

`func (o *SCIMEnterpriseUser) HasDivision() bool`

HasDivision returns a boolean if a field has been set.

### SetDivisionNil

`func (o *SCIMEnterpriseUser) SetDivisionNil(b bool)`

 SetDivisionNil sets the value for Division to be an explicit nil

### UnsetDivision
`func (o *SCIMEnterpriseUser) UnsetDivision()`

UnsetDivision ensures that no value is present for Division, not even an explicit nil
### GetDepartment

`func (o *SCIMEnterpriseUser) GetDepartment() string`

GetDepartment returns the Department field if non-nil, zero value otherwise.

### GetDepartmentOk

`func (o *SCIMEnterpriseUser) GetDepartmentOk() (*string, bool)`

GetDepartmentOk returns a tuple with the Department field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDepartment

`func (o *SCIMEnterpriseUser) SetDepartment(v string)`

SetDepartment sets Department field to given value.

### HasDepartment

`func (o *SCIMEnterpriseUser) HasDepartment() bool`

HasDepartment returns a boolean if a field has been set.

### SetDepartmentNil

`func (o *SCIMEnterpriseUser) SetDepartmentNil(b bool)`

 SetDepartmentNil sets the value for Department to be an explicit nil

### UnsetDepartment
`func (o *SCIMEnterpriseUser) UnsetDepartment()`

UnsetDepartment ensures that no value is present for Department, not even an explicit nil
### GetManager

`func (o *SCIMEnterpriseUser) GetManager() map[string]string`

GetManager returns the Manager field if non-nil, zero value otherwise.

### GetManagerOk

`func (o *SCIMEnterpriseUser) GetManagerOk() (*map[string]string, bool)`

GetManagerOk returns a tuple with the Manager field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetManager

`func (o *SCIMEnterpriseUser) SetManager(v map[string]string)`

SetManager sets Manager field to given value.

### HasManager

`func (o *SCIMEnterpriseUser) HasManager() bool`

HasManager returns a boolean if a field has been set.

### SetManagerNil

`func (o *SCIMEnterpriseUser) SetManagerNil(b bool)`

 SetManagerNil sets the value for Manager to be an explicit nil

### UnsetManager
`func (o *SCIMEnterpriseUser) UnsetManager()`

UnsetManager ensures that no value is present for Manager, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
