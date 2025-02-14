import time
from coapthon import defines
from coapthon.messages.message import Message
from coapthon.messages.response import Response

__author__ = 'Giacomo Tanganelli'
__version__ = "2.0"


class RequestLayer(object):
    """
    Handles the Request Layer functionality.
    """
    def __init__(self, parent):
        """
        Initialize a Request Layer.

        :type parent: coapserver.CoAP
        :param parent: the CoAP server
        """
        self._parent = parent

    def handle_request(self, request):
        """
        Handles requests.

        :param request: the request
        :return: the response
        """
        host, port = request.source
        key = hash(str(host) + str(port) + str(request.mid))
        if key not in self._parent.received:
            if request.blockwise:
                # Blockwise
                last, request = self._parent.blockwise_layer.handle_request(request)
                self._parent.received[key] = (request, time.time())
                return request
            else:
                self._parent.received[key] = (request, time.time())
                return request
        else:
            request, timestamp = self._parent.received.get(key)
            request.duplicated = True
            self._parent.received[key] = (request, timestamp)
            try:
                response, timestamp = self._parent.sent.get(key)
            except TypeError:
                response = None
            if isinstance(response, Response):
                return response
            elif request.acknowledged:
                ack = Message.new_ack(request)
                return ack
            elif request.rejected:
                rst = Message.new_rst(request)
                return rst
            else:
                # The server has not yet decided, whether to acknowledge or
                # reject the request. We know for sure that the server has
                # received the request though and can drop this duplicate here.
                return None

    def process(self, request):
        """
        Processes a request message.

        :param request: the request
        :return: the response
        """
        method = defines.codes[request.code]
        if method == 'GET':
            response = self.handle_get(request)
        elif method == 'POST':
            response = self.handle_post(request)
        elif method == 'PUT':
            response = self.handle_put(request)
        elif method == 'DELETE':
            response = self.handle_delete(request)
        else:
            response = None
        return response

    def handle_put(self, request):
        """
        Handles a PUT request

        :param request: the request
        :return: the response
        """
        response = Response()
        response.destination = request.source
        path = str("/" + request.uri_path)
        try:
            resource = self._parent.root[path]
        except KeyError:
            resource = None
        if resource is None:
            response = self._parent.send_error(request, response, 'NOT_FOUND')
            return response

        # Update request
        response = self._parent.resource_layer.update_resource(request, response, resource)
        return response

    def handle_post(self, request):
        """
        Handles a POST request.

        :param request: the request
        :return: the response
        """
        path = str("/" + request.uri_path)
        response = Response()
        response.destination = request.source
        # Create request
        response = self._parent.resource_layer.create_resource(path, request, response)
        return response

    def handle_delete(self, request):
        """
        Handles a DELETE request.

        :param request: the request
        :return: the response
        """
        path = str("/" + request.uri_path)
        try:
            resource = self._parent.root[path]
        except KeyError:
            resource = None

        response = Response()
        response.destination = request.source
        if resource is None:
            # Create request
            response = self._parent.send_error(request, response, 'NOT_FOUND')
            return response
        else:
            # Delete
            response = self._parent.resource_layer.delete_resource(request, response, path)
            return response

    def handle_get(self, request):
        """
        Handles a GET request.

        :param request: the request
        :return: the response
        """
        path = str("/" + request.uri_path)
        response = Response()
        response.destination = request.source
        if path == defines.DISCOVERY_URL:
            response = self._parent.resource_layer.discover(request, response)
        else:
            try:
                resource = self._parent.root[path]
            except KeyError:
                resource = None
            if resource is None:
                # Not Found
                response = self._parent.send_error(request, response, 'NOT_FOUND')
            else:
                response = self._parent.resource_layer.get_resource(request, response, resource)
        return response