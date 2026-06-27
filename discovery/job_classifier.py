#!/usr/bin/env python3
"""Job Classifier for HaxJobs pipeline.
Clusters jobs by role type so application packs can be reused.
Jobs in the same cluster with 85%+ similarity share a pack instead of regenerating.
"""
import json, os, re, glob
from collections import defaultdict
from datetime import datetime, timezone

from haxjobs_config import INTAKE_DIR, JOB_CLASSIFICATION_FILE as CLASSIFICATION_FILE

# Role clusters — each has keywords that identify the role type
ROLE_CLUSTERS = {
    "backend_engineer": {
        "label": "Backend Engineer",
        "strong": [r"\bbackend\b", r"\bapi\b", r"\bpostgresql\b", r"\bfastapi\b", r"\bdjango\b",
                   r"\bsqlalchemy\b", r"\bmicroservices?\b", r"\brest\b"],
        "weak": [r"\bpython\b", r"\bengineer\b", r"\bdeveloper\b", r"\bserver\b"],
    },
    "ai_ml_engineer": {
        "label": "AI / ML Engineer",
        "strong": [r"\bai\b", r"\bmachine learning\b", r"\bml\b", r"\bllm\b", r"\bagentic\b",
                   r"\brag\b", r"\bhuggingface\b", r"\bpytorch\b", r"\btensorflow\b"],
        "weak": [r"\bpython\b", r"\bdata\b", r"\bmodel\b", r"\btraining\b"],
    },
    "full_stack_engineer": {
        "label": "Full Stack Engineer",
        "strong": [r"\bfullstack\b", r"\bfull-stack\b", r"\bfrontend\b", r"\breact\b",
                   r"\btypescript\b", r"\bjavascript\b", r"\bvue\b", r"\bangular\b"],
        "weak": [r"\bengineer\b", r"\bdeveloper\b", r"\bweb\b", r"\bnode\b"],
    },
    "automation_test_engineer": {
        "label": "Automation / Test Engineer",
        "strong": [r"\bqa\b", r"\bquality assurance\b", r"\btest engineer\b", r"\bautomation engineer\b",
                   r"\bpytest\b", r"\bselenium\b", r"\bplaywright\b", r"\bsdet\b"],
        "weak": [r"\btest\b", r"\bautomation\b"],
    },
    "devops_infra": {
        "label": "DevOps / Infrastructure",
        "strong": [r"\bdevops\b", r"\binfrastructure\b", r"\bkubernetes\b", r"\bdocker\b",
                   r"\bterraform\b", r"\baws\b", r"\bgcp\b", r"\bazure\b", r"\bci/cd\b"],
        "weak": [r"\bcloud\b", r"\bdeployment\b", r"\bplatform\b"],
    },
    "data_engineer": {
        "label": "Data Engineer",
        "strong": [r"\bdata engineer\b", r"\bdata pipeline\b", r"\betl\b", r"\bspark\b",
                   r"\bsnowflake\b", r"\bdatabricks\b", r"\bairflow\b"],
        "weak": [r"\bdata\b", r"\bsql\b", r"\bwarehouse\b"],
    },
}


def classify_job(title, jd_text="", location=""):
    """Classify a job into one of the role clusters. Returns (cluster_key, confidence)."""
    combined = f"{title} {jd_text[:2000]} {location}".lower()
    scores = {}
    for key, cluster in ROLE_CLUSTERS.items():
        strong_matches = sum(1 for p in cluster["strong"] if re.search(p, combined, re.IGNORECASE))
        weak_matches = sum(1 for p in cluster["weak"] if re.search(p, combined, re.IGNORECASE))
        scores[key] = (strong_matches * 3) + weak_matches

    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score < 5:
        return "other", 0.0

    total_possible = (len(ROLE_CLUSTERS[best]["strong"]) * 3) + len(ROLE_CLUSTERS[best]["weak"])
    confidence = min(best_score / max(total_possible, 1), 1.0)
    return best, round(confidence, 2)


def compute_similarity(job1, job2):
    """Compute similarity between two jobs in the same cluster (0.0 to 1.0)."""
    t1 = set(re.findall(r'\b\w+\b', job1.get("title", "").lower()))
    t2 = set(re.findall(r'\b\w+\b', job2.get("title", "").lower()))
    if not t1 or not t2:
        return 0.0
    # Jaccard similarity on title words
    intersection = t1 & t2
    union = t1 | t2
    title_sim = len(intersection) / len(union) if union else 0

    # Also check company match (same company == even more reusable)
    company_match = 1.0 if job1.get("company") == job2.get("company") else 0.0

    return round((title_sim * 0.7) + (company_match * 0.3), 2)


