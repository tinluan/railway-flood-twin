"""
src/engine/hecras_hdf5_reader.py — HEC-RAS HDF5 Result Reader (Layer 3)
========================================================================
Pure-Python reader for pre-computed HEC-RAS 2D results stored in HDF5 files.
This module does NOT require HEC-RAS to be installed — it reads directly from
the plan output HDF5 files (.p01.hdf, .p02.hdf).

Architecture Position (Layer 3 — Simulation Engine):
    - READS:   data/New_data/HEC_RAS/CAPSTONE_JN_L752_PK.p01.hdf  (Plan 1: R100_1HR)
               data/New_data/HEC_RAS/CAPSTONE_JN_L752_PK.p02.hdf  (Plan 2: 21092025)
    - WRITES:  data/processed/hecras_wse_results.json  (WSE per asset per timestep)
    - FEEDS:   src/engine/fragility_curves.py  (water_depth = WSE - z_terrain)
               src/dashboard/app_main.py       (WSE chart, flood map)
               src/api/main.py                 (alert endpoints)

Difference vs hecras_bridge.py:
    hecras_bridge.py   → Needs HEC-RAS COM (Windows + HEC-RAS installed), runs live
    hecras_hdf5_reader → Reads pre-computed HDF5, cross-platform, no HEC-RAS needed

HDF5 Internal Structure (per plan .hdf):
    Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/
        Time Date Stamp          → (N_timesteps,)  e.g. b'30MAR2026 13:00:00'
        2D Flow Areas/PK534_FA_5M2/
            Water Surface        → (N_timesteps, N_cells) float32, WSE in metres NGF
            Face Velocity        → (N_timesteps, N_faces) float32, m/s
            Cell Cumulative Precipitation Depth → (N_timesteps, N_cells) float32, mm
    Geometry/2D Flow Areas/PK534_FA_5M2/
        Cells Center Coordinate  → (N_cells, 2) float64, Lambert 93 X,Y
        Cells Minimum Elevation  → (N_cells,)  float32, min terrain Z per cell
    Geometry/Structures/Attributes → 9 SA/2D connections (culverts under railway)

Dependency:
    pip install h5py numpy

Authors: TRAN Trong-Tin (Antigravity-generated)
Project: SNCF Railway Flood-Risk Digital Twin (Master Capstone)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import h5py
import numpy as np

logger = logging.getLogger(__name__)


# ======================================================================
# HDF5 path constants (HEC-RAS 6.x output structure)
# ======================================================================
_BASE_OUTPUT = "Results/Unsteady/Output/Output Blocks/Base Output"
_UTS = f"{_BASE_OUTPUT}/Unsteady Time Series"
_2D_FA = f"{_UTS}/2D Flow Areas"
_GEOM_2D = "Geometry/2D Flow Areas"
_STRUCTURES = "Geometry/Structures"


class HECRASResult:
    """Container for a single timestep of 2D HEC-RAS results."""

    def __init__(self, timestamp: str, wse: np.ndarray,
                 velocity: Optional[np.ndarray] = None,
                 precipitation: Optional[np.ndarray] = None):
        self.timestamp = timestamp
        self.wse = wse                    # (N_cells,) Water Surface Elevation
        self.velocity = velocity          # (N_faces,) Face velocity (optional)
        self.precipitation = precipitation  # (N_cells,) Cumulative precip (optional)


class HECRASPlanReader:
    """
    Reads pre-computed HEC-RAS 2D plan results from an HDF5 file.

    Usage:
        reader = HECRASPlanReader("data/New_data/HEC_RAS/CAPSTONE_JN_L752_PK.p01.hdf")
        reader.open()

        # Get metadata
        print(reader.flow_area_name)   # 'PK534_FA_5M2'
        print(reader.n_cells)          # 950122
        print(reader.n_timesteps)      # 13
        print(reader.timestamps)       # ['30MAR2026 13:00:00', ...]

        # Get cell coordinates (Lambert 93)
        centers = reader.cell_centers   # (N_cells, 2) X,Y

        # Get WSE at all cells for a specific timestep
        wse = reader.get_wse(timestep_idx=5)  # (N_cells,)

        # Get WSE at a specific X,Y location across all timesteps
        wse_ts = reader.get_wse_at_point(x=852400, y=6397800)
        # Returns: [(timestamp, wse_value), ...]

        # Get WSE at multiple asset locations
        assets = {"Buse_0": (852350, 6397750), "Voie_seg_01": (852400, 6397800)}
        results = reader.get_wse_at_assets(assets)
        # Returns: {"Buse_0": [(ts, wse), ...], "Voie_seg_01": [(ts, wse), ...]}

        # Export to project-compatible JSON
        reader.export_wse_json("data/processed/hecras_wse_results.json", assets)

        reader.close()
    """

    def __init__(self, hdf5_path: Union[str, Path]):
        self._path = Path(hdf5_path)
        self._f: Optional[h5py.File] = None
        self._flow_area_name: Optional[str] = None
        self._cell_centers: Optional[np.ndarray] = None
        self._cell_min_elev: Optional[np.ndarray] = None
        self._timestamps: Optional[List[str]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def open(self):
        """Open the HDF5 file and discover the 2D flow area."""
        if self._f is not None:
            return
        if not self._path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {self._path}")

        self._f = h5py.File(str(self._path), 'r')
        logger.info(f"Opened HEC-RAS HDF5: {self._path.name}")

        # Auto-discover the 2D flow area name
        fa_group = self._f[_GEOM_2D]
        attrs = fa_group['Attributes'][:]
        self._flow_area_name = attrs[0]['Name'].decode().strip()
        logger.info(f"Flow area: {self._flow_area_name}")

    def close(self):
        """Close the HDF5 file."""
        if self._f is not None:
            self._f.close()
            self._f = None
            logger.info("HDF5 file closed.")

    def refresh_from_latest_run(self):
        """
        Invalidates cached data and reopens the HDF5 file.
        Use this after triggering a new HEC-RAS computation.
        """
        self.close()
        # Reset lazy-loaded properties
        self._flow_area_name = None
        self._cell_centers = None
        self._cell_min_elev = None
        self._timestamps = None
        
        logger.info("Caches invalidated. Ready to read fresh HEC-RAS results.")
        self.open()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ------------------------------------------------------------------
    # Properties (lazy-loaded)
    # ------------------------------------------------------------------
    @property
    def flow_area_name(self) -> str:
        """Name of the 2D flow area (e.g. 'PK534_FA_5M2')."""
        self._ensure_open()
        return self._flow_area_name

    @property
    def cell_centers(self) -> np.ndarray:
        """(N_cells, 2) array of cell center coordinates in Lambert 93."""
        self._ensure_open()
        if self._cell_centers is None:
            path = f"{_GEOM_2D}/{self._flow_area_name}/Cells Center Coordinate"
            self._cell_centers = self._f[path][:]
            logger.info(f"Loaded {len(self._cell_centers)} cell centers")
        return self._cell_centers

    @property
    def cell_min_elevation(self) -> np.ndarray:
        """(N_cells,) array of minimum terrain elevation per cell."""
        self._ensure_open()
        if self._cell_min_elev is None:
            path = f"{_GEOM_2D}/{self._flow_area_name}/Cells Minimum Elevation"
            self._cell_min_elev = self._f[path][:]
        return self._cell_min_elev

    @property
    def n_cells(self) -> int:
        """Number of 2D mesh cells."""
        return len(self.cell_centers)

    @property
    def timestamps(self) -> List[str]:
        """List of output timestamp strings."""
        self._ensure_open()
        if self._timestamps is None:
            path = f"{_UTS}/Time Date Stamp"
            raw = self._f[path][:]
            self._timestamps = [ts.decode().strip() for ts in raw]
            logger.info(f"Found {len(self._timestamps)} timesteps: "
                        f"{self._timestamps[0]} to {self._timestamps[-1]}")
        return self._timestamps

    @property
    def n_timesteps(self) -> int:
        """Number of output timesteps."""
        return len(self.timestamps)

    # ------------------------------------------------------------------
    # Structures (culverts/bridges in the HEC-RAS model)
    # ------------------------------------------------------------------
    @property
    def structures(self) -> List[Dict]:
        """List of SA/2D connection structures (culverts, bridges)."""
        self._ensure_open()
        if _STRUCTURES not in self._f:
            return []
        attrs = self._f[f"{_STRUCTURES}/Attributes"][:]
        result = []
        for a in attrs:
            result.append({
                'type': a['Type'].decode().strip(),
                'name': a['Node Name'].decode().strip(),
                'connection': a['Connection'].decode().strip(),
                'group': a['Groupname'].decode().strip(),
            })
        return result

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------
    def get_wse(self, timestep_idx: int = -1) -> np.ndarray:
        """
        Get Water Surface Elevation for all cells at a given timestep.

        Args:
            timestep_idx: 0-based index, or -1 for last timestep.

        Returns:
            (N_cells,) float32 array of WSE in metres NGF.
        """
        self._ensure_open()
        path = f"{_2D_FA}/{self._flow_area_name}/Water Surface"
        return self._f[path][timestep_idx, :]

    def get_depth(self, timestep_idx: int = -1) -> np.ndarray:
        """
        Get water depth for all cells at a given timestep.
        Depth = WSE - Cell Minimum Elevation. Clamped to >= 0.

        Returns:
            (N_cells,) float32 array of depth in metres.
        """
        wse = self.get_wse(timestep_idx)
        z_min = self.cell_min_elevation
        depth = wse - z_min
        depth[depth < 0] = 0.0
        depth[np.isnan(depth)] = 0.0
        return depth

    def get_max_wse(self) -> np.ndarray:
        """
        Get the maximum WSE across all timesteps for each cell.

        Returns:
            (N_cells,) float32 array of maximum WSE.
        """
        self._ensure_open()
        path = f"{_2D_FA}/{self._flow_area_name}/Water Surface"
        wse_all = self._f[path][:]  # (N_timesteps, N_cells)
        return np.nanmax(wse_all, axis=0)

    def get_max_depth(self) -> np.ndarray:
        """
        Get the maximum water depth across all timesteps for each cell.

        Returns:
            (N_cells,) float32 array of maximum depth.
        """
        self._ensure_open()
        path = f"{_2D_FA}/{self._flow_area_name}/Water Surface"
        wse_all = self._f[path][:]  # (N_timesteps, N_cells)
        z_min = self.cell_min_elevation
        depth_all = wse_all - z_min[np.newaxis, :]
        depth_all[depth_all < 0] = 0.0
        depth_all[np.isnan(depth_all)] = 0.0
        return np.max(depth_all, axis=0)

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------
    def find_nearest_cell(self, x: float, y: float) -> Tuple[int, float]:
        """
        Find the nearest mesh cell to a given point.

        Args:
            x, y: Coordinates in Lambert 93 (EPSG:2154).

        Returns:
            Tuple of (cell_index, distance_m).
        """
        centers = self.cell_centers
        dx = centers[:, 0] - x
        dy = centers[:, 1] - y
        dist_sq = dx * dx + dy * dy
        idx = int(np.argmin(dist_sq))
        return idx, float(np.sqrt(dist_sq[idx]))

    def get_wse_at_point(self, x: float, y: float,
                         max_dist: float = 50.0) -> List[Tuple[str, float]]:
        """
        Get WSE time-series at the nearest cell to a given point.

        Args:
            x, y: Lambert 93 coordinates.
            max_dist: Maximum acceptable distance to nearest cell (m).

        Returns:
            List of (timestamp, wse_value) tuples. Empty if no cell within max_dist.
        """
        self._ensure_open()
        cell_idx, dist = self.find_nearest_cell(x, y)

        if dist > max_dist:
            logger.warning(f"No cell within {max_dist}m of ({x:.1f}, {y:.1f}). "
                           f"Nearest cell is {dist:.1f}m away.")
            return []

        path = f"{_2D_FA}/{self._flow_area_name}/Water Surface"
        wse_series = self._f[path][:, cell_idx]
        timestamps = self.timestamps

        return [(ts, round(float(wse), 4)) for ts, wse in zip(timestamps, wse_series)
                if not np.isnan(wse)]

    def get_wse_at_assets(
        self,
        asset_coords: Dict[str, Tuple[float, float]],
        max_dist: float = 50.0
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        Get WSE time-series at multiple asset locations.

        Args:
            asset_coords: Dict mapping asset_key -> (x, y) in Lambert 93.
            max_dist: Maximum distance to nearest cell.

        Returns:
            Dict mapping asset_key -> list of (timestamp, wse) tuples.
        """
        results = {}
        for asset_key, (x, y) in asset_coords.items():
            wse_ts = self.get_wse_at_point(x, y, max_dist)
            results[asset_key] = wse_ts
            if wse_ts:
                peak = max(wse_ts, key=lambda t: t[1])
                logger.info(f"  {asset_key}: peak WSE = {peak[1]:.2f}m at {peak[0]}")
            else:
                logger.warning(f"  {asset_key}: no HEC-RAS cell coverage")
        return results

    # ------------------------------------------------------------------
    # Export to project JSON format
    # ------------------------------------------------------------------
    def export_wse_json(
        self,
        output_path: Union[str, Path],
        asset_coords: Dict[str, Tuple[float, float]],
        max_dist: float = 50.0
    ) -> Dict:
        """
        Export WSE results in the format expected by the dashboard and API.

        Output format (compatible with existing hecras_wse_results.json):
        {
            "plan": "R100_1HR",
            "flow_area": "PK534_FA_5M2",
            "timesteps": ["30MAR2026 13:00:00", ...],
            "assets": {
                "Buse_0": {
                    "x": 852350.0, "y": 6397750.0,
                    "cell_idx": 12345, "cell_dist_m": 2.3,
                    "wse": [210.5, 210.8, 211.2, ...],
                    "peak_wse": 212.1,
                    "peak_timestep": "30MAR2026 13:30:00"
                },
                ...
            }
        }
        """
        self._ensure_open()
        timestamps = self.timestamps

        # Build per-asset results
        assets_out = {}
        path = f"{_2D_FA}/{self._flow_area_name}/Water Surface"
        wse_all = self._f[path][:]  # (N_timesteps, N_cells)

        for asset_key, (x, y) in asset_coords.items():
            cell_idx, dist = self.find_nearest_cell(x, y)

            if dist > max_dist:
                logger.warning(f"Skipping {asset_key}: nearest cell is {dist:.1f}m away")
                continue

            wse_series = wse_all[:, cell_idx].tolist()
            # Replace NaN with None for JSON
            wse_series = [round(v, 4) if not np.isnan(v) else None for v in wse_series]

            valid_wse = [(ts, w) for ts, w in zip(timestamps, wse_series)
                         if w is not None]
            if valid_wse:
                peak_ts, peak_wse = max(valid_wse, key=lambda t: t[1])
            else:
                peak_ts, peak_wse = None, None

            assets_out[asset_key] = {
                "x": round(x, 1),
                "y": round(y, 1),
                "cell_idx": cell_idx,
                "cell_dist_m": round(dist, 2),
                "wse": wse_series,
                "peak_wse": peak_wse,
                "peak_timestep": peak_ts,
            }

        result = {
            "plan": self._path.stem.split('.')[-1],
            "flow_area": self._flow_area_name,
            "source_file": self._path.name,
            "timesteps": timestamps,
            "n_cells": self.n_cells,
            "n_timesteps": self.n_timesteps,
            "structures": self.structures,
            "assets": assets_out,
        }

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8') as fp:
            json.dump(result, fp, indent=2, ensure_ascii=False)
        logger.info(f"WSE results exported to {out} "
                    f"({len(assets_out)} assets, {self.n_timesteps} timesteps)")

        return result

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------
    def get_flood_summary(self) -> Dict:
        """
        Get a summary of flood extent and depth across all timesteps.

        Returns:
            Dict with max_depth, flooded_area, peak_timestep, etc.
        """
        self._ensure_open()
        path = f"{_2D_FA}/{self._flow_area_name}/Water Surface"
        wse_all = self._f[path][:]
        z_min = self.cell_min_elevation

        # Compute depth per timestep
        depth_all = wse_all - z_min[np.newaxis, :]
        depth_all[depth_all < 0] = 0.0
        depth_all[np.isnan(depth_all)] = 0.0

        # Cell surface areas for flooded area calculation
        area_path = f"{_GEOM_2D}/{self._flow_area_name}/Cells Surface Area"
        if area_path in self._f:
            cell_areas = self._f[area_path][:]
        else:
            cell_areas = np.full(self.n_cells, 25.0)  # Assume 5m x 5m default

        # Per-timestep statistics
        timestep_stats = []
        for t_idx in range(self.n_timesteps):
            d = depth_all[t_idx, :]
            flooded_mask = d > 0.01  # > 1cm
            flooded_area = float(np.sum(cell_areas[flooded_mask]))
            max_depth = float(np.max(d))
            mean_depth = float(np.mean(d[flooded_mask])) if flooded_mask.any() else 0.0

            timestep_stats.append({
                "timestamp": self.timestamps[t_idx],
                "max_depth_m": round(max_depth, 3),
                "mean_depth_m": round(mean_depth, 3),
                "flooded_area_m2": round(flooded_area, 1),
                "flooded_cells": int(np.sum(flooded_mask)),
            })

        # Overall peak
        max_depths = [s['max_depth_m'] for s in timestep_stats]
        peak_idx = int(np.argmax(max_depths))

        return {
            "flow_area": self._flow_area_name,
            "n_cells": self.n_cells,
            "n_timesteps": self.n_timesteps,
            "peak_timestep": timestep_stats[peak_idx]["timestamp"],
            "peak_max_depth_m": timestep_stats[peak_idx]["max_depth_m"],
            "peak_flooded_area_m2": timestep_stats[peak_idx]["flooded_area_m2"],
            "timesteps": timestep_stats,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_open(self):
        if self._f is None:
            raise RuntimeError("HDF5 file not open. Call open() or use context manager.")


# ======================================================================
# Convenience functions
# ======================================================================

def list_available_plans(hecras_dir: Union[str, Path]) -> List[Dict]:
    """
    List all HEC-RAS plan HDF5 files in a directory.

    Returns:
        List of dicts with plan metadata.
    """
    hecras_dir = Path(hecras_dir)
    plans = []
    for hdf_file in sorted(hecras_dir.glob("*.p??.hdf")):
        try:
            with h5py.File(str(hdf_file), 'r') as f:
                # Get timestamps
                ts_path = f"{_UTS}/Time Date Stamp"
                if ts_path in f:
                    timestamps = [t.decode().strip() for t in f[ts_path][:]]
                else:
                    timestamps = []

                plans.append({
                    "file": hdf_file.name,
                    "path": str(hdf_file),
                    "size_mb": round(hdf_file.stat().st_size / 1e6, 1),
                    "n_timesteps": len(timestamps),
                    "start": timestamps[0] if timestamps else "?",
                    "end": timestamps[-1] if timestamps else "?",
                })
        except Exception as e:
            logger.warning(f"Could not read {hdf_file.name}: {e}")

    return plans


def extract_downsampled_flow_data(
    hdf5_path: Union[str, Path],
    timestep_idx: int,
    max_cells: int = 5000,
    depth_threshold: float = 0.02,
    dry_sample_rate: int = 50,
) -> Dict:
    """
    Extract a downsampled, WGS84-projected snapshot of flood depth from a
    HEC-RAS HDF5 output file. Designed for the F4 2D Flow Map Overlay panel
    in the Streamlit dashboard.

    The function prioritises **flooded cells** (depth > depth_threshold) and
    uniformly subsamples them to at most ``max_cells`` points.  A thin layer of
    dry background cells is appended so the map shows context beyond the flood
    envelope.  All Lambert 93 (EPSG:2154) coordinates are reprojected to
    WGS84 (EPSG:4326) using pyproj.

    Args:
        hdf5_path:       Path to ``CAPSTONE_JN_L752_PK.p02.hdf`` (or p01).
        timestep_idx:    0-based index into the output time series.
        max_cells:       Maximum flooded points to return (default 5 000 for
                         smooth browser rendering).
        depth_threshold: Minimum depth (m) to classify a cell as flooded
                         (default 0.02 m = 2 cm).
        dry_sample_rate: Keep 1-in-N dry cells for visual context around the
                         flood envelope (default 50).

    Returns:
        Dict with keys:
        - ``timestamp``  (str)  : HEC-RAS timestamp string for this step.
        - ``t_idx``      (int)  : Timestep index used.
        - ``n_flooded``  (int)  : Number of flooded cells before downsampling.
        - ``n_points``   (int)  : Number of points in the output.
        - ``points``     (list) : List of dicts, each with:
            - ``lat``    (float) : WGS84 latitude.
            - ``lon``    (float) : WGS84 longitude.
            - ``depth_m``(float) : Water depth in metres (0.0 for dry context cells).
            - ``wse_m``  (float) : Water Surface Elevation (metres NGF).
            - ``flooded``(bool)  : True if depth > threshold.

    Raises:
        FileNotFoundError: If the HDF5 file does not exist.
        ImportError:       If pyproj is not installed.
        RuntimeError:      If the timestep index is out of range.

    Example::

        from src.engine.hecras_hdf5_reader import extract_downsampled_flow_data

        data = extract_downsampled_flow_data(
            hdf5_path=\"data/hec-ras/CAPSTONE_JN_L752_PK.p02.hdf\",
            timestep_idx=60,
        )
        # data[\"timestamp\"] -> \"21SEP2025 17:00:00\"
        # data[\"n_flooded\"] -> 236267
        # data[\"n_points\"] -> 5068
        # data[\"points\"][0] -> {\"lat\": 44.63, \"lon\": 4.88, \"depth_m\": 0.53, ...}
    """
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise ImportError(
            "pyproj is required for coordinate reprojection. "
            "Install it with: pip install pyproj"
        ) from exc

    hdf5_path = Path(hdf5_path)
    if not hdf5_path.exists():
        raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    FA_NAME = None  # will be resolved from the file

    with h5py.File(str(hdf5_path), 'r') as f:

        # ── 1. Discover flow area name ──────────────────────────────────
        fa_attrs = f[f"{_GEOM_2D}/Attributes"][:]
        FA_NAME = fa_attrs[0]['Name'].decode().strip()
        logger.info(f"Flow area: {FA_NAME}")

        # ── 2. Read timestamps and validate index ───────────────────────
        ts_ds_path = f"{_UTS}/Time Date Stamp"
        if ts_ds_path in f:
            ts_raw = f[ts_ds_path][:]
            timestamps = [t.decode().strip() for t in ts_raw]
        else:
            # PostProcessing-format HDF5 (no UTS group): derive n_ts from WSE shape
            ws_probe = f.get(f"{_2D_FA}/{FA_NAME}/Water Surface")
            n_ts_probe = ws_probe.shape[0] if ws_probe is not None else 127
            import datetime as _dt
            _base = _dt.datetime(2025, 9, 21, 7, 0)
            timestamps = [
                (_base + _dt.timedelta(minutes=10 * i)).strftime("%d%b%Y %H:%M:%S").upper()
                for i in range(n_ts_probe)
            ]
        n_ts = len(timestamps)

        if not (-n_ts <= timestep_idx < n_ts):
            raise RuntimeError(
                f"timestep_idx={timestep_idx} is out of range "
                f"[0, {n_ts - 1}] for this plan."
            )
        if timestep_idx < 0:
            timestep_idx = n_ts + timestep_idx

        timestamp = timestamps[timestep_idx]
        logger.info(f"Extracting timestep {timestep_idx}: {timestamp}")

        # ── 3. Load spatial and result data ─────────────────────────────
        cc_path   = f"{_GEOM_2D}/{FA_NAME}/Cells Center Coordinate"
        ze_path   = f"{_GEOM_2D}/{FA_NAME}/Cells Minimum Elevation"
        ws_path   = f"{_2D_FA}/{FA_NAME}/Water Surface"

        cell_centers = f[cc_path][:]              # (N, 2) Lambert 93
        cell_min_elev = f[ze_path][:]             # (N,)
        wse_row   = f[ws_path][timestep_idx, :]   # (N,) — read only one row

        # Read Face Velocity and cell-face mapping indices if available
        face_vel_row = None
        cell_face_info = None
        cell_face_vals = None
        fv_path = f"{_2D_FA}/{FA_NAME}/Face Velocity"
        if fv_path in f:
            face_vel_row = f[fv_path][timestep_idx, :]
            cell_face_info = f[f"{_GEOM_2D}/{FA_NAME}/Cells Face and Orientation Info"][:]
            cell_face_vals = f[f"{_GEOM_2D}/{FA_NAME}/Cells Face and Orientation Values"][:]

    # ── 4. Compute water depth ──────────────────────────────────────────
    depth = wse_row - cell_min_elev
    # Clamp: negative or NaN → dry
    depth = np.where(np.isnan(depth) | (depth < 0), 0.0, depth)
    # Also zero out NaN WSE (inactive cells)
    depth = np.where(np.isnan(wse_row), 0.0, depth)

    # ── 5. Select points ────────────────────────────────────────────────
    flooded_mask = depth > depth_threshold
    flooded_idx  = np.where(flooded_mask)[0]
    dry_idx      = np.where(~flooded_mask)[0]
    n_flooded    = int(len(flooded_idx))

    # Downsample flooded cells to max_cells using uniform stride
    if len(flooded_idx) > max_cells:
        step = max(1, len(flooded_idx) // max_cells)
        flooded_sel = flooded_idx[::step]
    else:
        flooded_sel = flooded_idx

    # Thin dry background cells for context
    if len(dry_idx) > 0 and dry_sample_rate > 0:
        dry_sel = dry_idx[::dry_sample_rate]
    else:
        dry_sel = np.array([], dtype=np.int64)

    sel = np.concatenate([flooded_sel, dry_sel])
    logger.info(
        f"Selected {len(flooded_sel):,} flooded + {len(dry_sel):,} dry "
        f"= {len(sel):,} total points"
    )

    # ── 6. Reproject Lambert 93 → WGS84 ─────────────────────────────────
    transformer = Transformer.from_crs('EPSG:2154', 'EPSG:4326', always_xy=True)
    lons, lats = transformer.transform(
        cell_centers[sel, 0],
        cell_centers[sel, 1]
    )

    # ── 7. Build output list ─────────────────────────────────────────────
    flooded_set = set(flooded_sel.tolist())
    points = []
    for i, orig_idx in enumerate(sel):
        d = float(depth[orig_idx])
        
        # Compute mean velocity magnitude for this cell
        vel = 0.0
        if face_vel_row is not None and cell_face_info is not None and cell_face_vals is not None:
            start, count = cell_face_info[orig_idx]
            face_indices = cell_face_vals[start:start+count, 0]
            # Average of absolute values of surrounding face velocities
            vel = float(np.mean(np.abs(face_vel_row[face_indices])))

        points.append({
            "lat":          round(float(lats[i]), 6),
            "lon":          round(float(lons[i]), 6),
            "depth_m":      round(d, 3),
            "wse_m":        round(float(wse_row[orig_idx]), 3) if not np.isnan(wse_row[orig_idx]) else None,
            "velocity_ms":  round(vel, 3),
            "flooded":      bool(orig_idx in flooded_set),
        })

    return {
        "timestamp": timestamp,
        "t_idx":     timestep_idx,
        "n_flooded": n_flooded,
        "n_points":  len(points),
        "flow_area": FA_NAME,
        "points":    points,
    }

def rasterize_flow_to_bitmap(
    hdf5_path: Union[str, Path],
    timestep_idx: int,
    variable: str,
    grid_size: int = 512,
) -> Dict:
    """
    Rasterize HEC-RAS 2D flow area results into a base64-encoded PNG image
    to be displayed as a PyDeck BitmapLayer. This replicates HEC-RAS Mapper's
    smooth, continuous visual style.
    """
    try:
        from PIL import Image
        import io
        import base64
        from pyproj import Transformer
    except ImportError as exc:
        raise ImportError(
            "PIL and pyproj are required for rasterization. "
            "Install them with: pip install Pillow pyproj"
        ) from exc

    hdf5_path = Path(hdf5_path)
    if not hdf5_path.exists():
        raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    FA_NAME = None

    # Resolve geometry source: PostProcessing HDF5 files store results-only
    # and carry a Geometry group that was copied from the g01.hdf.  If that is
    # missing (older format), fall back to the sibling geometry file.
    geom_hdf = hdf5_path
    _g01_sibling = hdf5_path.parent.parent / "CAPSTONE_JN_L752_PK.g01.hdf"
    if _g01_sibling.exists():
        import h5py as _h5_probe
        with _h5_probe.File(str(hdf5_path), 'r') as _fp:
            if _GEOM_2D not in _fp:
                geom_hdf = _g01_sibling

    with h5py.File(str(geom_hdf), 'r') as fg:
        fa_attrs = fg[f"{_GEOM_2D}/Attributes"][:]
        FA_NAME = fa_attrs[0]['Name'].decode().strip()
        cc_path = f"{_GEOM_2D}/{FA_NAME}/Cells Center Coordinate"
        ze_path = f"{_GEOM_2D}/{FA_NAME}/Cells Minimum Elevation"
        cell_centers = fg[cc_path][:]
        cell_min_elev = fg[ze_path][:]

    with h5py.File(str(hdf5_path), 'r') as f:
        # Timestamps: fall back to synthetic 10-min series when missing
        ts_ds_path = f"{_UTS}/Time Date Stamp"
        if ts_ds_path in f:
            ts_raw = f[ts_ds_path][:]
            timestamps = [t.decode().strip() for t in ts_raw]
        else:
            ws_probe = f.get(f"{_2D_FA}/{FA_NAME}/Water Surface")
            n_ts_probe = ws_probe.shape[0] if ws_probe is not None else 127
            import datetime as _dt
            _base = _dt.datetime(2025, 9, 21, 7, 0)
            timestamps = [
                (_base + _dt.timedelta(minutes=10 * i)).strftime("%d%b%Y %H:%M:%S").upper()
                for i in range(n_ts_probe)
            ]

        n_ts = len(timestamps)
        if timestep_idx < 0:
            timestep_idx = n_ts + timestep_idx
        timestamp = timestamps[timestep_idx]

        ws_path = f"{_2D_FA}/{FA_NAME}/Water Surface"
        wse_row = f[ws_path][timestep_idx, :]

        # Load values based on variable
        if variable == "Water Depth":
            depth = wse_row - cell_min_elev
            depth = np.where(np.isnan(depth) | (depth < 0), 0.0, depth)
            values = depth
        elif variable == "Water Surface Elevation (WSE)":
            values = wse_row
        elif variable in ("Water Depth (Max)", "Channel Flooding (>0.5m)"):
            # Read stored Maximum Water Surface from Summary Output (matches RAS Mapper 'Depth Max')
            _summary_path = (
                f"Results/Unsteady/Output/Output Blocks/Base Output/"
                f"Summary Output/2D Flow Areas/{FA_NAME}/Maximum Water Surface"
            )
            max_wse_vals = f[_summary_path][0, :]  # Row 0 = WSE values, Row 1 = time-of-peak (days)
            max_depth = max_wse_vals - cell_min_elev
            max_depth = np.where(np.isnan(max_depth) | (max_depth < 0), 0.0, max_depth)
            values = max_depth
            depth = max_depth  # Use max depth for alpha masking
        else:  # Flow Velocity
            face_vel_row = None
            cell_face_info = None
            cell_face_vals = None
            fv_path = f"{_2D_FA}/{FA_NAME}/Face Velocity"
            if fv_path in f:
                face_vel_row = f[fv_path][timestep_idx, :]
                # Read geometry datasets from geom_hdf (may differ from results HDF)
                with h5py.File(str(geom_hdf), 'r') as _fg_vel:
                    fo_info_path = f"{_GEOM_2D}/{FA_NAME}/Cells Face and Orientation Info"
                    fo_vals_path = f"{_GEOM_2D}/{FA_NAME}/Cells Face and Orientation Values"
                    if fo_info_path in _fg_vel:
                        cell_face_info = _fg_vel[fo_info_path][:]
                        cell_face_vals = _fg_vel[fo_vals_path][:]

            # Compute cell centroid velocity using vectorized operations for speed
            velocity = np.zeros(len(cell_min_elev), dtype=np.float32)
            if face_vel_row is not None and cell_face_info is not None and cell_face_vals is not None:
                n_cells = len(cell_face_info)
                cell_indices = np.repeat(np.arange(n_cells), cell_face_info[:, 1])
                abs_face_vels = np.abs(face_vel_row[cell_face_vals[:, 0]])
                sum_vel = np.bincount(cell_indices, weights=abs_face_vels, minlength=n_cells)
                velocity = sum_vel / np.maximum(cell_face_info[:, 1], 1)
            values = velocity

        # Depth array for wet/dry masking (always required to hide dry lands)
        # For non-max variables: compute from timestep WSE
        if variable not in ("Water Depth (Max)", "Channel Flooding (>0.5m)"):
            depth = wse_row - cell_min_elev
            depth = np.where(np.isnan(depth) | (depth < 0), 0.0, depth)

    # Coordinates bounds in Lambert 93
    x_min, y_min = cell_centers[:, 0].min(), cell_centers[:, 1].min()
    x_max, y_max = cell_centers[:, 0].max(), cell_centers[:, 1].max()

    # Reproject bounds to WGS84 for PyDeck BitmapLayer bounds
    transformer = Transformer.from_crs('EPSG:2154', 'EPSG:4326', always_xy=True)
    lon_min, lat_min = transformer.transform(x_min, y_min)
    lon_max, lat_max = transformer.transform(x_max, y_max)

    # Bin cell coordinates to grid pixels
    cols = ((cell_centers[:, 0] - x_min) / (x_max - x_min) * (grid_size - 1)).astype(np.int32)
    rows = ((y_max - cell_centers[:, 1]) / (y_max - y_min) * (grid_size - 1)).astype(np.int32)

    # Initialize grid
    grid_val = np.zeros((grid_size, grid_size), dtype=np.float32)
    grid_depth = np.zeros((grid_size, grid_size), dtype=np.float32)
    
    # Fill grid values
    grid_val[rows, cols] = values
    grid_depth[rows, cols] = depth

    # Create RGBA Image
    rgba = np.zeros((grid_size, grid_size, 4), dtype=np.uint8)

    # Apply continuous color mapping
    if variable in ("Water Depth", "Water Depth (Max)", "Channel Flooding (>0.5m)"):
        depth_threshold_low = 0.50 if variable == "Channel Flooding (>0.5m)" else 0.20
        depth_threshold_high = 0.70 if variable == "Channel Flooding (>0.5m)" else 0.35
        # Normalize depth: 0 m = light cyan, 3 m+ = deep indigo
        norm = np.clip(grid_depth / 3.0, 0.0, 1.0)
        # Cyan [173,216,230] -> Royal Blue [65,105,225] -> Indigo [75,0,130]
        rgba[..., 0] = (173 * (1 - norm) + 75 * norm).astype(np.uint8)
        rgba[..., 1] = (216 * (1 - norm) + 0 * norm).astype(np.uint8)
        rgba[..., 2] = (230 * (1 - norm) + 130 * norm).astype(np.uint8)
        # Alpha ramp: fully transparent below low threshold, solid at high threshold
        rgba[..., 3] = np.clip(
            (grid_depth - depth_threshold_low) / (depth_threshold_high - depth_threshold_low) * 200,
            0, 200
        ).astype(np.uint8)
        
    elif variable == "Water Surface Elevation (WSE)":
        # Normalize WSE dynamically to local min/max
        valid_vals = grid_val[grid_depth > 0.20]
        vmin = valid_vals.min() if len(valid_vals) > 0 else 150.0
        vmax = valid_vals.max() if len(valid_vals) > 0 else 530.0
        norm = np.clip((grid_val - vmin) / max(vmax - vmin, 1e-3), 0.0, 1.0)
        
        # Color scale: green [0, 200, 100] -> yellow [255, 215, 0] -> orange [255, 140, 0] -> red [200, 0, 0]
        r = np.zeros_like(norm)
        g = np.zeros_like(norm)
        b = np.zeros_like(norm)
        
        mask1 = norm < 0.33
        f1 = norm[mask1] / 0.33
        r[mask1] = 0 * (1 - f1) + 255 * f1
        g[mask1] = 200 * (1 - f1) + 215 * f1
        b[mask1] = 100 * (1 - f1) + 0 * f1
        
        mask2 = (norm >= 0.33) & (norm < 0.66)
        f2 = (norm[mask2] - 0.33) / 0.33
        r[mask2] = 255 * (1 - f2) + 255 * f2
        g[mask2] = 215 * (1 - f2) + 140 * f2
        b[mask2] = 0 * (1 - f2) + 0 * f2
        
        mask3 = norm >= 0.66
        f3 = (norm[mask3] - 0.66) / 0.34
        r[mask3] = 255 * (1 - f3) + 200 * f3
        g[mask3] = 140 * (1 - f3) + 0 * f3
        b[mask3] = 0 * (1 - f3) + 0 * f3
        
        rgba[..., 0] = r.astype(np.uint8)
        rgba[..., 1] = g.astype(np.uint8)
        rgba[..., 2] = b.astype(np.uint8)
        rgba[..., 3] = np.clip((grid_depth - 0.20) / (0.35 - 0.20) * 180, 0, 180).astype(np.uint8)
        
    else:  # Flow Velocity
        # Color scale: lime green [50, 205, 50] -> orange [255, 165, 0] -> red [255, 69, 0] -> violet [148, 0, 211]
        norm = np.clip(grid_val / 2.0, 0.0, 1.0)
        
        r = np.zeros_like(norm)
        g = np.zeros_like(norm)
        b = np.zeros_like(norm)
        
        mask1 = norm < 0.25
        f1 = norm[mask1] / 0.25
        r[mask1] = 50 * (1 - f1) + 255 * f1
        g[mask1] = 205 * (1 - f1) + 165 * f1
        b[mask1] = 50 * (1 - f1) + 0 * f1
        
        mask2 = (norm >= 0.25) & (norm < 0.6)
        f2 = (norm[mask2] - 0.25) / 0.35
        r[mask2] = 255 * (1 - f2) + 255 * f2
        g[mask2] = 165 * (1 - f2) + 69 * f2
        b[mask2] = 0 * (1 - f2) + 0 * f2
        
        mask3 = norm >= 0.6
        f3 = (norm[mask3] - 0.6) / 0.4
        r[mask3] = 255 * (1 - f3) + 148 * f3
        g[mask3] = 69 * (1 - f3) + 0 * f3
        b[mask3] = 0 * (1 - f3) + 211 * f3
        
        rgba[..., 0] = r.astype(np.uint8)
        rgba[..., 1] = g.astype(np.uint8)
        rgba[..., 2] = b.astype(np.uint8)
        rgba[..., 3] = np.clip((grid_depth - 0.20) / (0.35 - 0.20) * 180, 0, 180).astype(np.uint8)

    # Save to buffer
    img = Image.fromarray(rgba)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "img_b64": img_b64,
        "bounds": [lon_min, lat_min, lon_max, lat_max],
        "timestamp": timestamp,
        "vmin": float(vmin) if 'vmin' in locals() else None,
        "vmax": float(vmax) if 'vmax' in locals() else None,
    }


# ======================================================================
# Standalone test / demo
# ======================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(message)s")

    from pathlib import Path
    hecras_dir = Path(r"c:\Users\ktstr\Documents\railway-flood-twin\data\hec-ras")

    # List available plans
    print("\n=== Available HEC-RAS Plans ===")
    plans = list_available_plans(hecras_dir)
    for p in plans:
        print(f"  {p['file']}: {p['n_timesteps']} timesteps, "
              f"{p['start']} to {p['end']} ({p['size_mb']} MB)")

    # Read Plan 1 (R100_1HR)
    print("\n=== Plan 1: R100_1HR ===")
    with HECRASPlanReader(hecras_dir / "CAPSTONE_JN_L752_PK.p01.hdf") as reader:
        print(f"Flow area: {reader.flow_area_name}")
        print(f"Cells: {reader.n_cells:,}")
        print(f"Timesteps: {reader.n_timesteps}")
        print(f"Timestamps: {reader.timestamps}")

        # Structures
        print(f"\nStructures ({len(reader.structures)}):")
        for s in reader.structures:
            print(f"  {s['connection']:30s}  type={s['type']}")

        # Flood summary
        print("\n--- Flood Summary ---")
        summary = reader.get_flood_summary()
        print(f"Peak timestep: {summary['peak_timestep']}")
        print(f"Peak max depth: {summary['peak_max_depth_m']:.3f} m")
        print(f"Peak flooded area: {summary['peak_flooded_area_m2']:,.0f} m2")
        print(f"\nPer-timestep:")
        for ts in summary['timesteps']:
            print(f"  {ts['timestamp']}  depth={ts['max_depth_m']:.3f}m  "
                  f"area={ts['flooded_area_m2']:,.0f}m2  cells={ts['flooded_cells']:,}")

    print("\nDone.")
