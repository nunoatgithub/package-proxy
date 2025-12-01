Too many important issues with the idea of a generic package-proxy, one that would seamlessly interconnect two interpreters running potentially different version of pyhton
- there is not one universally applicable serialization mechanism that works across python versions for all types of objects. specific serializers for different parts of the data surface would need to be provided.
- inefficient contract, forces too much conversation to resolve the simple local equivalent operations it tries to emulate, like a simple assignment for instance
- getters for fields that were never instantiated on the client side, require the dynamic transformation of that object in a tree of proxies on the server side, many of them new
- setters require the server to dereference the proxy objects embedded in the attributes of the received object, into real objects, otherwise the real system will need to dereference those too, when processing them
- proxy.__dict__ exposes the proxyid on the client side
