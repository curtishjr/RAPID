"""
Functionality related to the search endpoint of the Censys API
"""
import collections
import logging
import time
import sys
from .core import CensysApiAccessObject, CensysResultException, CensysResult, Endpoint, ErrorResult, HttpMethod


LOGGER = logging.getLogger(__name__)
"""The logger for this module"""


ENDPOINT = Endpoint.SEARCH
"""The search endpoint"""

RESERVED_CHARACTERS = ("+",
                       "-",
                       "=",
                       "&",
                       "|",
                       ">",
                       "<",
                       "!",
                       "(",
                       ")",
                       "{",
                       "}",
                       "[",
                       "]",
                       "^",
                       "\"",
                       "~",
                       "*",
                       "?",
                       ":",
                       "\\",
                       "/")
"""The reserved characters in the search syntax that must be escaped """


def escape(value):
    """
    Escape any reserved characters in a Censys search value.

    :param value: The original value
    :return: The escaped value
    """
    escape_dict = {}
    for escape_string in RESERVED_CHARACTERS:
        escape_dict[escape_string] = "\\" + escape_string
    return value.translate(str.maketrans(escape_dict))


class SearchException(CensysResultException):
    """
    A result exception from the Search API
    """
    pass


class SearchResult(CensysResult, collections.MutableMapping):
    """
    A single result from the Censys search API.

    A search result is a child of a SearchResultSet (its parent), accessible through its 'parent' property.  Search
    result instances are also dictionaries providing read-only access to all fields requested in the query (provided
    they were actually returned by Censys).
    """

    def __init__(self, parent, number_in_page, raw_result):
        if parent is None:
            raise RuntimeError("How is the parent null?!")
        super(SearchResult, self).__init__(parent.code, raw_result)
        self._parent = parent
        self._dict = dict(raw_result)
        self._number_in_page = number_in_page
        results_per_page = 100 if parent.current_page is not parent.total_pages else len(parent)
        self._overall_number = (results_per_page * parent.current_page) + number_in_page

    @property
    def parent(self):
        """
        Get the parent SearchResultSet of which this SearchResult is a part.

        :return: The parent search result set
        """
        return self._parent

    @property
    def number_in_page(self):
        """
        Get the number (index) of this search result on its page (i.e. within its parent search result set).

        :return: The number of this result on its page
        """
        return self._number_in_page

    @property
    def overall_number(self):
        """
        Get the number (index) of this search result within all results.

        :return: The overall number of this search result
        """
        return self._overall_number

    def __setitem__(self, key, value):
        raise KeyError("Search result fields may not be updated")

    def __delitem__(self, key):
        raise KeyError("Search result fields may not be deleted")

    def __getitem__(self, item):
        return self._dict[item]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return "%s(%s, %d, %s)" % (type(self).__name__, repr(self.parent), self.number_in_page, self.raw)

    def __str__(self):
        return str(self._dict)


class SearchResultSet(CensysResult):
    """
    The set of search results returned from the Censys search API.

    SearchResultSets are also immutable sequences of SearchResult instances.  While the "raw" results (i.e. the JSON
    returned by the server) are always immediately available, the child SearchResult instances are lazily loaded.
    """

    def __init__(self, index, code, raw):
        if code != 200:
            raise ValueError("Censys success results must have a 200 response code (not %d)" % code)
        super(SearchResultSet, self).__init__(code, raw)
        self._index = index
        self._status = raw["status"]
        metadata = raw["metadata"]
        self._count = metadata["count"]
        self._query = metadata["query"]
        self._backend_time = metadata["backend_time"]
        self._current_page = metadata["page"]
        self._total_pages = metadata["pages"]
        self._raw_results = raw["results"]
        self._results = None

    @property
    def index(self):
        """
        Get the Censys index that produced this set of search results.

        :return: The Index enumeration value identifiying the Censys index
        """
        return self._index

    @property
    def status(self):
        """
        Get the status returned by the server.

        This is a human-readable string, not a HTTP status code.  (Refer to the 'code' property for the latter.)

        :return: The status
        """
        return self._status

    @property
    def count(self):
        """
        Get the total number of results available from Censys for the query.

        This is NOT the number of results in this result set, but rather the TOTAL number of results across all pages.

        :return: The total number of results
        """
        return self._count

    @property
    def query(self):
        """
        Get the value for which the query was executed.

        :return: The queried value
        """
        return self._query

    @property
    def backend_time(self):
        """
        Get the length of time reported by Censys to execute the query.

        :return: The length of time to execute the query
        """
        return self._backend_time

    @property
    def current_page(self):
        """
        Get the current page number.

        Each SearchResultSet instance represents one page out of a total number of pages.  This property represents the
        page number of THIS result set.

        :return: The current page number
        """
        return self._current_page

    @property
    def total_pages(self):
        """
        Get the total number of pages of results available from Censys.

        :return: The total number of pages of results available
        """
        return self._total_pages

    @property
    def raw_results(self):
        """
        Get the raw JSON of the results provided by Censys.  This will include all results in this set.

        :return: The raw result JSON
        """
        return self._raw_results

    @property
    def results(self):
        """
        Get the list of SearchResult objects contained within this set.

        Accessing this property will cause lazy parsing of SearchResult instances.  This method does not return the
        internal set, but rather a copy of it.

        :return: The set of child SearchResults
        """
        self.__load_results()
        return list(self._results)

    def get_results_for_field(self, field):
        """
        Get a list of values for a given field.

        This is a convenience method that returns a list of values for one field across all results in this set.

        :param field: The field to be obtained
        :return: The list of result values
        """
        return [result[field] for result in self.results]

    def __load_results(self):
        """
        Perform lazy load parsing of SearchResult instances.

        If lazy-loading has already been performed, this method does nothing.

        :return: This method returns no values, but rather ensures that the 'self._results' member is properly
        initialized.
        """
        if self._results is not None:
            return
        self._results = list()
        for number_in_page in range(len(self._raw_results)):
            raw_result = self._raw_results[number_in_page]
            result = SearchResult(self, number_in_page, raw_result)
            self._results.append(result)

    def __repr__(self):
        return "%s(%s, %s, %s)" % (type(self).__name__, self.index, self.code, self.raw)

    def __iter__(self):
        return iter(self.results)

    def __getitem__(self, item):
        return self.results[item]

    def __len__(self):
        return len(self.results)


