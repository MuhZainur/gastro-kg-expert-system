import json
from concurrent.futures import ThreadPoolExecutor
from backend.tests.conftest import case_request


def _normalize(body: dict) -> dict:
    focus = body["graph"]["focus"]
    enc_id = focus.split(":", 1)[1]
    pat_nodes = [k for k, v in body["graph"]["nodes"].items() if v[0] == "patient"]
    pat_ids = [n.split(":", 1)[1] for n in pat_nodes]
    body.pop("meta", None)
    body.pop("graph", None)
    text = json.dumps(body, sort_keys=True).replace(enc_id, "<ENC>")
    for pid in pat_ids:
        text = text.replace(pid, "<PAT>")
    return json.loads(text)


def test_s15_concurrent_consultations_do_not_mix(client):
    case_ids = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    sequential = {}
    for cid in case_ids:
        r = client.post("/api/consultations", json=case_request(cid))
        assert r.status_code == 200
        sequential[cid] = _normalize(r.json())

    def run_one(cid):
        r = client.post("/api/consultations", json=case_request(cid))
        assert r.status_code == 200
        raw = r.text
        body = r.json()
        focus = body["graph"]["focus"]
        enc_id = focus.split(":", 1)[1]
        pat_nodes = [k for k, v in body["graph"]["nodes"].items() if v[0] == "patient"]
        pat_ids = [n.split(":", 1)[1] for n in pat_nodes]
        return cid, enc_id, pat_ids, raw, _normalize(body)

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(run_one, case_ids))

    enc_ids = [enc_id for _, enc_id, _, _, _ in results]
    all_pat_ids = [pid for _, _, pat_ids, _, _ in results for pid in pat_ids]
    assert len(set(enc_ids)) == 10
    assert len(set(all_pat_ids)) == 10

    for idx, (cid, _enc_id, _pat_ids, raw, norm_body) in enumerate(results):
        assert norm_body == sequential[cid]
        other_encs = [e for j, e in enumerate(enc_ids) if j != idx]
        other_pats = [p for j, (_, _, pids, _, _) in enumerate(results) if j != idx for p in pids]
        for foreign_id in other_encs + other_pats:
            assert foreign_id not in raw
