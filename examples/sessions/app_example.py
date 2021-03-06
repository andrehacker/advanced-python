from wsgiref.simple_server import make_server
import uuid
from http.cookies import SimpleCookie


class DictBasedSessionStore:
    """
    A reference store, which stores items in a global dictionary.

    This in not suitable for a real usage (e.g. an application which
    run with multiple workers)
    """

    sessions = {}

    def __setitem__(self, id, data):
        self.sessions[id] = data

    def __getitem__(self, id):
        return self.sessions[id]

    def __contains__(self, id):
        return id in self.sessions


class SimpleSession:

    def __init__(self, storage, id=None):
        self.store = storage
        self.data = {}
        self.load(id)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]

        return default

    def load(self, id):
        """
        Find id in storage, if failed create a new ID.

        """
        if id in self.store:
            self.data = self.store[id]
            self.id = id
        else:
            self.data = {}
            self.id = uuid.uuid4().hex

    def save(self):
        self.store[self.id] = self.data
        return self.id


class SimpleSessionMiddleware:
    """
    This middleware injects a SimpleSession instance to the envrionment
    passed to the application.

    You can than put anything you want in this instance of session.

    """
    def __init__(self, app, session_manager=DictBasedSessionStore,
                 env_key='wsgisession', cookie_key='session_id'):
        self.app = app
        self.env_key = env_key
        self.cookie_key = cookie_key
        self.manager = session_manager()

    def __call__(self, environ, start_response):
        cookie = SimpleCookie()
        if 'HTTP_COOKIE' in environ:
            cookie.load(environ['HTTP_COOKIE'])

        id = None
        if self.cookie_key in cookie:
            id = cookie[self.cookie_key].value

        session = SimpleSession(self.manager, id=id)
        environ[self.env_key] = session

        def middleware_start_response(status, response_headers, exc_info=None):

            session.save()
            cookie = SimpleCookie()
            cookie[self.cookie_key] = session.id
            cookie[self.cookie_key]['path'] = '/'
            cookie_string = cookie[self.cookie_key].OutputString()
            response_headers.append(('Set-Cookie', cookie_string))
            return start_response(status, response_headers, exc_info)

        return self.app(environ, middleware_start_response)


def wrapped_app(environ, start_response):

    session = environ.get('wsgisession')
    # google chrome sends 2 requests ...

    if environ['PATH_INFO'] != '/favicon.ico':

        session['counter'] = session.get('counter', 0) + 1

    start_response('200 OK', [('Content-Type', 'text/plain')])

    if session['counter'] > 1:
        response = ['Hello Again!\nYou Visited {} times'.format(
                    session['counter'])]
    else:
        response = ['Hello and Welcome!']

    return (x.encode() for x in response)


app = SimpleSessionMiddleware(wrapped_app)

if __name__ == '__main__':
    httpd = make_server('localhost', 8080, app)
    print("Listening on http://localhost:8080")

    httpd.serve_forever()
