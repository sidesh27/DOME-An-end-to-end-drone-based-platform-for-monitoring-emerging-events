# This file intended to hold various helper functions, constants, and eventually a
# registration system for URIs within the scale client.
import socket
import logging
log = logging.getLogger(__name__)

import uritools


# NOTE: underscores not allowed in scheme!
DEFAULT_SCALE_URI_SCHEME = 'scale-local'
# we somewhat support the idea of namespaces so that someone could manage URIs for their own purposes
# without interfering in the core scale client URI namespace
DEFAULT_SCALE_URI_NAMESPACE = 'scale'
DEFAULT_SCALE_URI_PATH_BASE = DEFAULT_SCALE_URI_NAMESPACE

NULL_REMOTE_URI_HOST = "0.0.0.0"


def build_uri(scheme=DEFAULT_SCALE_URI_SCHEME, namespace=DEFAULT_SCALE_URI_NAMESPACE,
              path=None, relative_path=None, **kwargs):
    """
    Build a URI from the specified parameters.  If you don't specify path to create a complete path,
     you can specify a relative path to have it build one for you on top of the optionally-specified
    namespace that helps avoid collision with core scale client URIs.

    NOTE: these parameters are just for conventional purposes and don't do any significant
     namespace separation, management, or API exposure currently...

    :param path: an absolute URI path (will skip over the namespace and relative one when present)
    :param scheme: first part of the URI identifying the protocol/scheme/etc. (default is scale-specific for local use)
    :param namespace: prepended on relative path (default is scale-specific); the scale core may handle the different namespaces separately
    :param relative_path: e.g. your/path/goes/here but note that you are responsible for managing this path hierarchy!
    :param kwargs: all these are passed to uritools.uricompose
    :return:
    """

    # First build up the path we'll use
    parts_to_use = []

    if not path and not relative_path:
        raise ValueError("must specify at least a component path (can be a simple name string) or ")
    elif not path and relative_path:
        if namespace:
            parts_to_use.append(namespace)
        parts_to_use.append(relative_path)
    else:
        parts_to_use.append(path)
        # TODO: check for ignored args and warn user? only when logging enabled...
        # if relative_path:

    # First, trim any leading/trailing slashes
    final_parts = []
    for part in parts_to_use:
        while part.startswith('/'):
            part = part[1:]
        while part.endswith('/'):
            part = part[:-1]
        final_parts.append(part)
    # Note that we enforce a leading / for the path!
    path = '/' + '/'.join(final_parts)

    return uritools.uricompose(scheme=scheme, path=path, **kwargs)

# TODO: get_namespace_from_path


def parse_uri(uri):
    """
    Returns a parsed object for the given URI that you can further extract info from:
    gethost, getpath, getport, getquerydict, etc.
    :param uri:
    :return:
    :rtype: uritools.SplitResult
    """
    return uritools.urisplit(uri)


def get_remote_uri(local_uri, protocol=None, host=None, port=None):
    """
    Converts the specified local_uri into a remote one such that remote entities can contact the entity referenced
    by local_uri.  The IP address component, if any, should be publicly accessible.  If the component is not
    publicly accessible (i.e. has no external-facing API), we build a default URI using the specified protocol and host.
    This is particularly useful for setting the source of a SensedEvent so that remote subscribers
    can contact the responsible entity for more information or configurations.

    NOTE: current implementation simply replaces the 'scheme' component with protocol and adds the host/port.  It makes
    no attempt to verify that host is publicly-routable!  Expect the implementation to change significantly at a
    later date in order to address these issues, look up the component in the URI registry, etc.

    NOTE: you must specify either the protocol or port!  Otherwise, the resulting URI cannot identify the protocol

    :param local_uri: of the component we're building a remote URI for
    :param protocol: default protocol to use if none found for the specified component
    :param host: default host address to use if none found for the specified component
    :param port: default port number to use if none found for the specified component
    :return:
    """

    # extract the required fields from the specified URI when possible
    local_uri = parse_uri(local_uri)
    if local_uri.port:
        port = local_uri.port
    if local_uri.scheme and local_uri.scheme != DEFAULT_SCALE_URI_SCHEME:
        protocol = local_uri.scheme
    if local_uri.host and is_host_known(_host=local_uri.host):
        host = local_uri.host
    elif host is None:
        hostname = socket.gethostname()
        if is_host_known(_host=hostname):
            host = socket.gethostbyname(hostname)
        else:
            host = NULL_REMOTE_URI_HOST

    if not protocol and not port:
        raise ValueError("must specify at least either the protocol or port to build a remote URI!"
                         " only got protocol=%s and port=%s" % (protocol, port))
    return build_uri(scheme=protocol, namespace='', path=local_uri.path, host=host, port=port)


LOCAL_URI_SCHEMES = (DEFAULT_SCALE_URI_SCHEME, 'file',)

def is_remote_uri(_uri):
    """Returns true if the specified URI points to a remote entity i.e. it doesn't specify a remote protocol"""
    uri_scheme = parse_uri(_uri).getscheme()
    if uri_scheme is None or uri_scheme in LOCAL_URI_SCHEMES:
        return False
    return True

UNKNOWN_HOST_VALUES = (None, NULL_REMOTE_URI_HOST, 'localhost', '127.0.0.1')

def is_host_known(_uri=None, _host=None):
    """Returns true if the specified URI's host has been specified i.e. is included in the URI and isn't
    a non-addressable value e.g. nonsense string, null route, etc.
    :param _uri: the URI to be inspected
    :param _host: the already-parsed hostname if you do not specify _uri
    """
    if _uri is not None:
        _host = parse_uri(_uri).host
    host_unknown = _host in UNKNOWN_HOST_VALUES
    return not host_unknown
