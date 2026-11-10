from app.services.evaluation_service import run_evaluation


def test_run_evaluation_benchmark():
    res = run_evaluation(top_k=3)
    metrics = res["metrics"]

    assert metrics["total_samples"] == 4
    assert metrics["mrr"] > 0.0
    assert metrics["hit_rate_1"] > 0.0
    assert metrics["hit_rate_3"] >= metrics["hit_rate_1"]
    assert metrics["avg_faithfulness"] > 0.0
    assert metrics["ndcg_at_k"] >= 0.0
    assert metrics["ndcg_at_k"] <= 1.0
    assert len(res["sample_details"]) == 4
    # Verify NDCG@K present in sample details
    for sample in res["sample_details"]:
        assert "ndcg_at_k" in sample
        assert 0.0 <= sample["ndcg_at_k"] <= 1.0


async def test_evaluation_api_workflow(client, operator_headers, viewer_headers):
    # Run evaluation via API
    run_resp = await client.post("/api/evaluation/run", json={"dataset_name": "rag-benchmark-v1", "top_k": 3}, headers=operator_headers)
    assert run_resp.status_code == 200
    data = run_resp.json()
    assert data["dataset_name"] == "rag-benchmark-v1"
    assert data["metrics"]["mrr"] > 0.0
    assert "ndcg_at_k" in data["metrics"]
    assert 0.0 <= data["metrics"]["ndcg_at_k"] <= 1.0

    # View history via API
    hist_resp = await client.get("/api/evaluation/history", headers=viewer_headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) >= 1


# Test for calculate_ndcg_at_k function
from app.services.evaluation_service import calculate_ndcg_at_k

def test_calculate_ndcg_at_k():
    # Perfect ranking - relevant item at position 1
    assert calculate_ndcg_at_k([1.0, 0.0, 0.0], 3) == 1.0
    
    # Relevant item at position 2
    ndcg = calculate_ndcg_at_k([0.0, 1.0, 0.0], 3)
    expected = (1.0 / math.log2(3)) / (1.0 / math.log2(2))  # DCG / IDCG
    assert abs(ndcg - expected) < 1e-10
    
    # No relevant items
    assert calculate_ndcg_at_k([0.0, 0.0, 0.0], 3) == 0.0
    
    # Empty list
    assert calculate_ndcg_at_k([], 3) == 0.0
    
    # k=0
    assert calculate_ndcg_at_k([1.0, 0.0], 0) == 0.0
    
    # Multiple relevant items (graded relevance)
    ndcg = calculate_ndcg_at_k([0.8, 1.0, 0.5, 0.0], 4)
    # Ideal order: [1.0, 0.8, 0.5, 0.0]
    ideal_dcg = 1.0/math.log2(2) + 0.8/math.log2(3) + 0.5/math.log2(4)
    actual_dcg = 0.8/math.log2(2) + 1.0/math.log2(3) + 0.5/math.log2(4)
    expected = actual_dcg / ideal_dcg
    assert abs(ndcg - expected) < 1e-10

import math
