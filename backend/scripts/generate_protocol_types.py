import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.protocol_codegen import write_types

if __name__ == "__main__":
    write_types()
