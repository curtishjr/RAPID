"""
Functionality related to the Censys top million websites index
"""

import logging
from .core import Index
from .search import CensysSearch

LOGGER = logging.getLogger(__name__)
"""The logger for this module"""

# TODO: Finish list of fields
# Fields are specified at https://censys.io/domain/help
# FIELDS = (
# )
# """The list of valid fields within the websites index"""

INDEX = Index.WEBSITES
"""The Censys websites index"""


def is_valid_field(field):
    """
    Query whether a particular field is a valid field from the top million websites data.

    Note: The current implementation always returns True

    :param field: The field name
    :return: True if this is a valid field, otherwise False
    """
    # TODO: Switch implementation once 'FIELDS' is complete, above (also remove corresponding docstring comment).
    return True
    # return field in FIELDS


class CensysWebsitesSearch(CensysSearch):
    """
    A Censys API access object for the search endpoint using the websites index
    """

    def __init__(self):
        """
        Create a new API access object for the search endpoint using the websites index.
        """
        super(CensysWebsitesSearch, self).__init__(Index.WEBSITES)

    def _is_field_valid(self, field):
        return is_valid_field(field)
