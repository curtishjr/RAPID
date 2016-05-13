"""
Core functionality for the Censys API module
"""
import abc
import json
import logging
import requests
import os
import sys

if sys.version_info[0] > 2:
    # Python 3.x Import Statements
    import enum
else:
    # Python 2.x Import Statements
    import enum34 as enum


LOGGER = logging.getLogger(__name__)
"""The logger for this module"""


class __EnumWithValue(enum.Enum):
    """
    A base class for enumerations used in URL construction.

    Each enumeration has a "value" read-only property which should be used when constructing the URLs.
    """

    def __init__(self, value):
        """
        Create a new enumerated value.

        :param value: The endpoint value used in URL construction
        """
        self.__value = value

    @property
    def value(self):
        """
        Get the URL construction value for this endpoint.

        :return: The value to be used in URL construction
        """
        return self.__value


@enum.unique
class Endpoint(__EnumWithValue):
    """
    An enumeration of Censys endpoints supported by this module
    """

    SEARCH = "search"
    """The search API"""


@enum.unique
class Index(__EnumWithValue):
    """
    An enumeration of the Censys indices supported by this module
    """

    CERTIFICATES = "certificates"
    """The certificates index"""

    IPV4 = "ipv4"
    """The IPv4 index"""

    WEBSITES = "websites"
    """The websites index"""


@enum.unique
class HttpMethod(enum.Enum):
    """
    An enumeration of HTTP methods supported by the Censys module
    """

    GET = 10
    """The HTTP GET method"""

    POST = 20
    """The HTTP POST method"""


class CensysResult(object):
    """
    A base class for results from a Censys API call
    """

    def __init__(self, code, raw):
        """
        Create a new result object.

        :param code: The HTTP status code returned from the API
        :param raw: The raw response JSON returned by the API
        """
        self._code = code
        self._raw = raw

    @property
    def code(self):
        """
        Get the HTTP status code returned from the API.

        :return: The HTTP status code
        """
        return self._code

    @property
    def raw(self):
        """
        Get the raw response JSON returned by the API.

        :return: The raw response JSON
        """
        return self._raw

    def __repr__(self):
        return "%s(%s, %s)" % (type(self).__name__, self.code, self.raw)

    def __str__(self):
        return CensysResult.__repr__(self)


class ErrorResult(CensysResult):
    """
    An error response from a Censys API call.

    In addition to the properties available from CensysResult, instances of this class also make available a 'message'
    property that is the error message.  This class also defines a better human-readable string version of instances.
    """

    def __init__(self, code, raw):
        """
        Create a new error response.

        :param code: The error code from the API
        :param raw: The raw response JSON from the API
        """
        super(ErrorResult, self).__init__(code, raw)
        if LOGGER.isEnabledFor(logging.WARN) and "error_code" in raw:
            error_code = raw["error_code"]
            if error_code != code:
                LOGGER.warn("Response status code (%d) does not match error code in response content (%d)",
                            code,
                            error_code)
        self._message = raw["error"]

    @property
    def message(self):
        """
        Get the error message for this result.

        :return: The error message
        """
        return self._message

    def __str__(self):
        # Example: "(403): Unauthorized.  You must authenticate with an API ID and secret."
        return "(%d): %s" % (self.code, self.message)


class CensysException(Exception):
    """
    The base class for all exceptions thrown by the Censys module.
    """
    pass


class CensysResultException(CensysException):
    """
    The base class for exceptions resulting from error responses from a Censys API call.

    Exceptions of subclasses of this type mean that actually calling the API was successful, but the API returned an
    error response.  As a result, the constructor for this exception takes an ErrorResult instance to construct the
    exception, which has both a code and message property.
    """

    def __init__(self, error_result):
        """
        Create a new exception.

        :param error_result: The ErrorResult instance
        """
        self._code = error_result.code
        self._message = error_result.message
        message = "Error (%d): %s" % (error_result.code, error_result.message)
        super(CensysResultException, self).__init__(message)

    @property
    def code(self):
        """
        Get the error code returned from the Censys API.

        :return: The error code
        """
        return self._code

    @property
    def message(self):
        """
        Get the error detail message returned from the Censys API.

        :return: The error detail message
        """
        return self._message

    def __str__(self):
        # Example: "(403): Unauthorized.  You must authenticate with an API ID and secret."
        return "(%d): %s" % (self.code, self.message)


