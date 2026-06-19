import json

import responses
from responses import matchers

from cloudos_cli.procurement import Images
from tests.functions_for_pytest import load_json_file

# Constants
APIKEY = "vnoiweur89u2ongs"
CLOUDOS_URL = "http://cloudos.lifebit.ai"
PROCUREMENT_ID = "lv89ufc838sdig"
ORGANISATION_ID = "org-12345678"

# Files
SET_IMAGE_RESPONSE = "tests/test_data/set_procurement_image_response.json"


@responses.activate
def test_set_procurement_organisation_image():
    mock_response = json.loads(load_json_file(SET_IMAGE_RESPONSE))

    headers = {"Content-type": "application/json", "apikey": APIKEY}

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-0123456789abcdef0",
        "imageName": "Custom-Job-Image",
        "imageVersion": "1.0.0",
    }

    # Mock endpoint
    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200,
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="JobDefault",
        provider="aws",
        region="eu-west-2",
        image_id="ami-0123456789abcdef0",
        image_name="Custom-Job-Image",
        image_version="1.0.0",
    )

    # Verify the image configuration details
    expected_config_keys = {
        "id",
        "organisationId",
        "imageType",
        "provider",
        "region",
        "imageId",
        "imageName",
        "isLifebitManaged",
        "lastUpdatedBy",
        "organisationName",
        "updatedAt",
    }
    assert expected_config_keys.issubset(result.keys()), (
        f"Missing keys in image config: {result}"
    )

    # Validate specific values
    assert result["organisationId"] == ORGANISATION_ID
    assert result["imageType"] == "JobDefault"
    assert result["provider"] == "aws"
    assert result["region"] == "eu-west-2"
    assert result["imageId"] == "ami-0123456789abcdef0"
    assert result["imageName"] == "Custom-Job-Image"
    assert isinstance(result["isLifebitManaged"], bool)
    assert result["isLifebitManaged"] is False


@responses.activate
def test_set_procurement_organisation_image_different_types():
    """Test setting different image types"""

    image_types = [
        "RegularInteractiveSessions",
        "SparkInteractiveSessions",
        "RStudioInteractiveSessions",
        "JupyterInteractiveSessions",
        "VSCodeInteractiveSessions",
        "NextflowBatchComputeEnvironment",
    ]

    for image_type in image_types:
        mock_response = {
            "id": f"config-{image_type.lower()}",
            "organisationId": ORGANISATION_ID,
            "imageType": image_type,
            "provider": "aws",
            "region": "eu-west-2",
            "imageId": f"ami-{image_type.lower()[:8]}123",
            "imageName": f"Custom-{image_type}-Image",
            "isLifebitManaged": False,
            "lastUpdatedBy": "test-user",
            "organisationName": "Test-Organisation",
            "updatedAt": "2025-07-28T12:00:00",
        }

        expected_payload = {
            "organisationId": ORGANISATION_ID,
            "imageType": image_type,
            "provider": "aws",
            "region": "eu-west-2",
            "imageId": f"ami-{image_type.lower()[:8]}123",
            "imageName": f"Custom-{image_type}-Image",
            "imageVersion": "1.0.0",
        }

        responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
            body=json.dumps(mock_response),
            match=[matchers.json_params_matcher(expected_payload)],
            status=200,
        )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    # Test each image type
    for image_type in image_types:
        result = procurement_images.set_procurement_organisation_image(
            organisation_id=ORGANISATION_ID,
            image_type=image_type,
            provider="aws",
            region="eu-west-2",
            image_id=f"ami-{image_type.lower()[:8]}123",
            image_name=f"Custom-{image_type}-Image",
            image_version="1.0.0",
        )

        assert result["imageType"] == image_type
        assert result["imageId"] == f"ami-{image_type.lower()[:8]}123"


@responses.activate
def test_set_procurement_organisation_image_without_image_name():
    """Test setting image configuration without providing image_name parameter"""

    mock_response = {
        "id": "68667809e13a844401d10f6c",
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-0123456789abcdef0",
        "imageName": None,
        "isLifebitManaged": False,
        "lastUpdatedBy": "test-user",
        "organisationName": "Test-Organisation",
        "updatedAt": "2025-07-28T12:00:00",
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-0123456789abcdef0",
        "imageName": None,
        "imageVersion": "1.0.0",
    }

    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200,
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="JobDefault",
        provider="aws",
        region="eu-west-2",
        image_id="ami-0123456789abcdef0",
        image_name=None,
        image_version="1.0.0",
    )

    assert result["imageName"] is None


