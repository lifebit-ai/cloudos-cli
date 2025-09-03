import json
import responses
from cloudos_cli.procurement import Images
from tests.functions_for_pytest import load_json_file
from responses import matchers

# Constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
PROCUREMENT_ID = 'lv89ufc838sdig'
ORGANISATION_ID = 'org-12345678'

# Files
SET_IMAGE_RESPONSE = "tests/test_data/set_procurement_image_response.json"

@responses.activate
def test_set_procurement_organisation_image():
    mock_response = json.loads(load_json_file(SET_IMAGE_RESPONSE))

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-0123456789abcdef0",
        "imageName": "Custom-Job-Image"
    }

    # Mock endpoint
    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="JobDefault",
        provider="aws",
        region="eu-west-2",
        image_id="ami-0123456789abcdef0",
        image_name="Custom-Job-Image"
    )

    # Verify the image configuration details
    expected_config_keys = {
        "id", "organisationId", "imageType", "provider", "region",
        "imageId", "imageName", "isLifebitManaged", "lastUpdatedBy",
        "organisationName", "updatedAt"
    }
    assert expected_config_keys.issubset(result.keys()), f"Missing keys in image config: {result}"

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
        "NextflowBatchComputeEnvironment"
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
            "updatedAt": "2025-07-28T12:00:00"
        }

        expected_payload = {
            "organisationId": ORGANISATION_ID,
            "imageType": image_type,
            "provider": "aws",
            "region": "eu-west-2",
            "imageId": f"ami-{image_type.lower()[:8]}123",
            "imageName": f"Custom-{image_type}-Image"
        }

        responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
            body=json.dumps(mock_response),
            match=[matchers.json_params_matcher(expected_payload)],
            status=200
        )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None
    )

    # Test each image type
    for image_type in image_types:
        result = procurement_images.set_procurement_organisation_image(
            organisation_id=ORGANISATION_ID,
            image_type=image_type,
            provider="aws",
            region="eu-west-2",
            image_id=f"ami-{image_type.lower()[:8]}123",
            image_name=f"Custom-{image_type}-Image"
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
        "updatedAt": "2025-07-28T12:00:00"
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "aws",
        "region": "eu-west-2",
        "imageId": "ami-0123456789abcdef0",
        "imageName": None
    }

    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_response),
        match=[matchers.json_params_matcher(expected_payload)],
        status=200
    )

    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None
    )

    result = procurement_images.set_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="JobDefault",
        provider="aws",
        region="eu-west-2",
        image_id="ami-0123456789abcdef0",
        image_name=None
    )

    assert result["imageName"] is None
