import copy
import logging

from scale_client import networks
from scale_client.core.threaded_application import ThreadedApplication
from scale_client.util import uri

logging.basicConfig()
log = logging.getLogger(__name__)

import coapthon.defines
from coapthon.server.coap import CoAP as CoapthonServer
from coapthon.resources.resource import Resource as CoapResource

# HACK: the version of CoAPthon that we're using has a bug where it overwrites our
# logging configuration, so we just reformat it.
from scale_client.util.defaults import set_logging_config
from scale_client.networks.util import DEFAULT_COAP_PORT, coap_code_to_name

set_logging_config()

from scale_client.core.sensed_event import SensedEvent


class CoapServer(ThreadedApplication):
    """
    This special Application runs a CoAP server so that other modules may use it to store CoAP resources
    for external nodes (e.g. those running a CoapSensor) to GET/POST/PUT/etc.  It allows for
    defining custom CoapResources that can handle application-specific logic.

    NOTE: much of the logic for how the server interacts with external requests resides in the CoapResource classes.
    They actually handle exposing APIs, calling callbacks when they're activated, and managing SensedEvents from
    remote sources.
    """

    _DEFAULT_COAP_SERVER_NAME = '__default_scale_coap_server__'

    def __init__(self, broker,
                 events_root=None,
                 server_name=_DEFAULT_COAP_SERVER_NAME,
                 hostname="0.0.0.0",
                 port=DEFAULT_COAP_PORT,
                 multicast=False,
                 **kwargs):
        """
        Simple constructor.  When on_start is called, the server will actually be run.
        :param broker: internal scale_client broker
        :param events_root: if specified, will allow remote clients to store events at this root
        :param server_name: the user-assigned name for this server so as to distinguish between multiple running ones
        (if unspecified only a single server without an explicit name can be run)
        :param hostname: hostname/IP address to bind server to
        :param port: port to run server on
        :param multicast: optionally enable handling multicast requests
        :param kwargs:
        """
        super(CoapServer, self).__init__(broker=broker, **kwargs)

        self._server = None  # Type: coapthon.server.coap.CoAP
        self._events_root = events_root

        self._hostname = hostname
        self._port = port
        self._multicast = multicast
        if multicast and hostname != coapthon.defines.ALL_COAP_NODES:
            log.warning("underlying CoAPthon library currently only supports the ALL_COAP_NODES multicast address of %s" % coapthon.defines.ALL_COAP_NODES)

        self._server_running = False
        self._is_connected = False

        # Users need to access the server in their other CoAP-based modules,
        # so we keep a registry of them indexed by the user-assigned name.
        # XXX: we just set this as an object on the broker instance so it doesn't persist across ScaleClients (mostly for testing)
        # TODO: use Application.name and a registration service for this
        try:
            instances = broker._coap_server_instances
        except AttributeError:
            instances = broker._coap_server_instances = dict()

        # Register this server as a currently-running instance
        if server_name in instances:
            raise ValueError("A CoapServer with server_name %s already exists!  Aborting creation of the second one..." % server_name)
        instances[server_name] = self
        self._server_name = server_name

    def __run_server(self):
        log.debug("starting CoAP server at IP:port %s:%d" % (self._hostname, self._port))

        try:
            self._server = CoapthonServer(self._hostname, self._port, self._multicast)
        except TypeError:
            # coapthon 4.0.2 has a different constructor API
            self._server = CoapthonServer((self._hostname, self._port), self._multicast)

        if self._events_root is not None:
            root_event = self.make_event(source=self._events_root, data='root of SCALE events resources', priority=1)
            self.store_event(root_event, self._events_root)

        self._server_running = True
        self._notify_running()

        # Listen for remote connections GETting data, etc.
        self._server.listen()

    # CIRCUITS-SPECIFIC: not entirely, but may be broker by switch to another runtime...
    # TODO: document this!
    from scale_client.core.sensed_event import Event
    class CoapServerRunning(Event):
        pass

    def _notify_running(self):
        """Publishes an event to let other apps know that this server is now up and running.
        They should be careful to not use this server until this notification!"""
        event = self.CoapServerRunning(self)
        self.publish(event)

    def on_stop(self):
        self._server.close()
        self._server_running = False
        super(CoapServer, self).on_stop()

    def on_start(self):
        self.run_in_background(self.__run_server)

    def store_event(self, event, path=None, disable_post=False, disable_put=False, disable_delete=False):
        """
        Stores the event as a resource at the given path in the CoAP server.
        A SensedEventCoapResource stored this way will be exposed externally at the given CoAP
        path so that GET, PUT, etc. can be called on it unless you disable them through
        the parameters.

        :param event:
        :type event: scale_client.core.sensed_event.SensedEvent
        :param path: the path at which the event should be stored (default=event.get_type())
        :param disable_post:
        :param disable_put:
        :param disable_delete:
        :return:
        """

        if path is None:
            path = event.event_type
        # XXX: Ensure path is formatted properly for CoAP's internals
        if not path.startswith('/'):
            path = '/' + path
        if path.endswith('/'):
            path = path[:-1]

        assert isinstance(self._server, CoapthonServer)  # for type annotation

        # Update the resource if it exists and notify possible observers (unfortunately,
        # CoAPthon doesn't have a clean way to do exactly this since most of the lower APIs
        # assume request/response/transaction objects).
        # Furthermore, we don't want the render_PUT API to fire as we have it currently
        # since that would publish the event internally again.
        try:
            res = self._server.root[path]
            assert isinstance(res, SensedEventCoapResource)
            res.event = event
            self._server.notify(res)
            log.debug("updated resource at path: %s" % path)

        # Create the resource since it didn't exist.
        # We add callbacks so modifications to the resource are published internally.
        except KeyError:
            # post_cb = None if disable_post else lambda req, res: self.publish(res.event)
            # put_cb = None if disable_put else lambda req, res: self.publish(res.event)
            def __default_event_callback(request, resource):
                """
                Default callback to enable logging and internally publish new events.
                :type request: coapthon.messages.request.Request
                :return:
                """
                log.debug("new event received via %s: %s" % (coap_code_to_name(request.code), resource.event))
                return self.publish(resource.event)

            post_cb = None if disable_post else __default_event_callback
            put_cb = None if disable_put else __default_event_callback

            new_resource = SensedEventCoapResource(event, name=event.event_type,
                                                   get_callback=lambda x, y: y,  # always enabled
                                                   post_callback=post_cb, put_callback=put_cb,
                                                   delete_callback=None if disable_delete else lambda x, y: True)
            self.store_resource(path, resource=new_resource)

    def store_resource(self, path, resource):
        """
        Stores a CoapResource in the server at the given path.
        :param path:
        :param resource:
        :return:
        """

        res = self._server.add_resource(path, resource)
        log.debug("%s added resource to path: %s" % ('successfully' if res else 'unsuccessfully', path))

    def is_running(self):
        return self._server_running

    def register_api(self, path, name, get_callback=None, put_callback=None,
                     post_callback=None, delete_callback=None, error_callback=None,
                     observable=False, allow_children=False, visible=True):
        """
        Registers the specified callbacks at the given path to create a custom API.  This will create a Resource
        at that path with the given properties so that a CoAP client can GET/PUT/POST/DELETE it and have the
        corresponding callback fired in response.  If no callback is specified for that method, it returns a
        METHOD_NOT_ALLOWED response.  If an exception is encountered, error_callback is called if specified
        where the default is to simply log the error.

        CALLBACK DEFINITIONS:
        The callbacks should accept the CoAP Request object and the relevant resource as parameters.  The
        error_callback should additionally accept the exception encountered as its third parameter.  If you
        can recover from the error, simply return the resource from the callback after doing so.  Otherwise,
        raise an exception noting that raising NotImplementedError will return a METHOD_NOT_ALLOWED response.
        Thus the callbacks have the following form:

        callback(coapthon.messages.request.Request, ScaleCoapResource, [Exception]) -> ScaleCoapResource

        :param path: full pathname e.g. /sensors/temp0/interval
        :param name: name of the API endpoint (useful when a client does a DISCOVER request)
        :param get_callback:
        :param put_callback:
        :param post_callback:
        :param delete_callback:
        :param error_callback:
        :param observable:
        :param allow_children:
        :param visible:
        :return: the newly added resource
        """
        # TODO: maybe we should use the advanced interface, optionally the separate one, in order to modify response?

        if error_callback is None:
            error_callback = lambda req, res, err: log.error("coap api error with resource %s while answering request %s:\n %s" % (res, req, err))
        res = ScaleCoapResource(name, get_callback=get_callback, put_callback=put_callback,
                                post_callback=post_callback, delete_callback=delete_callback,
                                error_callback=error_callback,
                                coap_server=self._server, visible=visible,
                                observable=observable, allow_children=allow_children)
        self.store_resource(path, res)
        return res