class CensysSearch(CensysApiAccessObject):
    """
    An Censys API access object for the search endpoint.

    Subclasses should override the '_is_field_valid' method if they provide field validation.  This class may be used
    directly, with the only loss of functionality being that fields are not validated when they are added.  (This could
    result in an error from the API when called.  In other words, subclasses are more fail-fast.)

    There are several ways to call this API:
        call: Use this method to return a SearchResultSet.  You specify the parameter each time; this method ignores the
              currently configured properties of the instance
        search: Use this method to return a SearchResultSet.  This method uses the currently configured properties of
              the instance
        get: This method is a generator yielding SearchResult instances.  This method may use the currently configured
              properties of the instance, but you may also override them.  Note that this method ignores pagination, and
              will iterate up to a specified maximum number of results.  CAUTION: Be careful, you can exceed your API
              rate limits easily with a high value!  In general, every 100 results is a separate call to the API.

    Note that a CensysSearch itself is iterable; it will iterate over the results of calling 'search.'  Thus there are
    four ways to use this API:
        VALUE = ...
        PAGE = 1
        with CensysSearch(index) as api:
            api.api_id = ...
            api.api_secret = ...

            # Using call:
            search_result_set = api.call(VALUE, PAGE, "ip")
            for search_result in search_result_set:
                ...

            # Using search:
            api.query = VALUE
            api.page = PAGE
            api.add_field("ip")
            search_result_set = api.search()
            for search_result in search_result_set
                ...

            # Using get:
            for search_result in api.get(query=VALUE, fields=["ip"], max_results=250):
                ...

            # Treating CensysSearch as an iterable:
            api.query = VALUE
            api.page = PAGE
            api.add_field("ip")
            for search_result in search_result_set:
                ...
    """

    DEFAULT_PAGE = 1
    """The default page number"""

    def __init__(self, index):
        """
        Create a new access object for the search endpoint using the given index.

        :param index: The Censys index to be used (an member of the Index enumeration)
        """
        super(CensysSearch, self).__init__(Endpoint.SEARCH, index)
        self._index = index
        self._query = None
        self._page = self.DEFAULT_PAGE
        self._fields = set()

    @property
    def query(self):
        """
        Get the query value to be sent to the search API.

        :return: The query value
        """
        return self._query

    @query.setter
    def query(self, value):
        """
        Set the query value to be sent to the search API.

        :param value: The query value
        :return: This method returns no values
        """
        self._query = value
        LOGGER.debug("Censys %s search query updated: %s", self.index.name, self._query)

    @property
    def page(self):
        """
        Get the page number to be retrieved from the search API.

        :return: The page number
        """
        return self._page

    @page.setter
    def page(self, value):
        """
        Set the page number to be retrieved from the search API.

        :param value: The page number
        :return: This method returns no values
        """
        self._page = value
        LOGGER.debug("Censys %s search page updated: %d", self.index.name, self._page)

    @property
    def fields(self):
        """
        Get the set of fields to be retrieved in results from the search API.

        Note that this method does NOT return a reference to the internal set.

        :return: The set of field names
        """
        return set(self._fields)

    @fields.setter
    def fields(self, value):
        """
        Set the fields to be retrieved in results from the search API.

        Use this property setter to REPLACE the existing fields with a new iterable of fields.

        :param value: The iterable of field names
        :return: This method returns no values
        :raises ValueError: If one or more fields are invalid
        """
        self._fields = set() if value is None else {self._validate_field(field) for field in value}
        LOGGER.debug("Censys %s search fields updated: %s", self.index.name, self._fields)

    def add_field(self, field):
        """
        Add a field to be retrieved in results from the search API.

        Use this method to ADD a new field to the existing set of fields

        :param field: The field to be retrieved
        :return: This method returns no values
        """
        self._fields.add(self._validate_field(field))

    def remove_field(self, field):
        """
        Remove a field from those to be retrieved in results from the search API.

        :param field: The field to be removed
        :return: This method returns no values
        """
        self._fields.remove(field)

    def call(self, query, page, *fields):
        """
        Call the Censys search API.

        This method ignores the currently configured query, page, and field properties of this instance.  Use 'search'
        to use those properties.

        When calling this method, you may specify fields variadically.  If you have fields in a list, you should be sure
        to unpack them when calling this method.  Here are two examples:
            with CensysSearch(index) as api:
                search_result_set = api.call(query, page, "field1", "field2")
                # OR
                fields = ["field1", "field2"]
                search_result_set = api.call(query, page, *fields)

        :param query: The value for which to search
        :param page: The page number of results to be retrieved
        :param fields: The iterable of field names to be retrieved (optional)
        :return: The SearchResult if successful
        :raises SearchException: If unsuccessful
        """
        fields = set() if fields is None else {self._validate_field(field) for field in fields}
        value = escape(query)
        data = collections.OrderedDict()
        data["query"] = value
        data["page"] = page
        data["fields"] = list(fields)
        result = self._do_call(HttpMethod.POST, params=None, data=data)
        if isinstance(result, ErrorResult):
            raise SearchException(result)
        return SearchResultSet(self.index, result.code, result.raw)

    def search(self):
        """
        Call the search API according to the currently configured properties of this instance.

        This is a convenience method for calling 'call' that uses the properties configured for this instance.  The
        following examples demonstrate the use of 'call' vs. the use of 'search.'
            # Using search:
            with CensysSearch(index) as api:
                api.api_id = ...
                api.api_secret = ...
                api.query = value,
                api.page = 1
                api.add_field("ip")
                for search_result in api.search():
                    ...

            # Using call:
            with CensysSearch(index) as api:
                api.api_id = ...
                api.api_secret = ...
                for search_result in api.call(value, 1, "ip")
                    ...

        There is also the similar 'generator' convenience method that will iterate up to a certain maximum number of
        results.

        :return: A SearchResultSet, if successful
        :raises SearchException: If unsuccessful
        """
        return self.call(self.query, self.page, *self.fields)

    def get(self, query=None, fields=None, max_results=100, sleep=0, start_page=1):
        """
        A generator to retrieve up to a maximum number of results.

        This method is a generator that yields SearchResult instances.

        :param query: The value for which to search, or None to use the query property of this instance
        :param fields: The fields to be retrieved (a list, or None to use the fields property of this instance)
        :param max_results: The maximum number of results to be obtained
        :param sleep: The length of time to sleep between pages, in seconds (a positive integer or float)
        :param start_page: The starting page number (a positive integer)
        :return:
        """
        result_fields = fields or self.fields
        cap = max_results or sys.maxsize
        LOGGER.debug("Using cap: %d", cap)
        value = query or self.query
        page = start_page
        max_page = -1
        count = 0
        while count < cap:
            if page == max_page:
                LOGGER.debug("Maximum page retrieved")
                break
            if page > start_page and sleep > 0:
                time.sleep(sleep)
            LOGGER.debug("Retrieving search results page %d", page)
            result_set = self.call(value, page, *result_fields)
            previous_max_page = max_page
            max_page = result_set.total_pages
            LOGGER.debug("Total pages is now %d (was %d)", max_page, previous_max_page)
            LOGGER.debug("Page %d contains %d result(s)", result_set.current_page, len(result_set))
            for result in result_set:
                count += 1
                yield result
                if count == cap:
                    break
            page += 1
        LOGGER.debug("Generator complete")

    def __iter__(self):
        for search_result in self.search():
            yield search_result

    def _validate_field(self, field):
        """
        Check that a field is valid for this search index and raise a ValueError if not.

        :param field: The field to be checked
        :return: The field (if successful)
        :raises ValueError: If the field is not valid
        """
        if not self._is_field_valid(field):
            msg = "Invalid field for %s/%s: %s" % (self.endpoint.name, self.index.name, field)
            LOGGER.error(msg)
            raise ValueError(msg)
        return field

    def _is_field_valid(self, field):
        """
        Query whether a field is valid for this access object.

        The default implementation always returns True.  Subclasses should override this if they provide addditional
        field validation.

        :param field: The field to be checked
        :return: True if the field is valid, otherwise False
        """
        return True
