from typing import Dict, NewType

# WebsiteName = NewType('WebsiteName', str)
# xpath related types
Xpath = NewType("Xpath", str)
XpathTextValue = NewType("XpathTextValue", str)
XpathDict = NewType("XpathDict", Dict[XpathTextValue, Xpath])

# cookie related types
CookieKey = NewType("CookieKey", str)
Cookies = NewType("Cookies", str)
CookiesDict = NewType("CookiesDict", Dict[CookieKey, Cookies])


CurrentPage = NewType("CurrentPage", int)
TotalPages = NewType("TotalPages", int)
# Page = NewType('Page', int)

JobApplication = NewType("JobApplication", dict)
