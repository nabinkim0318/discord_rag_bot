# rag_agent/evaluation/cli_eval.py
"""entrypoint to run evaluation pipeline from CLI(Command-line interface).
→ ✅ role: python cli_eval.py --input ... forma run
"""

import argparse
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List

# import evaluation utility (if implemented)
# from rag_agent.evaluation.evaluation_utils import evaluate_response


def load_test_dataset(input_path: str) -> List[Dict[str, Any]]:
    """load test dataset"""
    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        if input_path.endswith(".json"):
            return json.load(f)
        else:
            # support CSV or other formats
            print(f"❌ Unsupported file format: {input_path}")
            sys.exit(1)


def evaluate_rag_pipeline(
    test_cases: List[Dict[str, Any]],
    prompt_version: str = "v1.1",
    output_dir: str = "evaluation_results",
) -> Dict[str, Any]:
    """RAG pipeline evaluation execution"""

    results = {
        "evaluation_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "prompt_version": prompt_version,
        "total_cases": len(test_cases),
        "results": [],
        "metrics": {
            "accuracy": 0.0,
            "relevance": 0.0,
            "completeness": 0.0,
            "average_response_time": 0.0,
        },
    }

    total_time = 0
    correct_answers = 0

    print(f"🚀 Starting evaluation with {len(test_cases)} test cases...")
    print(f"📝 Using prompt version: {prompt_version}")

    for i, test_case in enumerate(test_cases, 1):
        print(
            f"📋 Processing case {i}/{len(test_cases)}: \
            {test_case.get('query', 'Unknown')[:50]}..."
        )

        start_time = time.time()

        # actual RAG pipeline call (mocked here)
        try:
            # from backend.app.services.rag_service import run_rag_pipeline
            # answer, contexts, metadata = run_rag_pipeline(
            #     test_case["query"],
            #     prompt_version=prompt_version
            # )

            # mocked response (use above code if implemented)
            answer = f"Mock answer for: {test_case['query']}"
            contexts = ["Mock context 1", "Mock context 2"]
            metadata = {"prompt_version": prompt_version, "model": "mock-llm"}

            response_time = time.time() - start_time
            total_time += response_time

            # calculate evaluation metrics (more sophisticated evaluation
            # if implemented)
            is_correct = "mock" in answer.lower()  # simple mocked evaluation
            if is_correct:
                correct_answers += 1

            case_result = {
                "case_id": i,
                "query": test_case["query"],
                "expected_answer": test_case.get("expected_answer", ""),
                "actual_answer": answer,
                "contexts": contexts,
                "response_time": response_time,
                "is_correct": is_correct,
                "metadata": metadata,
            }

            results["results"].append(case_result)

        except Exception as e:
            print(f"❌ Error processing case {i}: {str(e)}")
            case_result = {
                "case_id": i,
                "query": test_case["query"],
                "error": str(e),
                "response_time": time.time() - start_time,
            }
            results["results"].append(case_result)

    # calculate overall metrics
    results["metrics"]["accuracy"] = (
        correct_answers / len(test_cases) if test_cases else 0
    )
    results["metrics"]["average_response_time"] = (
        total_time / len(test_cases) if test_cases else 0
    )
    results["metrics"]["relevance"] = 0.85  # mocked value
    results["metrics"]["completeness"] = 0.78  # mocked value

    return results


def save_results(results: Dict[str, Any], output_dir: str) -> str:
    """save evaluation results"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"evaluation_{results['prompt_version']}_{timestamp}.json"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return output_path


def main():
    """CLI main function"""
    parser = argparse.ArgumentParser(description="RAG Pipeline Evaluation CLI")
    parser.add_argument(
        "--input", "-i", required=True, help="Input test dataset file (JSON)"
    )
    parser.add_argument(
        "--prompt-version", "-v", default="v1.1", help="Prompt version to test"
    )
    parser.add_argument(
        "--output-dir", "-o", default="evaluation_results", help="Output directory"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("🔍 RAG Pipeline Evaluation Tool")
    print("=" * 50)

    # load test dataset
    test_cases = load_test_dataset(args.input)
    print(f"✅ Loaded {len(test_cases)} test cases")

    # execute evaluation
    results = evaluate_rag_pipeline(test_cases, args.prompt_version, args.output_dir)

    # save results
    output_path = save_results(results, args.output_dir)

    # print results summary
    print("\n📊 Evaluation Results Summary")
    print("=" * 50)
    print(f"📝 Prompt Version: {results['prompt_version']}")
    print(f"📋 Total Cases: {results['total_cases']}")
    print(f"✅ Accuracy: {results['metrics']['accuracy']:.2%}")
    print(f"⏱️  Avg Response Time: {results['metrics']['average_response_time']:.2f}s")
    print(f"📁 Results saved to: {output_path}")

    # CI/CD results file (Prometheus metric format)
    ci_output_path = os.path.join(args.output_dir, "evaluation_metrics.json")
    ci_metrics = {
        "rag_evaluation_accuracy": results["metrics"]["accuracy"],
        "rag_evaluation_avg_response_time": results["metrics"]["average_response_time"],
        "rag_evaluation_total_cases": results["total_cases"],
        "rag_evaluation_prompt_version": results["prompt_version"],
    }

    with open(ci_output_path, "w") as f:
        json.dump(ci_metrics, f)

    print(f"📈 CI metrics saved to: {ci_output_path}")

    # return success/failure code
    success_threshold = 0.7  # 70% accuracy threshold
    if results["metrics"]["accuracy"] >= success_threshold:
        print("🎉 Evaluation passed!")
        sys.exit(0)
    else:
        print(f"❌ Evaluation failed (accuracy < {success_threshold:.0%})")
        sys.exit(1)


if __name__ == "__main__":
    main()
