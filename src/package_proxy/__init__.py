import os

if os.environ.get("PACKAGE_PROXY_TARGET") is not None:
    import package_proxy.client
else:
    import package_proxy.server