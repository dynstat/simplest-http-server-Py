import os
import socket
import threading
import mimetypes  # For content-type detection

# Define the server address and port
SERVER_ADDRESS = ("localhost", 8000)

# Define the allowed origins for CORS
ALLOWED_ORIGINS = [
    "*",
    "http://localhost:8000",
    "null",
]  # Allow requests from file:// URLs and the same origin

STATUS_CODE = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    301: "301 Moved Permanently",
    302: "302 Found",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    403: "403 Forbidden",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    500: "500 Internal Server Error",
    503: "503 Service Unavailable",
}

# Base directory is the current folder where this script is located
BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def handle_request(conn, addr):
    try:
        # Receive the HTTP request
        request_data = conn.recv(1024).decode()
        if not request_data:
            conn.close()
            return
        print("Received request:", request_data[0:14], "  ....")  # For debugging

        # Parse the first line of the request to get the method and path
        request_line = request_data.splitlines()[0]
        method, path, http_version = request_line.split()

        # Basic security: Validate HTTP method
        if method not in ["GET", "POST"]:
            raise ValueError("Unsupported HTTP method")

        # Basic security: Sanitize the requested path to prevent directory traversal
        if "../" in path:
            raise ValueError("Invalid path")

        # Default path to index.html if root is requested
        if path == "/":
            path = "/index.html"

        # Construct the file path
        file_path = os.path.join(BASE_DIR, path.strip("/"))

        # Basic security: Ensure requested file path is within the base directory
        if not file_path.startswith(BASE_DIR):
            raise ValueError("Invalid file path")

        # Check if the file exists and is not a directory
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            with open(file_path, "rb") as file:
                response_body = file.read()
            status_code = f"{STATUS_CODE[200]}"
            # Determine content type using mimetypes module
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"  # Default to binary data if type is unknown
        else:
            # File not found, send 404 response
            response_body = b"<h1>404 Not Found</h1>"
            content_type = "text/html"
            status_code = f"{STATUS_CODE[404]}"

        content_length = len(response_body)

        # Construct the response headers with CORS
        response_headers = [
            f"{http_version} {status_code}",
            f"Content-Type: {content_type}",
            f"Content-Length: {content_length}",
            "Connection: close",
            "Access-Control-Allow-Origin: *",  # Allow all origins for simplicity
            "Access-Control-Allow-Methods: GET, POST, OPTIONS",
            "Access-Control-Allow-Headers: Content-Type",
        ]

        # Combine headers into a single string, add a blank line to separate headers from the body
        response_header_str = "\r\n".join(response_headers) + "\r\n\r\n"

        print(f"Response: {http_version} {status_code}\n")
        # Send the combined response
        conn.sendall(response_header_str.encode() + response_body)
        conn.close()
    except Exception as e:
        print(f"\n************ EXCEPTION : {e} ***********\n")
        response_body = b"<h1>500 Internal Server Error</h1>"
        content_length = len(response_body)
        content_type = "text/html"
        # Use HTTP/1.1 as a fallback if an exception occurs before HTTP version is determined
        response_headers = [
            "HTTP/1.1 500 Internal Server Error",
            f"Content-Type: {content_type}",
            f"Content-Length: {content_length}",
            "Connection: close",
            f"Access-Control-Allow-Origin: {ALLOWED_ORIGINS[0]}",
            "Access-Control-Allow-Methods: GET, POST, OPTIONS",
            "Access-Control-Allow-Headers: Content-Type",
        ]
        response_header_str = "\r\n".join(response_headers) + "\r\n\r\n"
        conn.sendall(response_header_str.encode() + response_body)
        conn.close()


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(SERVER_ADDRESS)
    server_socket.listen(5)
    print(f"Server listening on http://{SERVER_ADDRESS[0]}:{SERVER_ADDRESS[1]}")

    # Setting a timeout of 1 second on blocking socket operations (accept() call) to allow for keyboard interrupt (CTRL + c) recognition in the terminal.
    server_socket.settimeout(1)

    try:
        print("Waiting for a connection...")
        while True:
            try:
                # no more a infinitely blocking call, because of server_socket.settimeout(1)
                conn, addr = server_socket.accept()
                print(f"Connection from {addr}")

                # Handle the client request in a new thread
                client_thread = threading.Thread(
                    target=handle_request, args=(conn, addr), name=f"{addr[1]}"
                )
                client_thread.start()
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                try:
                    if conn:
                        conn.close()
                except:
                    pass
                break
    except KeyboardInterrupt:
        print("Server stopped")
        server_socket.close()


if __name__ == "__main__":
    start_server()
