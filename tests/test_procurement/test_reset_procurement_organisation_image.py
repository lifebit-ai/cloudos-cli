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
RESET_IMAGE_RESPONSE = "tests/test_data/reset_procurement_image_response.json"

@responses.activate
def test_reset_procurement_organisation_image():
    mock_response = json.loads(load_json_file(RESET_IMAGE_RESPONSE))

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    expected_payload = {
        "organisationId": ORGANISATION_ID,
        "imageType": "JobDefault",
        "provider": "aws",
        "region": "eu-west-2"
    }

    # Mock endpoint
    responses.add(
        responses.PUT,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images/reset",
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

    result = procurement_images.reset_procurement_organisation_image(
        organisation_id=ORGANISATION_ID,
        image_type="JobDefault",
        provider="aws",
        region="eu-west-2"
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
    assert result["imageId"] == "ami-lifebit-default-123"
    assert result["imageName"] == "Lifebit Default Job Image"
    assert isinstance(result["isLifebitManaged"], bool)
    assert result["isLifebitManaged"] is True  # Should be True for reset to default
    assert "Lifebit" in result["lastUpdatedBy"]

@responses.activate
def test_reset_procurement_organisation_image_different_types():
    """Test resetting different image types"""

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
            "imageId": f"ami-lifebit-{image_type.lower()[:8]}-default",
            "imageName": f"Lifebit Default {image_type} Image",
            "isLifebitManaged": True,
            "lastUpdatedBy": "Lifebit System",
            "organisationName": "Test-Organisation",
            "updatedAt": "2025-07-28T12:00:00"
        }

        expected_payload = {
            "organisationId": ORGANISATION_ID,
            "imageType": image_type,
            "provider": "aws",
            "region": "eu-west-2"
        }

        responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images/reset",
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
        result = procurement_images.reset_procurement_organisation_image(
            organisation_id=ORGANISATION_ID,
            image_type=image_type,
            provider="aws",
            region="eu-west-2"
        )

        assert result["imageType"] == image_type
        assert result["isLifebitManaged"] is True
        assert result["imageId"] == f"ami-lifebit-{image_type.lower()[:8]}-default"
        assert "Lifebit" in result["lastUpdatedBy"]

@responses.activate
def test_reset_procurement_organisation_image_different_regions():
    """Test resetting image configuration for different AWS regions"""

    aws_regions = ["eu-west-1", "eu-west-2", "us-east-1", "us-west-2"]

    for region in aws_regions:
        mock_response = {
            "id": f"config-{region}",
            "organisationId": ORGANISATION_ID,
            "imageType": "JobDefault",
            "provider": "aws",
            "region": region,
            "imageId": f"ami-lifebit-{region}-default",
            "imageName": f"Lifebit Default Job Image ({region})",
            "isLifebitManaged": True,
            "lastUpdatedBy": "Lifebit System",
            "organisationName": "Test-Organisation",
            "updatedAt": "2025-07-28T12:00:00"
        }

        expected_payload = {
            "organisationId": ORGANISATION_ID,
            "imageType": "JobDefault",
            "provider": "aws",
            "region": region
        }

        responses.add(
            responses.PUT,
            url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images/reset",
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

    # Test each region
    for region in aws_regions:
        result = procurement_images.reset_procurement_organisation_image(
            organisation_id=ORGANISATION_ID,
            image_type="JobDefault",
            provider="aws",
            region=region
        )

        assert result["region"] == region
        assert result["imageId"] == f"ami-lifebit-{region}-default"
        assert result["isLifebitManaged"] is True
