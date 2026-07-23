"""Calibração da placa: detecção ArUco, homografia e retificação métrica.

Geometria do contrato (SPEC.md):
- 4 marcadores ArUco DICT_4X4_50, ids 0..3 = TL, TR, BR, BL, lado 40 mm.
- Centros dos marcadores formam retângulo de 250 x 380 mm.
- Imagem retificada: escala 2.0 px/mm, margem de 30 mm em volta do retângulo
  dos centros. Ou seja: pixel = (coord_mm + 30) * 2.0, com origem mm no canto
  superior-esquerdo do retângulo dos centros e eixo y para baixo.
"""

import cv2
import numpy as np

ARUCO_DICT_ID = cv2.aruco.DICT_4X4_50
MARKER_IDS = (0, 1, 2, 3)

MARKER_SIZE_MM = 40.0
PLATE_WIDTH_MM = 250.0
PLATE_HEIGHT_MM = 380.0
SCALE_PX_PER_MM = 2.0
MARGIN_MM = 30.0

RECTIFIED_WIDTH_PX = int(round((PLATE_WIDTH_MM + 2 * MARGIN_MM) * SCALE_PX_PER_MM))
RECTIFIED_HEIGHT_PX = int(round((PLATE_HEIGHT_MM + 2 * MARGIN_MM) * SCALE_PX_PER_MM))

MARKER_CENTERS_MM = {
    0: (0.0, 0.0),
    1: (PLATE_WIDTH_MM, 0.0),
    2: (PLATE_WIDTH_MM, PLATE_HEIGHT_MM),
    3: (0.0, PLATE_HEIGHT_MM),
}

_CORNER_OFFSETS_MM = np.array(
    [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]], dtype=np.float64
) * MARKER_SIZE_MM

_detector = None


def mm_to_px(points_mm):
    """Converte coordenadas mm da placa para pixels da imagem retificada."""
    pts = np.asarray(points_mm, dtype=np.float64)
    return (pts + MARGIN_MM) * SCALE_PX_PER_MM


def px_to_mm(points_px):
    """Converte pixels da imagem retificada para coordenadas mm da placa."""
    pts = np.asarray(points_px, dtype=np.float64)
    return pts / SCALE_PX_PER_MM - MARGIN_MM


def get_detector() -> "cv2.aruco.ArucoDetector":
    global _detector
    if _detector is None:
        dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID)
        params = cv2.aruco.DetectorParameters()
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        _detector = cv2.aruco.ArucoDetector(dictionary, params)
    return _detector


def detect_markers(image) -> dict:
    """Detecta os marcadores da placa.

    Retorna {marker_id: np.ndarray (4, 2) float64} com os cantos de cada
    marcador (ordem canônica ArUco: TL, TR, BR, BL), apenas para ids 0..3.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    corners, ids, _rejected = get_detector().detectMarkers(gray)
    found: dict = {}
    if ids is not None:
        for marker_corners, marker_id in zip(corners, ids.ravel()):
            mid = int(marker_id)
            if mid in MARKER_CENTERS_MM and mid not in found:
                found[mid] = marker_corners.reshape(4, 2).astype(np.float64)
    return found


def compute_homography(markers: dict) -> np.ndarray:
    """Homografia imagem original -> imagem retificada, usando os 16 cantos."""
    src = []
    dst = []
    for mid in MARKER_IDS:
        corners = markers[mid]
        center = np.asarray(MARKER_CENTERS_MM[mid], dtype=np.float64)
        for offset, corner in zip(_CORNER_OFFSETS_MM, corners):
            src.append(corner)
            dst.append(mm_to_px(center + offset))
    homography, _mask = cv2.findHomography(
        np.asarray(src, dtype=np.float64), np.asarray(dst, dtype=np.float64), 0
    )
    return homography


def rectify(image_bgr: np.ndarray, markers: dict) -> np.ndarray:
    """Retifica a foto para o plano métrico da placa (620 x 880 px)."""
    homography = compute_homography(markers)
    return cv2.warpPerspective(
        image_bgr,
        homography,
        (RECTIFIED_WIDTH_PX, RECTIFIED_HEIGHT_PX),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def marker_regions_px(pad_mm: float = 8.0) -> list:
    """Regiões (x0, y0, x1, y1) dos marcadores na imagem retificada, com folga."""
    half = MARKER_SIZE_MM / 2.0 + pad_mm
    regions = []
    for cx, cy in MARKER_CENTERS_MM.values():
        x0, y0 = mm_to_px((cx - half, cy - half))
        x1, y1 = mm_to_px((cx + half, cy + half))
        regions.append(
            (
                int(max(0, np.floor(x0))),
                int(max(0, np.floor(y0))),
                int(min(RECTIFIED_WIDTH_PX, np.ceil(x1))),
                int(min(RECTIFIED_HEIGHT_PX, np.ceil(y1))),
            )
        )
    return regions
