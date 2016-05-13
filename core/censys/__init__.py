"""
Censys API module.

Only the search usage is actually implemented so far.  The easiest way to use this is to instantiate a
ipv4.CensysIPv4Search, certificates.CensysCertificatesSearch, or websites.CensysWebsitesSearch instance.  Refer to the
documentation for search.CensysSearch for more information on how to use these objects.

Exception Hierarchy:
    Exception
    |
    +- CensysException
       |
       +- CensysResultException

Result Object Heirarchy:
    CensysResult
    |
    +- ErrorResult
    |
    +- SearchResult

API Access Object Hierarchy:
    CensysApiAccessObject
    |
    +- CensysSearch
       |
       +- CensysCertificatesSearch
       |
       +- CensysIPv4Search
       |
       +- CensysWebsitesSearch

Enumerations:
    - HttpMethod: Enumerations of HTTP methods used by CensysApiAccessObject subclasses
    - Endpoint: Enumeration of Censys endpoints (e.g. search)
    - Index: Enumeration of Censys indices (e.g. IPv4, Certificates, etc.)

"""
