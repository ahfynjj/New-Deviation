"""Execute native integration tests only in a disposable filesystem copy."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="tx15-model-test-") as tmp:
    runtime = Path(tmp) / "filesystem"
    shutil.copytree(root / "src/filesystem/tx15", runtime)
    env = os.environ.copy()
    env["DEVIATION_EMU_FILESYSTEM"] = str(runtime)
    # Under MSYS Python, native fopen/chdir need a Windows path.
    if os.name != "nt":
        env["DEVIATION_EMU_FILESYSTEM"] = subprocess.check_output(
            ["cygpath", "-w", str(runtime)], text=True).strip()
    result = subprocess.run([str(root / "src/tx15-input-test.exe")],
                            cwd=root / "src", env=env, capture_output=True, timeout=30)
    print(result.stdout.decode(errors="replace"))
    print(result.stderr.decode(errors="replace"))
    if result.returncode:
        raise SystemExit(result.returncode)
    assert "FMODE1" in (runtime / "models/model2.ini").read_text()
    assert not (runtime / "models/model250.ini").exists()
    print("PASS rejected files preserved")
