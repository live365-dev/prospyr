# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import functools
import re

import requests
from urlobject import URLObject
from urlobject.path import URLPath

from prospyr.exceptions import MisconfiguredError

_connections = {}
_default_url = 'https://api.prosperworks.com/developer_api/'


def connect(email, token, url=_default_url, name='default'):
    """
    Create a connection to ProsperWorks using credentials `email` and `token`.

    The new connection is returned. It can be retrieved later by name using
    `prospyr.connection.get`. By default the connection is named 'default'. You
    can provide a different name to maintain multiple connections to
    ProsperWorks.
    """
    if name in _connections:
        existing = _connections[name]
        raise ValueError(
            '`{name}` is already connected using account '
            '"{email}"'.format(name=name, email=existing.email)
        )

    validate_url(url)

    conn = Connection(url, email, token)
    _connections[name] = conn
    return conn


def get(name='default'):
    """
    Fetch a ProsperWorks connection by name.

    If you did not argue a name at connection time, the connection will be
    named 'default'.
    """
    try:
        return _connections[name]
    except KeyError:
        if name == 'default':
            msg = ('There is no default connection. '
                   'First try prospyr.connect(...)')
        else:
            msg = ('There is no connection named "{name}". '
                   'First try prospyr.connect(..., name="{name}")')
            msg = msg.format(name=name)
        raise MisconfiguredError(msg)


def validate_url(url):
    """
    True or MisconfiguredError if `url` is invalid.
    """
    uo = URLObject(url)
    if not uo.scheme or uo.scheme not in {'http', 'https'}:
        raise MisconfiguredError('ProsperWorks API URL `%s` must include a '
                                 'scheme (http, https)' % url)
    if not uo.hostname:
        raise MisconfiguredError('ProsperWorks API URL `%s` must include a '
                                 'hostname' % url)
    if re.search('/v\d', url):
        raise MisconfiguredError('ProsperWorks API URL `%s` should not '
                                 'include a "version" path segment' % url)

    return True


def url_join(base, *paths):
    """
    Append `paths` to `base`. Path resets on each absolute path.

    Like os.path.join, but for URLs.
    """
    if not hasattr(base, 'add_path'):
        base = URLObject(base)

    for path in paths:
        path = URLPath(path)
        return base.add_path(path)
    return base


class Connection(object):

    _resources = None

    def __init__(self, url, email, token, version='v1'):
        self.session = Connection._get_session(email, token)
        self.email = email
        self.base_url = URLObject(url)
        self.api_url = self.base_url.add_path_segment(version)

    def http_method(self, method, url, *args, **kwargs):
        """
        Send HTTP request with `method` to `url`.
        """
        method_fn = getattr(self.session, method)
        return method_fn(url, *args, **kwargs)

    def build_absolute_url(self, path):
        """
        Resolve relative `path` against this connection's API url.
        """
        return url_join(self.api_url, path)

    @staticmethod
    def _get_session(email, token):
        session = requests.Session()
        defaults = {
            'X-PW-Application': 'developer_api',
            'X-PW-AccessToken': token,
            'X-PW-UserEmail': email,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        session.headers.update(defaults)
        return session

    def __getattr__(self, name):
        """
        Turn HTTP verbs into http_method calls so e.g. conn.get(...) works.
        """
        methods = 'get', 'post', 'put', 'patch', 'delete', 'options'
        if name in methods:
            return functools.partial(self.http_method, name)
        return super(Connection, self).__getattr__(name)