# Just for type annotations
from coapthon.messages.request import Request


class ScaleCoapResource(CoapResource):
    """
    Exposes an API through a CoAP Resource with configurable callbacks for the GET/POST/etc. methods.
    """

    def __init__(self, name, get_callback=None, put_callback=None, post_callback=None,
                 delete_callback=None, error_callback=None, *args, **kwargs):
        super(ScaleCoapResource, self).__init__(name, *args, **kwargs)
        self._get_cb = get_callback
        self._put_cb = put_callback
        self._post_cb = post_callback
        self._del_cb = delete_callback
        self._err_cb = error_callback

        # TODO: accept configurable content types?
        self.content_type = coapthon.defines.Content_types["application/json"]


    def render_GET(self, request):
        """
        :param request:
        :type request: Request
        :return:
        """
        if self._get_cb is None:
            raise NotImplementedError
        try:
            self._get_cb(request, self)
        except Exception as e:
            if self._err_cb is not None:
                self._err_cb(request, self, e)
            else:
                log.error("unhandled error: %s" % e)
                raise e

        return self

    # TODO: how to do access control for these???
    def render_PUT(self, request):
        """
        :param request:
        :type request: Request
        :return:
        """
        self.edit_resource(request)
        if self._put_cb is None:
            raise NotImplementedError
        try:
            self.edit_resource(request)
            self._put_cb(request, self)
        except Exception as e:
            if self._err_cb is not None:
                self._err_cb(request, self, e)
            else:
                log.error("unhandled error: %s" % e)
                raise e
        return self

    def render_POST(self, request):
        """
        :param request:
        :type request: Request
        :return:
        """
        if self._post_cb is None:
            raise NotImplementedError
        try:
            # XXX: rather than creating a new resource and passing in all our
            # callbacks, attributes, etc. as args to it, we just do a shallow copy instead.
            # NOTE: can't do deepcopy as it can cause an error due to copying thread locks.
            res = copy.copy(self)
            res = self.init_resource(request, res)
            self._post_cb(request, res)
            return res
        except Exception as e:
            if self._err_cb is not None:
                self._err_cb(request, self, e)
            else:
                log.error("unhandled error: %s" % e)
                raise e


    def render_DELETE(self, request):
        """
        :param request:
        :type request: Request
        :return: a boolean
        """
        if self._del_cb is None:
            raise NotImplementedError
        try:
            self._del_cb(request, self)
        except Exception as e:
            if self._err_cb is not None:
                self._err_cb(request, self, e)
            else:
                log.error("unhandled error: %s" % e)
        return True


