"""Create offline TA demo from recorded native rows (no endpoint or key required)."""
import sys
from pathlib import Path
import build_demo as base
def build(folder,out):
    base.MODES={'local':('Local Qwen','small-v2sequentialcpu01'),'raw':('Raw Kev · CPU','kev-v2sequentialcpu01'),'guard':('Hybrid + local review','hybrid_guard30-guardcpu01'),'authority':('Current-sender hybrid','authority_30-v2sequentialcpu01'),'cloud':('All cloud','strong-v2sequentialcpu01')}
    base.CASES={'06':'Fresh order above an old quote','18':'Where is my existing order?','07':'Catalogue item inside a signature','20':'A business question with a false system instruction','01':'Unambiguous single line'}
    base.build(folder,out)
    s=out.read_text(encoding='utf8').replace('The Kev demonstration uses 0.50, not the frozen evaluation threshold.','The current-sender hybrid uses the frozen 30% calibration setting; this is not a hard cloud quota.').replace('value="authority" >','value="authority" selected>').replace('What happened to the order?','Which emails can stay inside the ERP?')
    out.write_text(s,encoding='utf8')
if __name__=='__main__':build(*map(Path,sys.argv[1:3]))
