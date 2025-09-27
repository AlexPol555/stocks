from __future__ import annotations


class PipelineError(Exception):
    """Base exception for the news pipeline."""


class RetryablePipelineError(PipelineError):
    """Raised when a chunk can be retried."""


class EmbeddingBackendError(PipelineError):
    """Raised when the embedding backend fails irrecoverably."""


__all__ = ["PipelineError", "RetryablePipelineError", "EmbeddingBackendError"]
