# pip install flask flask-cors

from flask import Flask, Response, request, has_request_context
from flask_cors import CORS
from datetime import datetime
import ast
import json
import logging
import os
import socket
import traceback


app = Flask(__name__)
CORS(app)

# ------------------------------------------------------------------------------
# Logging configuration
# ------------------------------------------------------------------------------

class RequestContextFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.client_ip = request.remote_addr
            record.method = request.method
            record.path = request.path
        else:
            record.client_ip = "-"
            record.method = "-"
            record.path = "-"
        return True

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s %(client_ip)s %(method)s %(path)s",
    datefmt="%I:%M:%S %p"
)

for handler in logging.getLogger().handlers:
    handler.addFilter(RequestContextFilter())

# Reduce Werkzeug noise but keep errors
werkzeug_log = logging.getLogger("werkzeug")
werkzeug_log.setLevel(logging.WARNING)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

port_number = 5001

# Resolve local IP
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]

# File path to serve
file_path = "data/GSE57383_ps_psa.txt"

# File to store DCP results
timestamp = datetime.now().strftime("%d%m%y_%H%M%S")  # e.g., 260112_212032
results_path = f"results/GSE57383_PsA_vs_Ps_{timestamp}.txt"

# ------------------------------------------------------------------------------
# Fail fast on startup if required file is missing
# ------------------------------------------------------------------------------

if not os.path.isfile(file_path):
    raise FileNotFoundError(f"Required file missing: {file_path}")


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route("/GSE57383_ps_psa", methods=["GET"])
def serve_file_content():
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        app.logger.info(
            f"Incoming request"
        )

        return Response(
            content,
            content_type="text/plain; charset=utf-8",
            status=200,
        )

    except FileNotFoundError:
        app.logger.error(f"File not found at request time: {file_path}")
        return Response(
            f"File not found: {file_path}",
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    except Exception:
        app.logger.error("Unhandled error while serving file")
        app.logger.error(traceback.format_exc())
        return Response(
            "Internal server error",
            status=500,
            content_type="text/plain; charset=utf-8",
        )


@app.route("/dcp-results", methods=["POST"])
def receive_dcp_results():
    try:
        # 1. Always form-encoded
        form = request.form.to_dict(flat=False)

        if not form:
            return Response(
                "Invalid or missing payload",
                status=400,
                content_type="text/plain; charset=utf-8",
            )

        # 2. Normalize envelope (single-value lists → scalars)
        envelope = {
            "elementType": form.get("elementType", [None])[0],
            "contentType": form.get("contentType", [None])[0],
            "element": form.get("element", [None])[0],
            "rawContent": form.get("content", [None])[0],
        }

        content_type = envelope["contentType"]
        raw_content = envelope["rawContent"]

        if raw_content is None:
            raise ValueError("Missing content field")

        # 3. Decode content payload
        if content_type == "application/json":
            # content is JSON serialized *inside a string*
            parsed_content = json.loads(raw_content)

        elif content_type == "text/plain":
            # Strip wrapping quotes and unescape
            parsed_content = ast.literal_eval(raw_content)

        else:
            # Unknown / passthrough
            parsed_content = raw_content

        result = {
            "elementType": envelope["elementType"],
            "element": envelope["element"],
            "contentType": content_type,
            "content": parsed_content,
        }

        with open(results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result["content"]) + "\n")

        app.logger.info(
            f"Received result {result['element']}"
        )

        return Response(
            f"Result received",
            status=200,
            content_type="text/plain; charset=utf-8",
        )

    except Exception:
        app.logger.error("Unhandled error while processing DCP result")
        app.logger.error(traceback.format_exc())
        return Response(
            "Internal server error",
            status=500,
            content_type="text/plain; charset=utf-8",
        )



@app.route("/health", methods=["GET"])
def health():
    return {
        "file_exists": os.path.isfile(file_path),
        "file_path": file_path,
    }

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print(f" * Serving data on: http://{local_ip}:{port_number}")
    print(f" * DCP results endpoint: http://{local_ip}:{port_number}/dcp-results")
    app.run(host="0.0.0.0", port=port_number)
