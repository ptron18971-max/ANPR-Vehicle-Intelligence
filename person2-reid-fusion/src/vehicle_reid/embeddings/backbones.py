"""Neural network backbones and pooling layers for vehicle Re-ID."""

from typing import Any, Optional
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    torch = None
    nn = None
    F = None
    HAS_TORCH = False

try:
    import timm
    HAS_TIMM = True
except ImportError:
    timm = None
    HAS_TIMM = False


if HAS_TORCH:
    class GeneralizedMeanPoolingP(nn.Module):
        """Generalized Mean Pooling (GeM) layer for Re-ID saliency enhancement."""

        def __init__(self, p: float = 3.0, eps: float = 1e-6):
            super().__init__()
            self.p = nn.Parameter(torch.ones(1) * p)
            self.eps = eps

        def forward(self, x: Any) -> Any:
            return self.gem(x, p=self.p, eps=self.eps)

        def gem(self, x: Any, p: Optional[Any] = None, eps: float = 1e-6) -> Any:
            return F.avg_pool2d(x.clamp(min=eps).pow(p), (x.size(-2), x.size(-1))).pow(1.0 / p)

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}(p={self.p.data.tolist()[0]:.4f}, eps={self.eps})"


    class VehicleReIDNet(nn.Module):
        """Vehicle Re-Identification embedding network with GeM pooling & BNNeck."""

        def __init__(
            self,
            backbone_name: str = "resnet50",
            embedding_dim: int = 512,
            pretrained: bool = True,
            use_gem: bool = True,
        ):
            super().__init__()
            self.backbone_name = backbone_name
            self.embedding_dim = embedding_dim

            if HAS_TIMM:
                self.backbone = timm.create_model(
                    backbone_name,
                    pretrained=pretrained,
                    num_classes=0,  # Remove classifier
                    features_only=True,
                )
                # Determine feature channels
                dummy_in = torch.randn(1, 3, 256, 256)
                with torch.no_grad():
                    features = self.backbone(dummy_in)
                    in_features = features[-1].shape[1]
            else:
                import torchvision.models as models
                if hasattr(models, backbone_name):
                    model_fn = getattr(models, backbone_name)
                    base = model_fn(pretrained=pretrained)
                    self.backbone = nn.Sequential(*list(base.children())[:-2])
                    in_features = 2048 if "resnet50" in backbone_name else 512
                else:
                    raise ValueError(f"Backbone {backbone_name} not available.")

            self.pooling = GeneralizedMeanPoolingP() if use_gem else nn.AdaptiveAvgPool2d((1, 1))

            # Embedding projection head (BNNeck structure standard in ReID)
            self.bottleneck = nn.BatchNorm1d(in_features)
            self.bottleneck.bias.requires_grad_(False)

            if embedding_dim != in_features:
                self.projection = nn.Sequential(
                    nn.Linear(in_features, embedding_dim, bias=False),
                    nn.BatchNorm1d(embedding_dim),
                )
            else:
                self.projection = nn.Identity()

        def forward(self, x: Any) -> Any:
            """Extract normalized embedding vector from batch of images."""
            if HAS_TIMM:
                feat_maps = self.backbone(x)
                feat = feat_maps[-1]
            else:
                feat = self.backbone(x)

            global_feat = self.pooling(feat).flatten(1)
            bn_feat = self.bottleneck(global_feat)
            emb = self.projection(bn_feat)
            # L2 normalize
            return F.normalize(emb, p=2, dim=1)


class MockEmbeddingBackbone:
    """Deterministic feature generator for CPU testing / simulation when PyTorch is not available."""

    def __init__(self, embedding_dim: int = 512):
        self.embedding_dim = embedding_dim

    def generate(self, image_input: any) -> np.ndarray:
        # Create deterministic pseudo-embedding based on pixel statistics
        if isinstance(image_input, np.ndarray):
            mean_val = float(image_input.mean())
            std_val = float(image_input.std())
            seed = int((mean_val * 1000 + std_val * 100) % 100000)
        else:
            seed = 42

        rng = np.random.RandomState(seed)
        vec = rng.randn(self.embedding_dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / (norm + 1e-7)
