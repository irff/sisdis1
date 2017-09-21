import datetime
import random
import socket
import sys
import urllib

HOST, PORT = '', 12345
REQUEST_QUEUE_SIZE = 16

class SisdisServer():
    CONTENT_TYPE_TEXT = 'text/plain; charset=UTF-8'
    CONTENT_TYPE_CSS = 'text/css; charset=utf-8'
    CONTENT_TYPE_HTML = 'text/html; charset=utf-8'
    CONTENT_TYPE_JPEG = ' image/jpeg; charset=utf-8'
    CONTENT_TYPE_FORM = 'application/x-www-form-urlencoded'

    MAX_INT = sys.maxint
    MIN_INT = -MAX_INT - 1

    def __init__(self):
        self.client_connection = None
        self.default_version = 'HTTP/1.1'
        self.headers = ''

    def build_header(self, version, status, message):
        return version + " " + str(status) + " " + message + "\r\n"

    def add_header(self, key, value):
        self.headers += str(key) + ': ' + str(value) + '\r\n'

    def add_headers(self, headers):
        for key, value in headers:
            self.add_header(key, value)

    def build_response(self, header, body):
        return header + self.headers + '\r\n' + body

    def send_error(self, version, status, message, reason):
        header = self.build_header(version, status, message)
        body = str(status) + ' ' + message + ': Reason: ' + reason

        self.add_headers([
            ('Connection', 'close'),
            ('Content-Type', 'text/plain; charset=UTF-8'),
            ('Content-Length', str(len(body)))
        ])

        self.client_connection.sendall(self.build_response(header, body))

    def send_response(self, message, headers):
        header = self.build_header(self.default_version, 200, 'OK')
        body = message

        self.add_headers([
            ('Connection', 'close'),
            ('Content-Length', str(len(body)))
        ])

        self.add_headers(headers)

        self.client_connection.sendall(self.build_response(header, body))

    def send_redirect(self, target):
        header = self.build_header(self.default_version, 302, 'Found')
        body = str(302) + ' ' + 'Found: Location: ' + target

        self.add_headers([
            ('Connection', 'close'),
            ('Location', target),
            ('Content-Type', self.CONTENT_TYPE_TEXT),
            ('Content-Length', str(len(body)))
        ])

        self.client_connection.sendall(self.build_response(header, body))

    def read_file(self, filename):
        f = open(filename, 'r')
        return f.read()

    def handle_request(self, client_connection):
        self.client_connection = client_connection
        self.headers = ''
        request = self.client_connection.recv(1024)
        request = request.decode()

        print(request)

        request_lines = request.rstrip('\r\n').split('\r\n')
        words = request_lines[0].split()
        request_components = request.rstrip('\r\n').split('\r\n\r\n')

        post_params = None
        url_encoded = False

        for request_line in request_lines:
            request_line_components = request_line.split(': ')
            if len(request_line_components) == 2:
                key = request_line_components[0]
                value = request_line_components[1]

                if key == 'Content-Type' and value == self.CONTENT_TYPE_FORM:
                    url_encoded = True

        if len(request_components) == 2:
            post_params = request_components[1]

        if len(words) == 3:
            command, path, version = words
            if version[:5] != 'HTTP/':
                self.send_error(self.default_version, 400, 'Bad request', 'Invalid Protocol Type')
                return False

            version_number = version.split('/', 1)[1]
            if not (version_number == '1.0' or version_number == '1.1'):
                self.send_error(self.default_version, 400, 'Bad request', 'Invalid HTTP Version')
                return False

            if command == 'GET':
                if path == '/':
                    self.send_redirect('/hello-world')
                elif path == '/style':
                    self.send_response(self.read_file('style.css'), [('Content-Type', self.CONTENT_TYPE_CSS)])
                elif path == '/background':
                    self.send_response(self.read_file('background.jpg'), [('Content-Type', self.CONTENT_TYPE_JPEG)])
                elif path == '/hello-world':
                    file = self.read_file('hello-world.html').replace('__HELLO__', 'World')
                    self.send_response(file, [('Content-Type', self.CONTENT_TYPE_HTML)])
                else:
                    paths = path.split('?')
                    if len(paths) == 2 and paths[0] == '/info' and paths[1][:4] == 'type':
                        type = paths[1][5:]

                        content = 'No Data'
                        if type == 'random':
                            content = str(random.randint(self.MIN_INT, self.MAX_INT))
                        elif type == 'time':
                            content = str(datetime.datetime.now())

                        self.send_response(content, [('Content-Type', self.CONTENT_TYPE_TEXT)])
                    else:
                        self.send_error(self.default_version, 404, 'Not Found', 'Content Not Found')

            elif command == 'POST':
                if path == '/':
                    self.send_redirect('/hello-world')
                elif path == '/hello-world':
                    if url_encoded and post_params:
                        params = post_params.split('=')
                        if len(params) == 2 and params[0] == 'name':
                            name = urllib.unquote(params[1])
                            file = self.read_file('hello-world.html').replace('__HELLO__', name)
                            self.send_response(file, [('Content-Type', self.CONTENT_TYPE_HTML)])
                        else:
                            self.send_error(self.default_version, 400, 'Bad request', 'Invalid Parameters')
                    else:
                        self.send_error(self.default_version, 400, 'Bad request', 'Invalid Content Type')
                else:
                    self.send_error(self.default_version, 404, 'Not Found', 'Content Not Found')
            else:
                self.send_error(self.default_version, 501, 'Not Implemented', command)
                return False

def serve():
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind((HOST, PORT))
    listen_socket.listen(REQUEST_QUEUE_SIZE)
    print('Serving HTTP on port {port} ...'.format(port=PORT))

    server = SisdisServer()

    while True:
        client_connection, client_address = listen_socket.accept()
        server.handle_request(client_connection)
        client_connection.close()


if __name__ == '__main__':
    serve()
