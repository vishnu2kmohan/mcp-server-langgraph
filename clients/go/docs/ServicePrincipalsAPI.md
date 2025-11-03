# \ServicePrincipalsAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost**](ServicePrincipalsAPI.md#AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost) | **Post** /api/v1/service-principals/{service_id}/associate-user | Associate Service Principal With User
[**CreateServicePrincipalApiV1ServicePrincipalsPost**](ServicePrincipalsAPI.md#CreateServicePrincipalApiV1ServicePrincipalsPost) | **Post** /api/v1/service-principals/ | Create Service Principal
[**DeleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete**](ServicePrincipalsAPI.md#DeleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete) | **Delete** /api/v1/service-principals/{service_id} | Delete Service Principal
[**GetServicePrincipalApiV1ServicePrincipalsServiceIdGet**](ServicePrincipalsAPI.md#GetServicePrincipalApiV1ServicePrincipalsServiceIdGet) | **Get** /api/v1/service-principals/{service_id} | Get Service Principal
[**ListServicePrincipalsApiV1ServicePrincipalsGet**](ServicePrincipalsAPI.md#ListServicePrincipalsApiV1ServicePrincipalsGet) | **Get** /api/v1/service-principals/ | List Service Principals
[**RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost**](ServicePrincipalsAPI.md#RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost) | **Post** /api/v1/service-principals/{service_id}/rotate-secret | Rotate Service Principal Secret



## AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost

> ServicePrincipalResponse AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost(ctx, serviceId).UserId(userId).InheritPermissions(inheritPermissions).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Associate Service Principal With User



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	serviceId := "serviceId_example" // string | 
	userId := "userId_example" // string | 
	inheritPermissions := true // bool |  (optional) (default to true)
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ServicePrincipalsAPI.AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost(context.Background(), serviceId).UserId(userId).InheritPermissions(inheritPermissions).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ServicePrincipalsAPI.AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost`: ServicePrincipalResponse
	fmt.Fprintf(os.Stdout, "Response from `ServicePrincipalsAPI.AssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**serviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiAssociateServicePrincipalWithUserApiV1ServicePrincipalsServiceIdAssociateUserPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **userId** | **string** |  | 
 **inheritPermissions** | **bool** |  | [default to true]
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**ServicePrincipalResponse**](ServicePrincipalResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## CreateServicePrincipalApiV1ServicePrincipalsPost

> CreateServicePrincipalResponse CreateServicePrincipalApiV1ServicePrincipalsPost(ctx).BodyCreateServicePrincipalApiV1ServicePrincipalsPost(bodyCreateServicePrincipalApiV1ServicePrincipalsPost).Execute()

Create Service Principal



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	bodyCreateServicePrincipalApiV1ServicePrincipalsPost := *openapiclient.NewBodyCreateServicePrincipalApiV1ServicePrincipalsPost(*openapiclient.NewCreateServicePrincipalRequest("Name_example", "Description_example")) // BodyCreateServicePrincipalApiV1ServicePrincipalsPost | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ServicePrincipalsAPI.CreateServicePrincipalApiV1ServicePrincipalsPost(context.Background()).BodyCreateServicePrincipalApiV1ServicePrincipalsPost(bodyCreateServicePrincipalApiV1ServicePrincipalsPost).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ServicePrincipalsAPI.CreateServicePrincipalApiV1ServicePrincipalsPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateServicePrincipalApiV1ServicePrincipalsPost`: CreateServicePrincipalResponse
	fmt.Fprintf(os.Stdout, "Response from `ServicePrincipalsAPI.CreateServicePrincipalApiV1ServicePrincipalsPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateServicePrincipalApiV1ServicePrincipalsPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bodyCreateServicePrincipalApiV1ServicePrincipalsPost** | [**BodyCreateServicePrincipalApiV1ServicePrincipalsPost**](BodyCreateServicePrincipalApiV1ServicePrincipalsPost.md) |  | 

### Return type

[**CreateServicePrincipalResponse**](CreateServicePrincipalResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## DeleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete

> DeleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete(ctx, serviceId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Delete Service Principal



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	serviceId := "serviceId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	r, err := apiClient.ServicePrincipalsAPI.DeleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete(context.Background(), serviceId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ServicePrincipalsAPI.DeleteServicePrincipalApiV1ServicePrincipalsServiceIdDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**serviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiDeleteServicePrincipalApiV1ServicePrincipalsServiceIdDeleteRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

 (empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## GetServicePrincipalApiV1ServicePrincipalsServiceIdGet

> ServicePrincipalResponse GetServicePrincipalApiV1ServicePrincipalsServiceIdGet(ctx, serviceId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Get Service Principal



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	serviceId := "serviceId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ServicePrincipalsAPI.GetServicePrincipalApiV1ServicePrincipalsServiceIdGet(context.Background(), serviceId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ServicePrincipalsAPI.GetServicePrincipalApiV1ServicePrincipalsServiceIdGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetServicePrincipalApiV1ServicePrincipalsServiceIdGet`: ServicePrincipalResponse
	fmt.Fprintf(os.Stdout, "Response from `ServicePrincipalsAPI.GetServicePrincipalApiV1ServicePrincipalsServiceIdGet`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**serviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiGetServicePrincipalApiV1ServicePrincipalsServiceIdGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**ServicePrincipalResponse**](ServicePrincipalResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListServicePrincipalsApiV1ServicePrincipalsGet

> []ServicePrincipalResponse ListServicePrincipalsApiV1ServicePrincipalsGet(ctx).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

List Service Principals



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ServicePrincipalsAPI.ListServicePrincipalsApiV1ServicePrincipalsGet(context.Background()).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ServicePrincipalsAPI.ListServicePrincipalsApiV1ServicePrincipalsGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListServicePrincipalsApiV1ServicePrincipalsGet`: []ServicePrincipalResponse
	fmt.Fprintf(os.Stdout, "Response from `ServicePrincipalsAPI.ListServicePrincipalsApiV1ServicePrincipalsGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListServicePrincipalsApiV1ServicePrincipalsGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**[]ServicePrincipalResponse**](ServicePrincipalResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost

> RotateSecretResponse RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost(ctx, serviceId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Rotate Service Principal Secret



### Example

```go
package main

import (
	"context"
	"fmt"
	"os"
	openapiclient "github.com/GIT_USER_ID/GIT_REPO_ID"
)

func main() {
	serviceId := "serviceId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.ServicePrincipalsAPI.RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost(context.Background(), serviceId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `ServicePrincipalsAPI.RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost`: RotateSecretResponse
	fmt.Fprintf(os.Stdout, "Response from `ServicePrincipalsAPI.RotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**serviceId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiRotateServicePrincipalSecretApiV1ServicePrincipalsServiceIdRotateSecretPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**RotateSecretResponse**](RotateSecretResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

