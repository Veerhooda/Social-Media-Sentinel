"""Platform-independent trend analysis package.

The BERTrend runtime is imported lazily by the service so the FastAPI frequency
fallback can still start when the optional trend dependencies are unavailable.
"""
