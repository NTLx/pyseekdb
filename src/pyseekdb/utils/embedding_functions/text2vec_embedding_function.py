"""
Text2Vec embedding function for pyseekdb.

This module provides an embedding function using the text2vec library,
which is a powerful multilingual embedding model trained on HuggingFace.
"""

from typing import Any, ClassVar
from pyseekdb.client.embedding_function import (
    Documents,
    EmbeddingFunction,
    Embeddings,
)


class Text2VecEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    An embedding function using text2vec with a specific model.

    Text2Vec provides multilingual embeddings (supports 100+ languages) with
    various pretrained models.
    """

    # Class variable to cache loaded models
    models: ClassVar[dict[str, Any]] = {}

    def __init__(
        self,
        model_name: str = "shibing624/text2vec-base-chinese",
        device: str = "cpu",
        normalize_embeddings: bool = False,
        **kwargs: Any,
    ):
        """Initialize Text2VecEmbeddingFunction."""
        # Validate kwargs - only allow primitive types
        for key, value in kwargs.items():
            if not isinstance(value, (str, int, float, bool, list, dict, tuple)):
                raise TypeError(f"Keyword argument {key} is not a primitive type")

        self.model_name = model_name
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        self.kwargs = kwargs

        # Lazy import - only load text2vec when needed
        if model_name not in self.models:
            try:
                from text2vec import SentenceModel
                # Initialize the model
                self.models[model_name] = SentenceModel(
                    model_name_or_path=model_name,
                    device=device,
                    **kwargs
                )
            except ImportError as exc:
                raise ValueError(
                    "The text2vec python package is not installed. "
                    "Please install it with: `pip install text2vec`"
                ) from exc

        # Get the actual model instance
        self._model = self.models[model_name]

    @property
    def dimension(self) -> int:
        """Get the dimension of embeddings produced by this function."""
        # Get dimension from the model's encoding directly if possible
        # Or try encoding a dummy string
        sample = self._model.encode("test", normalize_embeddings=self.normalize_embeddings)
        if hasattr(sample, 'shape'):
            return sample.shape[0] if len(sample.shape) == 1 else sample.shape[1]
        return len(sample)

    def __call__(self, documents: Documents) -> Embeddings:
        """Generate embeddings for given documents."""
        # Handle single string input
        if isinstance(documents, str):
            documents = [documents]

        # Handle empty input
        if not documents:
            return []

        # Generate embeddings using text2vec
        # text2vec's encode returns numpy array or list based on implementation
        embeddings = self._model.encode(
            list(documents),
            normalize_embeddings=self.normalize_embeddings,
        )

        # Convert to list of lists
        if hasattr(embeddings, 'tolist'):
            return embeddings.tolist()
        return list(embeddings)

    @staticmethod
    def name() -> str:
        """Return the embedding function name identifier."""
        return "text2vec"

    def get_config(self) -> dict[str, Any]:
        """Get configuration dictionary for serialization."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "normalize_embeddings": self.normalize_embeddings,
            "kwargs": self.kwargs,
        }

    @staticmethod
    def build_from_config(
        config: dict[str, Any],
    ) -> "Text2VecEmbeddingFunction":
        """Build Text2VecEmbeddingFunction from configuration dictionary."""
        model_name = config.get("model_name", "shibing624/text2vec-base-chinese")
        device = config.get("device", "cpu")
        normalize_embeddings = config.get("normalize_embeddings", False)
        kwargs = config.get("kwargs", {})

        if not isinstance(kwargs, dict):
            raise TypeError(f"kwargs must be a dictionary, but got {kwargs}")

        return Text2VecEmbeddingFunction(
            model_name=model_name,
            device=device,
            normalize_embeddings=normalize_embeddings,
            **kwargs,
        )
