# rag_agent/evaluation/metrics.py
# real evaluation metrics functions (BLEU, F1, ROUGE 등)

# from rouge_score import rouge_score
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


def calculate_metrics(predictions, references):
    """Calculate evaluation metrics"""
    accuracy = accuracy_score(references, predictions)
    f1 = f1_score(references, predictions, average="macro")
    precision = precision_score(references, predictions, average="macro")
    recall = recall_score(references, predictions, average="macro")
    return accuracy, f1, precision, recall