class CensysApiAccessObject(object):
    """
    The abstract base class for all Censys API access in this module.

    Subclasses must implement the 'call' method.

    By default, new objects use the default time and try to obtain the API ID and API secret value from OS
    environment variables (CENSYS_API_ID and CENSYS_API_SECRET, respectively).   Users may override these values using
    the appropriate property setter

    Censys API access objects should be closed when no longer in use.  They support use in with statements but may also
    be closed via the 'close' method.
    """

    __metaclass__ = abc.ABCMeta

    BASE_URL = "https://www.censys.io/api/v1"
    """The base URL for the Censys API"""

    DEFAULT_TIMEOUT = 30
    """The default timeout for calls to the Censys REST API"""

    def __init__(self, endpoint, index):
        """
        Create a new API access object for the given endpoint and index.



        :param endpoint: The Censys endpoint (must be a member of the Endpoint enumeration)
        :param index: The Censys index (must be a member of the Index enumeration)
        """
        self._endpoint = endpoint
        self._index = index
        self._timeout = self.DEFAULT_TIMEOUT
        self._api_id = os.environ.get("CENSYS_API_ID", None)
        self._api_secret = os.environ.get("CENSYS_API_SECRET", None)
        self._session = None
        self.__session_is_invalid = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @abc.abstractmethod
    def call(self, **kwargs):
        """
        Call the Censys API and return a generator over the results.

        This method forms a generator yielding CensysResult objects.  Note that the actual type of the returned object
        may be (and likely is) a subtype of CensysResult--either ErrorResult in the case of an error or another subtype
        specific to the API in use.   An ErrorResult should cause the generator to complete.

        :param kwargs: The arguments to be used to call the API (see subclasses for actual parameters)
        :return: A generator of CensysResult objects (see comments)
        :raises CensysResultException: If the API returned an error result
        :raises CensysException: If another error was encountered
        """
        # Developer Note: Subclasses should generally just need to create the 'params' and 'data' structures and then
        # call self._do_call.   They may optionally need to perform additional processing on the result (i.e. to create
        # an isntance of the appropriate CensysResult subclass).
        raise NotImplementedError("CensysBase subclasses must implement the 'call' method")

    def close(self):
        """
        Close this API access object.

        :return: This method returns no values
        """
        if self._session is not None:
            self._session.close()

    @property
    def endpoint(self):
        """
        Get the endpoint accessed by this API access object.

        :return: The Endpoint enumeration value that identifies the endpoint accessed by this object
        """
        return self._endpoint

    @property
    def index(self):
        """
        Get the index accessed by this API access object

        :return: The Index enumeration value that identifies the index accessed by this object
        """
        return self._index

    @property
    def timeout(self):
        """
        Get the current timeout used when accessing the Censys API.

        :return: The timeout to use when accessing the Censys API, in seconds
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        """
        Set the timeout to be used when accessing the Censys API.

        :param value: The timeout, in seconds
        :return: This method returns no values
        """
        self._timeout = value
        self._invalidate_session()
        LOGGER.debug("Timeout for %s/%s is now %s", self.endpoint.name, self.index.name, self._timeout)

    @property
    def api_id(self):
        """
        Get the API ID used to access the Censys API.

        :return: The API ID (a string or None)
        """
        return self._api_id

    @api_id.setter
    def api_id(self, value):
        """
        Set the API ID used to access the Censys API.

        :param value: The API ID (a string or None)
        :return: This method returns no values
        """
        self._api_id = value
        self._invalidate_session()
        LOGGER.debug("Censys %s/%s now API ID: %s", self.endpoint.name, self.index.name, self._api_id)

    @property
    def api_secret(self):
        """
        Get the API secret value used to access the Censys API.

        :return: The API secret value (a string or None)
        """
        return self._api_secret

    @api_secret.setter
    def api_secret(self, value):
        """
        Set the API secret value used to access the Censys API.

        :param value: The API secret value (a string or None)
        :return: This method returns no values
        """
        self._api_secret = value
        self._invalidate_session()
        LOGGER.debug("Censys %s/%s API secret has been updated", self.endpoint.name, self.index.name)

    def _do_call(self, method, params=None, data=None):
        """
        Perform the actual call to the Censys API.

        This is a helper method available to subclasses to actually perform the API call.

        :param method: The HttpMethod enumeration instance identifying what method should be used when calling the API
        :param params: A dictionary containing key value pairs used as query parameters when constructing the API URL.
        (Use None or an empty dictionary for no query parameters.)
        :param data: A dictionary of the data to be passed (used only for POST calls), or None for no data
        :return: A CensysResult object
        :raises ValueError: If 'method' is not a supported HTTP method
        """
        self._check_session()
        params = params or dict()
        body = None if data is None else json.dumps(data)
        url = self._make_url()
        if method is HttpMethod.POST:
            func = self._session.post
        elif method is HttpMethod.GET:
            func = self._session.get
        else:
            msg = "Invalid/Unsupported HTTP method: %s" % method
            LOGGER.error(msg)
            raise ValueError(msg)
        LOGGER.debug("Censys %s/%s call: %s %s (params: %s, body: %s)",
                     self.endpoint.name,
                     self.index.name,
                     method, url,
                     params,
                     body)
        response = func(url=url, params=params, data=body)
        LOGGER.debug("Censys %s/%s raw response: %s", self.endpoint.name, self.index.name, response)
        code = response.status_code
        response_json = response.json()
        LOGGER.debug("Censys %s/%s call responded %d:\n%s", self.endpoint.name, self.index.name, code, response_json)
        if code == 200:
            return CensysResult(code, response_json)
        LOGGER.warn("Censys error response: %s", response_json)
        return ErrorResult(code, response_json)

    def _make_url(self):
        """
        Create the URL for accessing the Censys API.

        The URL is based upon the endpoint and the index, together with the base URL.

        :return: The URL for accessing the Censys API
        """
        url = "/".join([self.BASE_URL, self.endpoint.value, self.index.value])
        LOGGER.debug("Created Censys URL: %s", url)
        return url

    def _invalidate_session(self):
        """
        Mark the session as invalid.

        This should be used if something has changed that should cause the session to be re-initiated.  Examples include
        changing the authentication (API ID or API secret) or timeout.

        :return: This method returns no values
        """
        self.__session_is_invalid = True

    def _check_session(self):
        """
        Ensure that the internal session is ready for use.

        This method will close an old session if it has been marked as invalid.  Then, if no session is available, it
        will create a new one, which is then available via the self._session member.
        :return:
        """
        if self.__session_is_invalid:
            if self._session is not None:
                self._session.close()
                self._session = None
        if self._session is None:
            self._session = self._make_session()

    def _make_session(self):
        """
        Create a new Requests session object.

        :return: The new session object
        """
        session = requests.Session()
        session.auth = (self.api_id, self.api_secret)
        session.timeout = self.timeout
        session.headers.update({"accept": "application/json, */8"})
        self._test_session(session)
        return session

    def _test_session(self, session):
        """
        Test that the session works properly.

        The default implementation performs no tests.

        :param session: The session to be tested
        :return: This method returns no values
        :raises CensysException: If the session is not valid
        """
        pass