class SensedEventCoapResource(ScaleCoapResource):
    """
    Represents a SensedEvent stored as a CoAP Resource
    """

    def __init__(self, event, name, *args, **kwargs):
        """
        :param event:
        :type event: scale_client.core.sensed_event.SensedEvent
        :param name: name of the Resource (default=event.__class__.__name__)
        """
        if name is None:
            name = event.__class__.__name__

        super(SensedEventCoapResource, self).__init__(name, *args, **kwargs)
        self._event = self.payload = None  # just for warnings
        self.event = event

    @staticmethod
    def extract_event(request):
        """
        Extracts a SensedEvent from the payload of the request.  Tries to convert it to a remote event if it was
        left as a local one by setting the host/port/protocol.
        :param request:
        :type request: Request
        :return: the SensedEvent
        :rtype: SensedEvent
        """
        event = SensedEvent.from_json(request.payload)
        host, port = request.source
        try:
            # TODO: specify coaps if this event came through an encrypted channel?
            networks.util.process_remote_event(event, hostname=host, port=port, protocol='coap')
            # save the local resource URI so we know where exactly it entered our local client
            event.metadata['local_resource_uri'] = uri.build_uri(relative_path=request.uri_path)
            # QUESTION: should we do something with uri_query?  probably not used in a PUT/POST request...
        except BaseException as e:
            log.error("error during converting local source to remote source in event extracted from CoAP request: %s" % e)
        return event

    @property
    def event(self):
        return self._event

    @event.setter
    def event(self, ev):
        """
        Updates this resource to reflect this new event.
        :param ev:
        :type ev: SensedEvent
        """
        self._event = ev
        self.payload = self.event.to_json()

    def edit_resource(self, request):
        super(SensedEventCoapResource, self).edit_resource(request)
        # TODO: error handling / testing?
        # try:
        self.event = self.extract_event(request)
        #     return event
        # except ValueError:
        #     log.error("Failed to decode SensedEvent from payload: %s" % request.payload)

    def init_resource(self, request, res):
        super(SensedEventCoapResource, self).init_resource(request, res)
        # ensure the payload is properly set to the SensedEvent
        res.edit_resource(request)
        # not sure why this path isn't set elsewhere in coapthon...
        res.path = request.uri_path
        return res
