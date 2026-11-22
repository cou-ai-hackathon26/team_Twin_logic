"""Export the wav2vec2 CTC model to ONNX (optionally int8) for faster CPU inference.

    python -m scripts.export_onnx            # fp32 + int8 into data/onnx/
    # the app picks data/onnx/model.int8.onnx automatically (PB_CTC_BACKEND=auto)

The output is a single graph: input_values (1, samples) -> logits (1, frames, vocab).
The processor (tokenizer + feature extractor) is saved next to it.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=get_settings().ctc_model_id)
    ap.add_argument("--out", default=str(get_settings().data_dir / "onnx"))
    ap.add_argument("--no-int8", action="store_true")
    args = ap.parse_args()

    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    proc = Wav2Vec2Processor.from_pretrained(args.model)
    model = Wav2Vec2ForCTC.from_pretrained(args.model).eval()
    proc.save_pretrained(out)
    model.config.save_pretrained(out)
    dummy = torch.randn(1, 16000 * 4)
    fp32 = out / "model.onnx"
    t0 = time.perf_counter()
    torch.onnx.export(
        model, (dummy,), str(fp32), input_names=["input_values"], output_names=["logits"],
        dynamic_axes={"input_values": {1: "samples"}, "logits": {1: "frames"}}, opset_version=17,
        dynamo=False,
    )
    print(f"exported {fp32} in {time.perf_counter() - t0:.1f}s")
    if not args.no_int8:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        q = out / "model.int8.onnx"
        # Only MatMul/Gemm: ConvInteger has no CPU kernel in ONNX Runtime.
        quantize_dynamic(str(fp32), str(q), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"])
        print(f"quantised -> {q}")

    # parity check
    import onnxruntime as ort

    with torch.inference_mode():
        ref = model(dummy).logits.numpy()
    sess = ort.InferenceSession(str(fp32), providers=["CPUExecutionProvider"])
    got = sess.run(["logits"], {"input_values": dummy.numpy()})[0]
    print("max abs diff fp32:", float(np.abs(ref - got).max()))


if __name__ == "__main__":
    main()
