import json
import responses
from cloudos_cli.procurement import Images
from tests.functions_for_pytest import load_json_file
from responses import matchers

# Constants
APIKEY = 'vnoiweur89u2ongs'
CLOUDOS_URL = 'http://cloudos.lifebit.ai'
PROCUREMENT_ID = 'lv89ufc838sdig'

# Files
INPUT_IMAGES = "tests/test_data/procurement_images.json"

@responses.activate
def test_list_procurement_images():
    mock_images = json.loads(load_json_file(INPUT_IMAGES))

    # Matchers
    params_base_images = {}
    params_pagination = { "page": 1, "limit": 10 }

    headers = {
        "Content-type": "application/json",
        "apikey": APIKEY
    }

    # Mock endpoints
    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_images),
        match=[matchers.query_param_matcher(params_base_images)],
        status=200
    )

    responses.add(
        responses.GET,
        url=f"{CLOUDOS_URL}/api/v1/procurements/{PROCUREMENT_ID}/images",
        body=json.dumps(mock_images),
        match=[matchers.query_param_matcher(params_pagination)],
        status=200
    )


    procurement_images = Images(
        cloudos_url=CLOUDOS_URL,
        apikey=APIKEY,
        procurement_id=PROCUREMENT_ID,
        verify=True,
        cromwell_token=None
    )

    result = procurement_images.list_procurement_images()

    assert "image_configurations" in result
    assert isinstance(result["image_configurations"], list)

    expected_keys = {
        "lastUpdatedBy", "imageName", "imageType", "isLifebitManaged",
        "region", "provider", "imageId", "id", "organisationName", "updatedAt"
    }

    for image in result["image_configurations"]:
        # Check all expected keys are present
        assert expected_keys.issubset(image.keys()), f"Missing keys in image: {image}"

        # Validate types of a few key fields
        assert isinstance(image["imageName"], str)
        assert isinstance(image["imageType"], str)
        assert isinstance(image["isLifebitManaged"], bool)
        assert image["region"] == "eu-west-2"
        assert image["provider"] == "aws"
        assert image["imageId"].startswith("ami-")
        assert "Lifebit" in image["lastUpdatedBy"]

    # Check if one of the images is JobDefault
    assert any(img["imageType"] == "JobDefault" for img in result["image_configurations"])

    # Check pagination metadata
    assert "pagination_metadata" in result
    pagination = result["pagination_metadata"]
    assert pagination.get("Pagination-Count") == 4
    assert pagination.get("Pagination-Page") == 1
    assert pagination.get("Pagination-Limit") == 10
