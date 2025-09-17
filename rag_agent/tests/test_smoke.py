import importlib


def test_import_pipelines():
    # Ensure main modules import without side effects
    for mod in [
        "ingestion.pipeline",
        "retrieval.pipeline",
        "generation.pipeline",
    ]:
        importlib.import_module(mod)
