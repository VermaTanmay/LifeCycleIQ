import subprocess, sys, sqlite3, tempfile, unittest
from pathlib import Path
GEN=Path(__file__).resolve().parents[1]/"generator"/"generate_data.py"
class GeneratorTests(unittest.TestCase):
    def test_small_dataset_counts_and_foreign_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable,str(GEN),"--output",tmp,"--employees","20","--tasks","160","--grants","30","--assets","24"],check=True,capture_output=True)
            con=sqlite3.connect(Path(tmp)/"lifecycleiq.db")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM Employee").fetchone()[0],20)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM Task").fetchone()[0],160)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM AccessGrant").fetchone()[0],30)
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(),[])
            con.close()
if __name__=="__main__": unittest.main()
