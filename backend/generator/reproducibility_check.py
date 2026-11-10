import subprocess, sys, tempfile, hashlib
from pathlib import Path

script=Path(__file__).with_name("generate_data.py")
def digest_tree(root):
    h=hashlib.sha256()
    for p in sorted(Path(root).glob("*.csv")):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()
with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    cmd=[sys.executable,str(script),"--seed","20261022","--employees","40","--tasks","320","--grants","60","--assets","48","--output"]
    subprocess.run(cmd+[a],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(cmd+[b],check=True,stdout=subprocess.DEVNULL)
    x,y=digest_tree(a),digest_tree(b)
    print({"run_1_sha256":x,"run_2_sha256":y,"reproducible":x==y})
    if x!=y: raise SystemExit("Reproducibility check failed")