@responses.activate
def test_set_procurement_organisation_image_azure_provider():
    """Test setting image configuration for Azure provider"""

    mock_response = {
        "id": "config-azure-123",
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "azure",
        "region": "eastus",
        "imageId": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/custom-image",
        "imageName": "Custom-Azure-Job-Image",
        "isLifebitManaged": False,
        "lastUpdatedBy": "test-user",
        "organisationName": "Test-Organisation",
        "updatedAt": "2025-07-28T12:00:00",
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "azure",
        "region": "eastus",
        "imageId": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/custom-image",
        "imageName": "Custom-Azure-Job-Image",
        "imageVersion": "1.0.0",
    }

    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200,
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="JobDefault",
        provider="azure",
        region="eastus",
        image_id="/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/custom-image",
        image_name="Custom-Azure-Job-Image",
        image_version="1.0.0",
    )

    assert result["provider"] == "azure"
    assert result["region"] == "eastus"
    assert result["isLifebitManaged"] is False


@responses.activate
def test_set_procurement_organisation_image_azure_different_regions():
    """Test setting image configuration for different Azure regions"""

    azure_regions = ["eastus", "westus2", "northeurope", "westeurope", "uksouth"]

    for region in azure_regions:
        mock_response = {
            "id": f"config-azure-{region}",
            "organisationId": ORGANISATION_ID,
            "imageType": "JobDefault",
            "provider": "azure",
            "region": region,
            "imageId": f"/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/custom-{region}",
            "imageName": f"Custom-Azure-Job-Image-{region}",
            "isLifebitManaged": False,
            "lastUpdatedBy": "test-user",
            "organisationName": "Test-Organisation",
            "updatedAt": "2025-07-28T12:00:00",
        }

        expected_payload = {
            "organisationId": ORGANISATION_ID,
            "imageType": "JobDefault",
            "provider": "azure",
            "region": region,
            "imageId": f"/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/custom-{region}",
            "imageName": f"Custom-Azure-Job-Image-{region}",
            "imageVersion": "1.0.0",
        }

        responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
            body=json.dumps(mock_response),
            match=[matchers.json_params_matcher(expected_payload)],
            status=200,
        )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    # Test each Azure region
    for region in azure_regions:
        result = procurement_images.set_procurement_organisation_image(
            organisation_id=ORGANISATION_ID,
            image_type="JobDefault",
            provider="azure",
            region=region,
            image_id=f"/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/custom-{region}",
            image_name=f"Custom-Azure-Job-Image-{region}",
            image_version="1.0.0",
        )

        assert result["provider"] == "azure"
        assert result["region"] == region
        assert result["isLifebitManaged"] is False


@responses.activate
def test_set_procurement_organisation_image_vscode_interactive_sessions():
    """Test setting VSCodeInteractiveSessions image type specifically"""

    mock_response = {
        "id": "config-vscode-123",
        "organisationId": ORGANISATION_ID,
        "imageType": "VSCodeInteractiveSessions",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-vscode-custom-123",
        "imageName": "Custom VSCode Interactive Sessions Image",
        "isLifebitManaged": False,
        "lastUpdatedBy": "test-user",
        "organisationName": "Test-Organisation",
        "updatedAt": "2025-07-28T12:00:00",
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "VSCodeInteractiveSessions",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-vscode-custom-123",
        "imageName": "Custom VSCode Interactive Sessions Image",
        "imageVersion": "2.0.0",
    }

    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200,
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="VSCodeInteractiveSessions",
        provider="aws",
        region="eu-west-2",
        image_id="ami-vscode-custom-123",
        image_name="Custom VSCode Interactive Sessions Image",
        image_version="2.0.0",
    )

    assert result["imageType"] == "VSCodeInteractiveSessions"
    assert result["isLifebitManaged"] is False
    assert "vscode" in result["imageId"].lower()


@responses.activate
def test_set_procurement_organisation_image_vscode_azure():
    """Test setting VSCodeInteractiveSessions image type with Azure provider"""

    mock_response = {
        "id": "config-vscode-azure-123",
        "organisationId": ORGANISATION_ID,
        "imageType": "VSCodeInteractiveSessions",
        "provider": "azure",
        "region": "westeurope",
        "imageId": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/vscode-custom",
        "imageName": "Custom VSCode Interactive Sessions Image (Azure)",
        "isLifebitManaged": False,
        "lastUpdatedBy": "test-user",
        "organisationName": "Test-Organisation",
        "updatedAt": "2025-07-28T12:00:00",
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "VSCodeInteractiveSessions",
        "provider": "azure",
        "region": "westeurope",
        "imageId": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/vscode-custom",
        "imageName": "Custom VSCode Interactive Sessions Image (Azure)",
        "imageVersion": "1.0.0",
    }

    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200,
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None,
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="VSCodeInteractiveSessions",
        provider="azure",
        region="westeurope",
        image_id="/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Compute/images/vscode-custom",
        image_name="Custom VSCode Interactive Sessions Image (Azure)",
        image_version="1.0.0",
    )

    assert result["imageType"] == "VSCodeInteractiveSessions"
    assert result["provider"] == "azure"
    assert result["region"] == "westeurope"
    assert result["isLifebitManaged"] is False
