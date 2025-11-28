import os

PACKAGE_PROXY_TARGET ="PKG_PROXY_TARGET"
PACKAGE_PROXY_API ="PKG_PROXY_API"
PACKAGE_PROXY_API_LOGLEVEL ="PKG_PROXY_API_LOGLEVEL"

if os.environ.get(PACKAGE_PROXY_TARGET) is not None:
    import package_proxy.client
else:
    import package_proxy.server