def build_classifications():
    """Scan all completed intake files, classify them, find reusable packs."""
    os.makedirs(os.path.dirname(CLASSIFICATION_FILE), exist_ok=True)

    jobs = []
    if os.path.isdir(INTAKE_DIR):
        for fpath in sorted(glob.glob(f"{INTAKE_DIR}/*.json")):
            try:
                d = json.load(open(fpath))
                if d.get("status") != "completed":
                    continue
                cluster, confidence = classify_job(
                    d.get("title", ""),
                    d.get("jd_text", ""),
                    d.get("location", ""),
                )
                jobs.append({
                    "file": os.path.basename(fpath),
                    "title": d.get("title", ""),
                    "company": d.get("company", ""),
                    "fit_score": d.get("fit_report", {}).get("fit_score", 0),
                    "cluster": cluster,
                    "cluster_label": ROLE_CLUSTERS.get(cluster, {}).get("label", "Other"),
                    "cluster_confidence": confidence,
                    "pack_dir": d.get("pack_dir", ""),
                })
            except:
                pass

    # Group by cluster
    clusters = defaultdict(list)
    for j in jobs:
        clusters[j["cluster"]].append(j)

    # Find reusable packs within each cluster
    result = {"updated_at": datetime.now(timezone.utc).isoformat(), "clusters": {}}
    for cluster_key, cluster_jobs in clusters.items():
        reusable = []
        for i, j1 in enumerate(cluster_jobs):
            for j2 in cluster_jobs[i + 1:]:
                sim = compute_similarity(j1, j2)
                if sim >= 0.85 and (j1["pack_dir"] or j2["pack_dir"]):
                    reusable.append({
                        "job_a": j1["title"],
                        "job_b": j2["title"],
                        "similarity": sim,
                        "reuse_pack_from": j1["pack_dir"] or j2["pack_dir"],
                    })

        result["clusters"][cluster_key] = {
            "label": ROLE_CLUSTERS.get(cluster_key, {}).get("label", "Other"),
            "job_count": len(cluster_jobs),
            "reusable_pairs": reusable[:5],  # Top 5
        }

    with open(CLASSIFICATION_FILE, "w") as f:
        json.dump(result, f, indent=2)

    return result


def find_matching_pack(title, jd_text="", location=""):
    """For a new job, check if an existing pack can be reused."""
    if not os.path.exists(CLASSIFICATION_FILE):
        return None

    classification = json.load(open(CLASSIFICATION_FILE))
    cluster, confidence = classify_job(title, jd_text, location)

    if cluster not in classification.get("clusters", {}):
        return None

    # Find the most similar job in this cluster that has a pack
    best_match = None
    best_sim = 0.0
    for job_file in glob.glob(f"{INTAKE_DIR}/*.json"):
        try:
            d = json.load(open(job_file))
            if d.get("status") != "completed" or not d.get("pack_dir"):
                continue
            j_cluster, _ = classify_job(d.get("title", ""), d.get("jd_text", ""), d.get("location", ""))
            if j_cluster != cluster:
                continue
            sim = compute_similarity(
                {"title": title, "company": ""},
                {"title": d.get("title", ""), "company": d.get("company", "")},
            )
            if sim > best_sim:
                best_sim = sim
                best_match = {
                    "cluster": cluster,
                    "cluster_label": ROLE_CLUSTERS.get(cluster, {}).get("label", "Other"),
                    "similarity": sim,
                    "reuse_pack": d.get("pack_dir", ""),
                    "reuse_title": d.get("title", ""),
                    "reuse_company": d.get("company", ""),
                    "recommendation": "REUSE" if sim >= 0.85 else ("SIMILAR" if sim >= 0.6 else "REGENERATE"),
                }
        except:
            pass

    return best_match


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "classify"

    if action == "classify":
        result = build_classifications()
        total_jobs = sum(c["job_count"] for c in result["clusters"].values())
        print(f"Classified {total_jobs} jobs into {len(result['clusters'])} clusters:")
        for key, data in sorted(result["clusters"].items()):
            print(f"  {data['label']}: {data['job_count']} jobs, {len(data['reusable_pairs'])} reusable pairs")

    elif action == "match":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        if not title:
            print("Usage: job_classifier.py match <job_title>")
            sys.exit(1)
        match = find_matching_pack(title)
        if match:
            print(json.dumps(match, indent=2))
        else:
            print("No matching pack found")
