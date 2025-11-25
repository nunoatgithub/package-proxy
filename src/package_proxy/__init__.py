import os

PACKAGE_PROXY_TARGET ="PACKAGE_PROXY.TARGET"
PACKAGE_PROXY_API ="PACKAGE_PROXY.API"

if os.environ.get(PACKAGE_PROXY_TARGET) is not None:
    import package_proxy.client
else:
    import package_proxy.server