def get_path(param, param_kind_map, execution_platform, storage_provider, mode="parameters"):
    """
    Constructs a storage path based on the parameter kind and execution platform.

    Parameters
    ----------
    param : dict
        A dictionary containing parameter details. Expected keys include:
            - 'parameterKind': Specifies the kind of parameter (e.g., 'dataItem', 'globPattern').
            - For 'dataItem': Contains nested keys such as 'item', which includes:
                - 's3BucketName', 's3ObjectKey', 's3Prefix' (for AWS Batch).
                - 'blobStorageAccountName', 'blobContainerName', 'blobName' (for other platforms).
            - For 'globPattern': Contains nested keys such as 'folder', which includes:
                - 's3BucketName', 's3Prefix' (for AWS Batch).
                - 'blobStorageAccountName', 'blobContainerName', 'blobPrefix' (for other platforms).
    param_kind_map : dict
        A mapping of parameter kinds to their corresponding keys in the `param` dictionary.
    execution_platform : str
        The platform on which the execution is taking place. 
        Expected values include "Batch AWS" or other non-AWS platforms.
    storage_provider : str
        Either s3:// or az://
    mode : str
        For "parameters" is creating the '*.config' file and it adds the complete path, for "asis"
        leaves the constructed path as generated from the API

    Returns
    -------
    str: A constructed storage path based on the parameter kind and execution platform.
        - For 'dataItem' on AWS Batch: "s3BucketName/s3ObjectKey" or "s3BucketName/s3Prefix".
        - For 'dataItem' on other platforms: "blobStorageAccountName/blobContainerName/blobName".
        - For 'globPattern' on AWS Batch: "s3BucketName/s3Prefix/globPattern".
        - For 'globPattern' on other platforms: "blobStorageAccountName/blobContainerName/blobPrefix/globPattern".
    """
    value = param[param_kind_map[param['parameterKind']]]
    if param['parameterKind'] == 'dataItem':
        if execution_platform == "Batch AWS":
            s3_object_key = value['item'].get('s3ObjectKey', None) if value['item'].get('s3Prefix', None) is None else value['item'].get('s3Prefix', None)
            if mode == "parameters":
                value = storage_provider + value['item']['s3BucketName'] + '/' + s3_object_key
            else:
                value = value['item']['s3BucketName'] + '/' + s3_object_key
        else:
            account_name = value['item']['blobStorageAccountName'] + ".blob.core.windows.net"
            container_name = value['item']['blobContainerName']
            blob_name = value['item']['blobName']
            if mode == "parameters":
                value = storage_provider + account_name + '/' + container_name + '/' + blob_name
            else:
                value = value['item']['blobStorageAccountName'] + '/' + container_name + '/' + blob_name
    elif param['parameterKind'] == 'globPattern':
        if execution_platform == "Batch AWS":
            if mode == "parameters":
                value = storage_provider + param['folder']['s3BucketName'] + '/' + param['folder']['s3Prefix'] + '/' + param['globPattern']
            else:
                value = param['folder']['s3BucketName'] + '/' + param['folder']['s3Prefix'] + '/' + param['globPattern']
        else:
            account_name = param['folder']['blobStorageAccountName'] + ".blob.core.windows.net"
            container_name = param['folder']['blobContainerName']
            blob_name = param['folder']['blobPrefix']
            if mode == "parameters":
                value = storage_provider + account_name + '/' + container_name + '/' + blob_name + '/' + param['globPattern']
            else:
                value = param['folder']['blobStorageAccountName'] + '/' + container_name + '/' + blob_name + '/' + param['globPattern']

    return value
