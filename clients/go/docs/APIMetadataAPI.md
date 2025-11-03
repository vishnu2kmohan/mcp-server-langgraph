# \APIMetadataAPI

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**GetApiVersionMetadata**](APIMetadataAPI.md#GetApiVersionMetadata) | **Get** /api/version | Get API version information



## GetApiVersionMetadata

> APIVersionInfo GetApiVersionMetadata(ctx).Execute()

Get API version information



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

	configuration := openapiclient.NewConfiguration()
	apiClient := openapiclient.NewAPIClient(configuration)
	resp, r, err := apiClient.APIMetadataAPI.GetApiVersionMetadata(context.Background()).Execute()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error when calling `APIMetadataAPI.GetApiVersionMetadata``: %v\n", err)
		fmt.Fprintf(os.Stderr, "Full HTTP response: %v\n", r)
	}
	// response from `GetApiVersionMetadata`: APIVersionInfo
	fmt.Fprintf(os.Stdout, "Response from `APIMetadataAPI.GetApiVersionMetadata`: %v\n", resp)
}
```

### Path Parameters

This endpoint does not need any parameter.

### Other Parameters

Other parameters are passed through a pointer to a apiGetApiVersionMetadataRequest struct via the builder pattern


### Return type

[**APIVersionInfo**](APIVersionInfo.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints)
[[Back to Model list]](../README.md#documentation-for-models)
[[Back to README]](../README.md)

