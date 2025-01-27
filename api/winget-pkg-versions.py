from http.server import BaseHTTPRequestHandler
from sqlite3 import connect
from json import dumps
from zipfile import ZipFile
from urllib.request import urlretrieve

# Download the source.msix file from the WinGet CDN (Content Delivery Network)
urlretrieve("https://cdn.winget.microsoft.com/cache/source.msix", "/tmp/source.msix")

# Extract the index.db file from the source.msix file
ZipFile("/tmp/source.msix").extract("Public/index.db", "/tmp/")

# Connect to the database
db = connect("/tmp/Public/index.db")
cursor = db.cursor()

# Get the manifests table
cursor.execute('SELECT id, version FROM manifest')
manifests = cursor.fetchall()

# Initialize the result dictionary
result = {}

# Iterate over each row in the manifests table
for row in manifests:
    id, version = row

    # Get the id value from the ids table
    cursor.execute(f'SELECT id FROM ids WHERE rowid = {id}')
    id_value = cursor.fetchone()[0]

    # Get the version value from the versions table
    cursor.execute(f'SELECT version FROM versions WHERE rowid = {version}')
    version_value = cursor.fetchone()[0]

    # Add the id and version to the result dictionary
    if id_value not in result:
        result[id_value] = []
    result[id_value].append(version_value)

# Close the database connection
db.close()

class handler(BaseHTTPRequestHandler):

  def do_GET(self):
    # get query parameters in form of map/dictionary
    query = dict()
    
    # check if query parameters are present
    if "?" in self.path:
        query = dict(q.split("=") for q in self.path.split("?")[1].split("&"))
    else:
        self.send_response(400)
        self.end_headers()
        self.wfile.write("pkgid is either empty or not provided".encode())
        return

    # check if pkgid is provided
    if "pkgid" not in query:
        self.send_response(400)
        self.end_headers()
        self.wfile.write("pkgid is either empty or not provided".encode())
        return
    
    pkg_id = query["pkgid"]

    # if package identifier is "*", return all packages
    if pkg_id == "*":
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(dumps(result).encode())
        return

    # check if package identifier is in result dictionary
    if pkg_id not in result:
        self.send_response(404)
        self.end_headers()
        self.wfile.write("Package identifier not found. Please make sure that atleast one version of the package is available in winget-pkgs repository.".encode())
        return
    
    # send response
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(dumps({pkg_id: result[pkg_id]}).encode())
    return
