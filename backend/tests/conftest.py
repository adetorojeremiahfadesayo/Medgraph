import os
from pathlib import Path


os.environ["MEDGRAPH_ENV_FILE"] = str(Path(__file__).with_name(".env.test"))
os.environ["COGNEE_ENABLE_SDK"] = "false"
os.environ["COGNEE_ENABLE_CLOUD"] = "false"
os.environ.setdefault("COGNEE_ENABLE_SDK", "false")
os.environ.setdefault("COGNEE_ENABLE_CLOUD", "false")
os.environ.setdefault("COGNEE_LOCAL_OPERATION_TIMEOUT", "1")
os.environ.setdefault("COGNEE_CLOUD_OPERATION_TIMEOUT", "1")
os.environ.setdefault("COGNEE_CLOUD_CONNECT_TIMEOUT", "1")
