import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib

from app.core.config import settings
from app.core.logging import logger

REGISTRY_DIR = Path(settings.MODEL_REGISTRY_PATH)
META_FILE = REGISTRY_DIR / "registry_meta.json"


class ModelRegistry:
    def __init__(self, registry_dir: Optional[Path] = None) -> None:
        self.registry_dir = registry_dir or REGISTRY_DIR
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.registry_dir / "registry_meta.json"
        self._init_meta()

    def _init_meta(self) -> None:
        if not self.meta_file.exists():
            data = {
                "active_version": None,
                "history": [],
                "versions": {},
            }
            with open(self.meta_file, "w") as f:
                json.dump(data, f, indent=2)

    def _read_meta(self) -> Dict[str, Any]:
        self._init_meta()
        with open(self.meta_file, "r") as f:
            return json.load(f)

    def _write_meta(self, meta: Dict[str, Any]) -> None:
        with open(self.meta_file, "w") as f:
            json.dump(meta, f, indent=2)

    def save_model(
        self,
        version: str,
        models_dict: Dict[str, Any],
        metrics: Dict[str, Any],
        feature_importances: Dict[str, float],
    ) -> str:
        version_dir = self.registry_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = version_dir / "model_bundle.joblib"
        bundle = {
            "version": version,
            "q10": models_dict["model_q10"],
            "q50": models_dict["model_q50"],
            "q90": models_dict["model_q90"],
            "metrics": metrics,
            "feature_importances": feature_importances,
        }
        joblib.dump(bundle, artifact_path)

        meta = self._read_meta()
        meta["versions"][version] = {
            "path": str(artifact_path),
            "metrics": metrics,
            "feature_importances": feature_importances,
            "created_at": str(metrics.get("sample_count", 0)),
        }
        meta["history"].append(version)
        self._write_meta(meta)

        logger.info(f"Model saved to registry as {version}")
        return version

    def get_active_version(self) -> Optional[str]:
        meta = self._read_meta()
        return meta.get("active_version")

    def get_active_model(self) -> Optional[Dict[str, Any]]:
        meta = self._read_meta()
        active_ver = meta.get("active_version")
        if not active_ver:
            return None
        return self.load_model(active_ver)

    def load_model(self, version: str) -> Optional[Dict[str, Any]]:
        meta = self._read_meta()
        ver_info = meta.get("versions", {}).get(version)
        if not ver_info:
            return None
        artifact_path = ver_info["path"]
        if not os.path.exists(artifact_path):
            return None
        return joblib.load(artifact_path)

    def promote(self, version: str) -> bool:
        meta = self._read_meta()
        if version not in meta.get("versions", {}):
            return False
        meta["active_version"] = version
        self._write_meta(meta)
        logger.info(f"Promoted model {version} to active")
        return True

    def rollback(self, target_version: Optional[str] = None) -> Optional[str]:
        meta = self._read_meta()
        history: List[str] = meta.get("history", [])
        current_active = meta.get("active_version")

        if target_version:
            if target_version in meta.get("versions", {}):
                meta["active_version"] = target_version
                self._write_meta(meta)
                return target_version
            return None

        # Pick previous version in history
        if not history:
            return None

        valid_previous = [v for v in history if v != current_active and v in meta.get("versions", {})]
        if not valid_previous:
            return None

        previous_ver = valid_previous[-1]
        meta["active_version"] = previous_ver
        self._write_meta(meta)
        logger.info(f"Rolled back model from {current_active} to {previous_ver}")
        return previous_ver

    def list_versions(self) -> List[str]:
        meta = self._read_meta()
        return list(meta.get("versions", {}).keys())


model_registry = ModelRegistry()
