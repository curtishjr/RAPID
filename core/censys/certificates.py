"""
Functionality related to the Certificates Censys index
"""

import logging
from .core import Index
from .search import CensysSearch

LOGGER = logging.getLogger(__name__)
"""The logger for this module"""

# TODO: Finish list of fields
# Fields are specified at https://censys.io/certificates/help
# FIELDS = (
# )
# """The list of valid fields within the certificates index"""

INDEX = Index.CERTIFICATES
"""The Censys certificates index"""


def is_valid_field(field):
    """
    Query whether a particular field is a valid field from the certificates data.

    Note: The current implementation always returns True

    :param field: The field name
    :return: True if this is a valid field, otherwise False
    """
    # TODO: Switch implementation once 'FIELDS' is complete, above (also remove corresponding docstring comment).
    return True
    # return field in FIELDS


class CensysCertificatesSearch(CensysSearch):
    """
    A Censys API access object for the search endpoint using the certificates index
    """

    def __init__(self):
        """
        Create a new API access object for the search endpoint using the certificates index.
        """
        super(CensysCertificatesSearch, self).__init__(Index.CERTIFICATES)

    def _is_field_valid(self, field):
        return is_valid_field(field)
