# Dataset-specific parsers + paraphrasing flow
import json
import random
import hashlib
from typing import Callable, Optional, Dict, Tuple

from utils.schema import sft_row
from utils import augment as A

def _hash_id(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
    return h.hexdigest()[:16]

def _iter_json_or_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        first = f.read(1); f.seek(0)
        if first == "[":
            data = json.load(f)
            for obj in data: yield obj
        else:
            for line in f:
                line = line.strip()
                if line: yield json.loads(line)

def process_file_into_sft(
    dataset_key: str,
    input_path: str,
    writer,
    paraphraser,
    augment_opts: Dict,
    sample_limit: Optional[int],
    seed: int,
    progress_cb: Optional[Callable[[float, str], None]]
) -> Tuple[int, Dict]:
    random.seed(seed)
    stats = {
        "written": 0,
        "paraphrased_input": 0,
        "paraphrased_output": 0,
        "backtranslated_input": 0,
        "backtranslated_output": 0,
        "dedup_skipped": 0,
        "consistency_failed": 0
    }
    dedupe_seen = set() if augment_opts.get("dedupe", True) else None

    key = dataset_key.lower()
    if key in ("healthcaremagic", "icliniq"):
        count = _proc_med_dialog(source=key, path=input_path, writer=writer,
                                 paraphraser=paraphraser, opts=augment_opts,
                                 sample_limit=sample_limit, stats=stats, cb=progress_cb)
    elif key == "pubmedqa_l":
        count = _proc_pubmedqa_l(input_path, writer, paraphraser, augment_opts, sample_limit, stats, progress_cb)
    elif key == "pubmedqa_u":
        count = _proc_pubmedqa_u(input_path, writer, paraphraser, augment_opts, sample_limit, stats, progress_cb)
    elif key == "pubmedqa_map":
        count = _proc_pubmedqa_map(input_path, writer, paraphraser, augment_opts, sample_limit, stats, progress_cb)
    else:
        raise ValueError(f"Unknown dataset: {dataset_key}")
    return count, stats

# ——————————— helpers ———————————

def _apply_aug(instr: str, user: str, out: str, source: str, opts: Dict, paraphraser, stats: Dict):
    # Base cleanup & caps
    user = A.base_cleanup(user, opts.get("max_chars", 5000), opts.get("deidentify", True))
    out  = A.base_cleanup(out,  opts.get("max_chars", 5000), opts.get("deidentify", True))
    instr = A.base_cleanup(instr, opts.get("max_chars", 5000), False)

    # Language sanity (mostly English—skip aggressive transforms if not)
    if not A.lang_is_english(user):  # very rare
        return instr, user, out, []

    applied = []

    # Paraphrase & Back-translate (inputs)
    u2, did_p = A.maybe_paraphrase(user, opts.get("paraphrase_ratio", 0.0), paraphraser, "easy")
    if did_p: applied.append("paraphrase_input"); stats["paraphrased_input"] += 1
    u3, did_bt = A.maybe_backtranslate(u2, opts.get("backtranslate_ratio", 0.0), paraphraser)
    if did_bt: applied.append("backtranslate_input"); stats["backtranslated_input"] += 1
    user = u3

    # Outputs (optional)
    if opts.get("paraphrase_outputs", False):
        o2, did_p2 = A.maybe_paraphrase(out, opts.get("paraphrase_ratio", 0.0), paraphraser, "hard")
        if did_p2: applied.append("paraphrase_output"); stats["paraphrased_output"] += 1
        o3, did_bt2 = A.maybe_backtranslate(o2, opts.get("backtranslate_ratio", 0.0), paraphraser)
        if did_bt2: applied.append("backtranslate_output"); stats["backtranslated_output"] += 1
        out = o3

    # Style standardise the answer
    if opts.get("style_standardize", True):
        out = A.style_standardize_answer(out)
        applied.append("style_standardize")

    # Ensure punctuation/whitespace
    user = A.ensure_terminal_punct(user) if user else user
    out  = A.ensure_terminal_punct(out)  if out  else out

    return instr, user, out, applied

def _commit_row(writer, source, rid, task, instr, user, out, opts, stats, aug_applied, extra_meta=None, dedupe_seen=None):
    # Dedup
    if dedupe_seen is not None:
        fp = A.fingerprint(instr, user, out)
        if fp in dedupe_seen:
            stats["dedup_skipped"] += 1
            return False
        dedupe_seen.add(fp)

    meta = {"augmentations": aug_applied}
    if extra_meta:
        meta.update(extra_meta)

    row = sft_row(instr, user, out, source=source, rid=rid, task=task, meta=meta)
    writer.write(row)
    stats["written"] += 1
    return True

# ——————————— dataset processors ———————————

def _proc_med_dialog(source, path, writer, paraphraser, opts, sample_limit, stats, cb):
    count = 0
    written = 0
    for i, obj in enumerate(_iter_json_or_jsonl(path), start=1):
        instr = (obj.get("instruction") or "Answer the patient's question like a clinician. Be concise and safe.")
        user  = (obj.get("input") or "").strip()
        out   = (obj.get("output") or "").strip()
        rid   = _hash_id(source, i, len(user), len(out))

        instr, user, out, applied = _apply_aug(instr, user, out, source, opts, paraphraser, stats)

        # Optional consistency spot-check (cheap)
        if not A.consistency_ok(user, out, opts.get("consistency_check_ratio", 0.0), paraphraser):
            stats["consistency_failed"] += 1
            # keep the sample but tag it
            applied.append("consistency_flag")

        _commit_row(writer, source, rid, "medical_dialogue", instr, user, out, opts, stats, applied)

        count += 1
        if sample_limit and count >= sample_limit:
            break
        if cb and i % 1000 == 0:
            cb(min(0.9, 0.05 + i/200000), f"{source}: processed {i} rows")
    if cb:
        cb(0.92, f"{source} done ({count})")
    return count

def _proc_pubmedqa_l(path, writer, paraphraser, opts, sample_limit, stats, cb):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for k, v in data.items():
        q = (v.get("QUESTION") or "").strip()
        ctx_list = v.get("CONTEXTS") or []
        long_ans = (v.get("LONG_ANSWER") or "").strip()
        final = (v.get("final_decision") or "").strip()
        context = "\n".join(ctx_list).strip()

        instr = "Answer the biomedical question using the provided context. Include a concise rationale if possible."
        user  = f"Question: {q}\n\nContext:\n{context}" if context else f"Question: {q}"
        out   = long_ans if long_ans else final
        rid   = str(k)

        instr, user, out, applied = _apply_aug(instr, user, out, "pubmedqa_l", opts, paraphraser, stats)
        _commit_row(writer, "pubmedqa_l", rid, "biomedical_qa", instr, user, out, opts, stats, applied,
                    extra_meta={"year": v.get("YEAR"), "meshes": v.get("MESHES"), "labels": v.get("LABELS")})

        count += 1
        if sample_limit and count >= sample_limit:
            break
        if cb and count % 1000 == 0:
            cb(min(0.9, 0.05 + count/60000), f"pubmedqa_l processed {count}")
    if cb:
        cb(0.93, f"pubmedqa_l done ({count})")
    return count

def _proc_pubmedqa_u(path, writer, paraphraser, opts, sample_limit, stats, cb):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    count = 0
    for k, v in data.items():
        q = (v.get("QUESTION") or "").strip()
        ctx_list = v.get("CONTEXTS") or []
        context = "\n".join(ctx_list).strip()

        instr = "Rewrite the context into a succinct note, then answer the question. If unknown, say 'insufficient evidence'."
        user  = f"Question: {q}\n\nContext:\n{context}" if context else f"Question: {q}"
        out   = ""  # unlabeled

        # Optional KD/distillation for a small fraction
        if opts.get("distill_fraction", 0.0) > 0.0 and random.random() < float(opts["distill_fraction"]):
            prompt = f"{instr}\n\n{user}\n\nAnswer briefly and safely."
            guess = paraphraser.paraphrase(prompt, difficulty="hard")  # cheap single call
            if guess and len(guess) < 2000:
                out = guess.strip()

        instr, user, out, applied = _apply_aug(instr, user, out, "pubmedqa_u", opts, paraphraser, stats)
        _commit_row(writer, "pubmedqa_u", str(k), "biomedical_qa_unlabeled", instr, user, out, opts, stats, applied)

        count += 1
        if sample_limit and count >= sample_limit:
            break
        if cb and count % 2000 == 0:
            cb(min(0.9, 0.05 + count/80000), f"pubmedqa_u processed {count}")
    if cb:
        cb(0.94, f"pubmedqa_u done ({count})")
    return count

def _proc_pubmedqa_map(path, writer, paraphraser, opts, sample_limit, stats, cb):
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    def iter_items():
        if isinstance(obj, list):
            for it in obj: yield it
        elif isinstance(obj, dict):
            qs, cs, ans = obj.get("question"), obj.get("context"), obj.get("answer")
            if isinstance(qs, list) and isinstance(cs, list) and isinstance(ans, list):
                for i in range(min(len(qs), len(cs), len(ans))):
                    yield {"question": qs[i], "context": cs[i], "answer": ans[i]}
            else:
                for _, v in obj.items(): yield v

    count = 0
    for i, v in enumerate(iter_items(), start=1):
        q = (v.get("question") or "").strip()
        c = (v.get("context") or "").strip()
        a = (v.get("answer") or "").strip()

        instr = "Answer the biomedical question based on the context. Justify briefly."
        user  = f"Question: {q}\n\nContext:\n{c}" if c else f"Question: {q}"
        out   = a
        rid   = _hash_id("pubmedqa_map", i, len(q))

        instr, user, out, applied = _apply_aug(instr, user, out, "pubmedqa_map", opts, paraphraser, stats)
        _commit_row(writer, "pubmedqa_map", rid, "biomedical_qa", instr, user, out, opts, stats, applied)

        count += 1
        if sample_limit and count >= sample_limit:
            break
        if cb and i % 2000 == 0:
            cb(min(0.9, 0.05 + i/120000), f"pubmedqa_map processed {i}")
    if cb:
        cb(0.95, f"pubmedqa_map done ({count})")
    return count
