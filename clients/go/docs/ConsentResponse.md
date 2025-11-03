# ConsentResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**UserId** | **string** |  |
**Consents** | **map[string]map[string]interface{}** | Current consent status for all types |

## Methods

### NewConsentResponse

`func NewConsentResponse(userId string, consents map[string]map[string]interface{}, ) *ConsentResponse`

NewConsentResponse instantiates a new ConsentResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewConsentResponseWithDefaults

`func NewConsentResponseWithDefaults() *ConsentResponse`

NewConsentResponseWithDefaults instantiates a new ConsentResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetUserId

`func (o *ConsentResponse) GetUserId() string`

GetUserId returns the UserId field if non-nil, zero value otherwise.

### GetUserIdOk

`func (o *ConsentResponse) GetUserIdOk() (*string, bool)`

GetUserIdOk returns a tuple with the UserId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUserId

`func (o *ConsentResponse) SetUserId(v string)`

SetUserId sets UserId field to given value.


### GetConsents

`func (o *ConsentResponse) GetConsents() map[string]map[string]interface{}`

GetConsents returns the Consents field if non-nil, zero value otherwise.

### GetConsentsOk

`func (o *ConsentResponse) GetConsentsOk() (*map[string]map[string]interface{}, bool)`

GetConsentsOk returns a tuple with the Consents field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsents

`func (o *ConsentResponse) SetConsents(v map[string]map[string]interface{})`

SetConsents sets Consents field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
