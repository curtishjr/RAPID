"""
Functionality related to the Censys IPv4 index
"""

import logging
from .core import Index
from .search import CensysSearch

LOGGER = logging.getLogger(__name__)
"""The logger for this module"""

# TODO: Finish list of fields
# Fields are specified at https://censys.io/ipv4/help
# FIELDS = (
#     "ip",
#     "protocols",
#     "location",
#     "location.province",
#     "location.province.raw",
#     "location.registered_country_code",
#     "location.postal_code",
#     "location.country_code",
#     "location.timezone",
#     "location.continent",
#     "location.city",
#     "location.country",
#     "location.country.raw",
#     "location.longitude",
#     "location.registered_country",
#     "location.registered_country.raw",
#     "location.latitude",
#     "autonomous_system",
#     "autonomous_system.description",
# )
# """The list of valid fields within the IPv4 index"""

INDEX = Index.IPV4
"""The Censys IPv4 index"""


def is_valid_field(field):
    """
    Query whether a particular field is a valid field from the IPv4 data.

    Note: The current implementation always returns True

    :param field: The field name
    :return: True if this is a valid field, otherwise False
    """
    # TODO: Switch implementation once 'FIELDS' is complete, above (also remove corresponding docstring comment).
    return True
    # return field in FIELDS


class CensysIPv4Search(CensysSearch):
    """
    A Censys API access object for the search endpoint using the IPv4 index
    """

    def __init__(self):
        """
        Create a new API access object for the search endpoint using the IPv4 index.
        """
        super(CensysIPv4Search, self).__init__(Index.IPV4)

    def _is_field_valid(self, field):
        return is_valid_field(field)
