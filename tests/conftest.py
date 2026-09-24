"""Point the app at a throw-away database so tests never touch backend/data/."""
import os
import tempfile

os.environ.setdefault(
    "HOSPITALFLOW_DB", os.path.join(tempfile.mkdtemp(prefix="hospitalflow-tests-"), "test.db")
)
