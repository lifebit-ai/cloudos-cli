"""
This is the main class for procurement images interaction.
"""

import json
from dataclasses import dataclass
from cloudos_cli.clos import Cloudos
from typing import Union
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_get, retry_requests_put

@dataclass
class Images(Cloudos):
    """Class for procurement images.

    Parameters
    ----------
    cloudos_url : string
        The CloudOS service url.
    apikey : string
        Your CloudOS API key.
    verify: [bool|string]
        Whether to use SSL verification or not. Alternatively, if
        a string is passed, it will be interpreted as the path to
        the SSL certificate file.
    procurement_id : string
        The specific Cloudos procurement id.
    page
        The specific page
    limit
        The number of items per page
    """
    procurement_id: str
    verify: Union[bool, str] = True
    page: str = 1
    limit: str = 10

    def list_procurement_images(self):
        """
        Fetch the information of images associated with all organisations of a given procurement.

        Uses
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        procurement_id : string
            The specific Cloudos procurement id.
        page
            The specific page
        limit
            The number of items per page
        """

        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        r = retry_requests_get("{}/api/v1/procurements/{}/images?page={}&limit={}".format(self.cloudos_url,
                               self.procurement_id, self.page, self.limit),
                               headers=headers, verify=self.verify)

        if r.status_code >= 400:
            raise BadRequestException(r)

        raw = r.json()
        image_configurations = raw.get("imageConfigurations", [])
        pagination_metadata = raw.get("paginationMetadata", [])
        response ={
            "image_configurations": image_configurations,
            "pagination_metadata": pagination_metadata
        }

        return response

    def set_procurement_organisation_image(self, organisation_id, image_type, provider, region, image_id, image_name):
        """
        Sets the value for a procurement image of a given organisation.

        Uses
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        procurement_id : string
            The specific Cloudos procurement id.
        organisationId
            The organisation where this change is going to be applied.
        imageType
            The image type. Possible values are:
            RegularInteractiveSessions
            SparkInteractiveSessions
            RStudioInteractiveSessions
            JupyterInteractiveSessions
            JobDefault
            NextflowBatchComputeEnvironment
        provider
            The cloud provider. Currently only supporting 'aws'.
        region
            The region. Currently only supporting aws regions.
        imageId
            The new value for image Id. Required.
        imageName
            The new value for image name. Optional.
        """

        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        payload = {
            "organisationId": organisation_id,
            "imageType": image_type,
            "imageName": image_name,
            "provider": provider,
            "region": region,
            "imageId": image_id
        }
        r = retry_requests_put("{}/api/v1/procurements/{}/images".format(self.cloudos_url, self.procurement_id),
                               headers=headers, data=json.dumps(payload), verify=self.verify)

        if r.status_code >= 400:
            raise BadRequestException(r)

        response = r.json()

        return response

    def reset_procurement_organisation_image(self, organisation_id, image_type, provider, region):
        """
        Sets the value for a procurement image of a given organisation

        Uses
        ----------
        apikey : string
            Your CloudOS API key
        cloudos_url : string
            The CloudOS service url.
        procurement_id : string
            The specific Cloudos procurement id.
        organisationId
            The organisation where this change is going to be applied.
        imageType
            The image type. Possible values are:
            RegularInteractiveSessions
            SparkInteractiveSessions
            RStudioInteractiveSessions
            JupyterInteractiveSessions
            JobDefault
            NextflowBatchComputeEnvironment
        provider
            The cloud provider. Currently only supporting 'aws'.
        region
            The region. Currently only supporting aws regions.
        """

        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }
        payload = {
            "organisationId": organisation_id,
            "imageType": image_type,
            "provider": provider,
            "region": region
        }
        r = retry_requests_put("{}/api/v1/procurements/{}/images/reset".format(self.cloudos_url,
                               self.procurement_id),
                               headers=headers, data=json.dumps(payload), verify=self.verify)

        if r.status_code >= 400:
            raise BadRequestException(r)

        response = r.json()

        return response
