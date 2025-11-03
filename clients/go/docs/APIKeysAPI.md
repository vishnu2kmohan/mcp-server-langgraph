# \APIKeysAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**CreateApiKeyApiV1ApiKeysPost**](APIKeysAPI.md#CreateApiKeyApiV1ApiKeysPost) | **Post** /api/v1/api-keys/ | Create Api Key
[**ListApiKeysApiV1ApiKeysGet**](APIKeysAPI.md#ListApiKeysApiV1ApiKeysGet) | **Get** /api/v1/api-keys/ | List Api Keys
[**RevokeApiKeyApiV1ApiKeysKeyIdDelete**](APIKeysAPI.md#RevokeApiKeyApiV1ApiKeysKeyIdDelete) | **Delete** /api/v1/api-keys/{key_id} | Revoke Api Key
[**RotateApiKeyApiV1ApiKeysKeyIdRotatePost**](APIKeysAPI.md#RotateApiKeyApiV1ApiKeysKeyIdRotatePost) | **Post** /api/v1/api-keys/{key_id}/rotate | Rotate Api Key



## CreateApiKeyApiV1ApiKeysPost

> CreateAPIKeyResponse CreateApiKeyApiV1ApiKeysPost(ctx).BodyCreateApiKeyApiV1ApiKeysPost(bodyCreateApiKeyApiV1ApiKeysPost).Execute()

Create Api Key



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
	bodyCreateApiKeyApiV1ApiKeysPost := *openapiclient.NewBodyCreateApiKeyApiV1ApiKeysPost(*openapiclient.NewCreateAPIKeyRequest("Name_example")) // BodyCreateApiKeyApiV1ApiKeysPost | 

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.APIKeysAPI.CreateApiKeyApiV1ApiKeysPost(context.Background()).BodyCreateApiKeyApiV1ApiKeysPost(bodyCreateApiKeyApiV1ApiKeysPost).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `APIKeysAPI.CreateApiKeyApiV1ApiKeysPost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `CreateApiKeyApiV1ApiKeysPost`: CreateAPIKeyResponse
	fmt.Fprintf(os.Stdout, "Response from `APIKeysAPI.CreateApiKeyApiV1ApiKeysPost`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiCreateApiKeyApiV1ApiKeysPostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **bodyCreateApiKeyApiV1ApiKeysPost** | [**BodyCreateApiKeyApiV1ApiKeysPost**](BodyCreateApiKeyApiV1ApiKeysPost.md) |  | 

### Return type

[**CreateAPIKeyResponse**](CreateAPIKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## ListApiKeysApiV1ApiKeysGet

> []APIKeyResponse ListApiKeysApiV1ApiKeysGet(ctx).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

List Api Keys



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
	resp, r, err := apiClient.APIKeysAPI.ListApiKeysApiV1ApiKeysGet(context.Background()).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `APIKeysAPI.ListApiKeysApiV1ApiKeysGet``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `ListApiKeysApiV1ApiKeysGet`: []APIKeyResponse
	fmt.Fprintf(os.Stdout, "Response from `APIKeysAPI.ListApiKeysApiV1ApiKeysGet`: %v\n", resp)
}
```

### Path Parameters



### Other Parameters

Other parameters are passed through a pointer to a apiListApiKeysApiV1ApiKeysGetRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**[]APIKeyResponse**](APIKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)


## RevokeApiKeyApiV1ApiKeysKeyIdDelete

> RevokeApiKeyApiV1ApiKeysKeyIdDelete(ctx, keyId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Revoke Api Key



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
	keyId := "keyId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	r, err := apiClient.APIKeysAPI.RevokeApiKeyApiV1ApiKeysKeyIdDelete(context.Background(), keyId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `APIKeysAPI.RevokeApiKeyApiV1ApiKeysKeyIdDelete``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**keyId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiRevokeApiKeyApiV1ApiKeysKeyIdDeleteRequest struct via the builder pattern


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


## RotateApiKeyApiV1ApiKeysKeyIdRotatePost

> RotateAPIKeyResponse RotateApiKeyApiV1ApiKeysKeyIdRotatePost(ctx, keyId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()

Rotate Api Key



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
	keyId := "keyId_example" // string | 
	hTTPAuthorizationCredentials := *openapiclient.NewHTTPAuthorizationCredentials("Scheme_example", "Credentials_example") // HTTPAuthorizationCredentials |  (optional)

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.APIKeysAPI.RotateApiKeyApiV1ApiKeysKeyIdRotatePost(context.Background(), keyId).HTTPAuthorizationCredentials(hTTPAuthorizationCredentials).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `APIKeysAPI.RotateApiKeyApiV1ApiKeysKeyIdRotatePost``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `RotateApiKeyApiV1ApiKeysKeyIdRotatePost`: RotateAPIKeyResponse
	fmt.Fprintf(os.Stdout, "Response from `APIKeysAPI.RotateApiKeyApiV1ApiKeysKeyIdRotatePost`: %v\n", resp)
}
```

### Path Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
**ctx** | **context.Context** | context for authentication, logging, cancellation, deadlines, tracing, etc.
**keyId** | **string** |  | 

### Other Parameters

Other parameters are passed through a pointer to a apiRotateApiKeyApiV1ApiKeysKeyIdRotatePostRequest struct via the builder pattern


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------

 **hTTPAuthorizationCredentials** | [**HTTPAuthorizationCredentials**](HTTPAuthorizationCredentials.md) |  | 

### Return type

[**RotateAPIKeyResponse**](RotateAPIKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: application/json
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

