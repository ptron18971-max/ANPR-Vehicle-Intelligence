"""Image preprocessing and quality estimation for vehicle Re-ID crops."""

import base64
import io
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    cv2 = None
    HAS_OPENCV = False

try:
    import torch
    from torchvision import transforms
    HAS_TORCH = True
except ImportError:
    torch = None
    transforms = None
    HAS_TORCH = False


class VehicleImagePreprocessor:
    """Preprocesses vehicle image crops for deep feature extraction and evaluates crop quality."""

    def __init__(
        self,
        image_size: Tuple[int, int] = (256, 256),
        use_clahe: bool = False,
        mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
        std: Tuple[float, float, float] = (0.229, 0.224, 0.225),
    ):
        """Initialize preprocessor.

        Args:
            image_size: Target (height, width) for model input. Default (256, 256).
            use_clahe: Whether to apply CLAHE contrast enhancement.
            mean: Normalization mean for (R, G, B).
            std: Normalization standard deviation for (R, G, B).
        """
        self.image_size = image_size
        self.use_clahe = use_clahe
        self.mean = np.array(mean, dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array(std, dtype=np.float32).reshape(1, 1, 3)

        if HAS_TORCH:
            self.torch_transform = transforms.Compose([
                transforms.Resize(self.image_size, interpolation=transforms.InterpolationMode.BICUBIC),
                transforms.ToTensor(),
                transforms.Normalize(mean=mean, std=std),
            ])
        else:
            self.torch_transform = None

    def load_image(self, image_input: Any) -> Image.Image:
        """Convert various input formats into a PIL RGB Image."""
        if isinstance(image_input, Image.Image):
            return image_input.convert("RGB")

        if isinstance(image_input, (str, Path)):
            path_str = str(image_input)
            if path_str.startswith("data:image") and "base64," in path_str:
                # Base64 data URL
                encoded_data = path_str.split("base64,")[1]
                image_bytes = base64.b64decode(encoded_data)
                return Image.open(io.BytesIO(image_bytes)).convert("RGB")
            # Local file path
            return Image.open(path_str).convert("RGB")

        if isinstance(image_input, np.ndarray):
            # If 2D grayscale
            if image_input.ndim == 2:
                return Image.fromarray(image_input).convert("RGB")
            # If 3D array: assume BGR if opencv shape (H, W, 3), convert to RGB
            if image_input.ndim == 3 and image_input.shape[2] == 3:
                # Check if values are in 0-255 float/int
                if image_input.dtype == np.uint8:
                    return Image.fromarray(image_input[:, :, ::-1], mode="RGB")
                else:
                    arr = np.clip(image_input * 255 if image_input.max() <= 1.0 else image_input, 0, 255).astype(np.uint8)
                    return Image.fromarray(arr[:, :, ::-1], mode="RGB")

        if HAS_TORCH and isinstance(image_input, torch.Tensor):
            t = image_input.detach().cpu()
            if t.ndim == 3 and t.shape[0] in (1, 3):
                t = t.permute(1, 2, 0).numpy()
                arr = np.clip(t * 255 if t.max() <= 1.0 else t, 0, 255).astype(np.uint8)
                return Image.fromarray(arr).convert("RGB")

        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    def apply_clahe(self, pil_img: Image.Image) -> Image.Image:
        """Apply Contrast Limited Adaptive Histogram Equalization to the luminance channel."""
        if not HAS_OPENCV:
            return pil_img

        rgb = np.array(pil_img)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        final_rgb = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
        return Image.fromarray(final_rgb)

    def estimate_quality(self, pil_img: Image.Image) -> float:
        """Compute an image quality score in [0.0, 1.0] based on resolution and Laplacian sharpness.

        Returns:
            float: Quality score between 0.0 (unusable/blurry) and 1.0 (crisp, high-res crop).
        """
        w, h = pil_img.size
        # 1. Resolution score: optimal when width & height >= 128px
        min_dim = min(w, h)
        res_score = min(1.0, min_dim / 128.0)

        # 2. Sharpness score via Laplacian variance
        sharpness_score = 0.5
        if HAS_OPENCV:
            gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Empirical calibration: variance > 300 is sharp, < 30 is very blurry
            sharpness_score = float(np.clip((lap_var - 20.0) / 280.0, 0.0, 1.0))

        # Weighted combination: 40% resolution, 60% sharpness
        quality = 0.4 * res_score + 0.6 * sharpness_score
        return round(float(np.clip(quality, 0.05, 1.0)), 3)

    def preprocess_numpy(self, image_input: Any) -> Tuple[np.ndarray, float]:
        """Preprocess to normalized numpy array of shape (3, H, W)."""
        pil_img = self.load_image(image_input)
        quality = self.estimate_quality(pil_img)

        if self.use_clahe:
            pil_img = self.apply_clahe(pil_img)

        pil_img = pil_img.resize((self.image_size[1], self.image_size[0]), Image.BICUBIC)
        arr = np.array(pil_img, dtype=np.float32) / 255.0  # (H, W, 3)
        arr = (arr - self.mean) / self.std
        tensor_arr = np.transpose(arr, (2, 0, 1))  # (3, H, W)
        return tensor_arr, quality

    def preprocess_torch(self, image_input: Any) -> Tuple[Any, float]:
        """Preprocess to normalized PyTorch tensor of shape (3, H, W)."""
        if not HAS_TORCH:
            arr, quality = self.preprocess_numpy(image_input)
            return arr, quality

        pil_img = self.load_image(image_input)
        quality = self.estimate_quality(pil_img)

        if self.use_clahe:
            pil_img = self.apply_clahe(pil_img)

        tensor = self.torch_transform(pil_img)
        return tensor, quality
