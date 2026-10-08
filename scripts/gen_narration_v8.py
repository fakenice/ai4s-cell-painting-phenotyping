# -*- coding: utf-8 -*-
"""Generate v8 English narration (en-US-ChristopherNeural) synced to storyline.
Output: temp/narration_v8/narration_v8.mp3 (~2:15, fits the 136s video).
"""
import os
import subprocess
import sys

TXT = [
 # S1-S2 opening + task definition (~12s)
 "This demonstration shows our full pipeline for organ-on-a-chip single-cell phenotyping. "
 "Our task: turn raw microscopy images from 384-well plates into treatment signatures. "
 "We segment single cells with Cellpose, build structure-aware features, and validate across plates.",
 # S3-S6 protocol (~30s)
 "Our evaluation protocol is strict. We train on one plate and test on another, "
 "with well-level, compound-grouped, and scaffold-grouped cross-validation. "
 "No compound leakage is allowed. Structural fingerprints like ECFP4 are used only as a structure control, "
 "not as a phenotypic input. Grouped cross-validation honestly reports in-distribution performance around one point zero "
 "dropping to about zero point five.",
 # S7-S9 cross-plate (~30s)
 "Here is the real run of stage eleven, cross-plate generalization. "
 "We train on plate one and test on plate two, strictly held out. "
 "The cross-plate AUC is zero point six eight two five, average precision zero point nine one zero seven. "
 "Compound identity reaches top-one zero point three three, top-five zero point five one.",
 # S10-S11 retrieval (~16s)
 "Same-compound retrieval across plates is six point one times above chance, "
 "with average precision zero point two four five one versus zero point zero four zero one random.",
 # S12-S15 appendix + segmentation (~20s)
 "The appendix reports our negative results honestly: a self-supervised CNN reaches only zero point zero nine five five, "
 "and harmony correction does not help. For reproducibility, here is real Cellpose inference, "
 "segmenting one hundred fifteen cells on CPU in ninety-seven seconds.",
 # S16-S17 scaffold CV (~18s)
 "Finally, scaffold-grouped cross-validation shows what happens when chemistry is held out: "
 "phenotype plus fingerprint drops to about zero point four eight, a honest generalization floor. "
 "ECFP4 fingerprints separate structures, not phenotypes, and are reported only as a SAR control.",
 # S18 close (~6s)
 "All scripts, real logs, and the full seventeen-page technical report are available on GitHub Pages. Thank you.",
]

def main():
    out_dir = r"C:\Users\bigcat\AppData\Roaming\Tencent\Marvis\User\oAN1i2cP6FM7HGCOOYIJo-q-zF5g\workspace\conv_4d6c260740374c1f8951d14f49f075c7\temp\narration_v8"
    os.makedirs(out_dir, exist_ok=True)
    text = " ".join(TXT)
    mp3 = os.path.join(out_dir, "narration_v8.mp3")
    cmd = [sys.executable, "-m", "edge_tts", "--voice", "en-US-ChristopherNeural", "--rate", "+0%",
           "--text", text, "--write-media", mp3]
    print("[tts] running:", " ".join(cmd[:4]), "...")
    rc = subprocess.call(cmd)
    print(f"[tts] rc={rc}, out={mp3}, words={len(text.split())}")
    return rc == 0

if __name__ == "__main__":
    main()
