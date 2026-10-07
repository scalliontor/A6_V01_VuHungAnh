"""Catalog image index backed by local Apple Vision feature prints."""
import atexit
import json
from pathlib import Path
import subprocess
import sys


class VectorIndex:
    def __init__(self, repository):
        self.repository = repository
        self._process = None
        self.last_ocr_text = ""
        self.last_image_scores = {}
        atexit.register(self.close)

    def _backend(self):
        if sys.platform != "darwin":
            raise RuntimeError("Image search requires macOS Vision and Swift")
        if self._process is None or self._process.poll() is not None:
            script = Path(__file__).with_name("vision_backend.swift")
            command = ["swift", str(script), str(self.repository.path.resolve())]
            try:
                self._process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1,
                )
            except FileNotFoundError as error:
                raise RuntimeError("Swift is required for macOS Vision image search") from error
        return self._process

    def scores(self, query_image):
        backend = self._backend()
        backend.stdin.write(json.dumps({"image_path": str(Path(query_image).resolve())}) + "\n")
        backend.stdin.flush()
        response = backend.stdout.readline()
        if not response:
            message = backend.stderr.read().strip()
            raise RuntimeError(f"Vision backend stopped: {message or 'no response'}")
        result = json.loads(response)
        if "error" in result:
            raise RuntimeError(f"Vision could not analyze the image: {result['error']}")
        self.last_ocr_text = " ".join(result.get("recognized_text", []))
        # Sorting by this similarity is equivalent to sorting by Vision distance.
        self.last_image_scores = {
            product_id: 1.0 / (1.0 + distance)
            for product_id, distance in result["distances"].items()
        }
        return self.last_image_scores

    def close(self):
        process = self._process
        if process is not None and process.poll() is None:
            process.stdin.close()
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if process is not None:
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
        self._process = None
