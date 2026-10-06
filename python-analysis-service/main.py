from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
import io
import json
import math
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from report import build_pdf, build_csv

app = FastAPI(title="DataHub Advanced Analysis Service", version="2.0")


# ==================== HELPERS ====================

def sanitize(o):
    """Replace NaN/Inf with None so the JSON response is valid."""
    if isinstance(o, dict):
        return {k: sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def load_dataframe(filename: str, contents: bytes) -> pd.DataFrame:
    name = (filename or "").lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(contents))
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(io.BytesIO(contents))
        if name.endswith(".json"):
            return pd.read_json(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")
    raise HTTPException(status_code=400, detail="Unsupported file type.")


# ==================== DATA PREVIEW ====================

def preview_data(df: pd.DataFrame) -> dict:
    """First 10 rows + column info"""
    return {
        "preview_rows": df.head(10).to_dict(orient="records"),
        "columns": list(df.columns),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
        "shape": {"rows": len(df), "columns": len(df.columns)},
    }


# ==================== DATA QUALITY REPORT ====================

def quality_report(df: pd.DataFrame) -> dict:
    """Comprehensive data quality analysis"""
    numeric_cols = df.select_dtypes(include=np.number).columns
    total_rows = max(len(df), 1)
    total_cells = max(len(df) * len(df.columns), 1)

    missing = df.isnull().sum()
    missing_pct = (missing / total_rows * 100).round(2)

    duplicates = df.duplicated().sum()
    duplicates_pct = round(duplicates / total_rows * 100, 2)

    dtype_summary = df.dtypes.astype(str).value_counts().to_dict()

    outliers = {}
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outlier_count = ((df[col] < lower) | (df[col] > upper)).sum()
        outliers[col] = {
            "count": int(outlier_count),
            "percentage": round(outlier_count / total_rows * 100, 2),
        }

    column_stats = []
    for col in df.columns:
        stats_dict = {
            "column": col,
            "dtype": str(df[col].dtype),
            "missing": int(missing[col]),
            "missing_pct": float(missing_pct[col]),
            "unique": int(df[col].nunique()),
        }
        if col in numeric_cols:
            stats_dict.update({
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
            })
        column_stats.append(stats_dict)

    return {
        "summary": {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "missing_values": int(missing.sum()),
            "missing_pct": round(missing.sum() / total_cells * 100, 2),
            "duplicate_rows": int(duplicates),
            "duplicate_pct": float(duplicates_pct),
        },
        "dtype_summary": dtype_summary,
        "column_stats": column_stats,
        "outliers": outliers,
    }


# ==================== ADVANCED STATS ====================

def compute_stats(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include="number")
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "numeric_summary": json.loads(numeric_df.describe().to_json()) if not numeric_df.empty else {},
    }


# ==================== CHART DATA ====================

def build_chart_data(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include="number").columns
    charts = {}

    if len(numeric_cols) > 0:
        col = numeric_cols[0]
        series = df[col].dropna()
        if len(series) > 0:
            counts, bins = np.histogram(series, bins=min(10, series.nunique() or 1))
            charts["histogram"] = {
                "column": col,
                "labels": [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(len(bins) - 1)],
                "values": counts.tolist(),
            }

    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr().round(3)
        charts["heatmap"] = {
            "columns": list(corr_matrix.columns),
            "data": corr_matrix.values.tolist(),
        }

    box_plots = {}
    for col in list(numeric_cols)[:4]:
        series = df[col].dropna()
        if len(series) > 0:
            box_plots[col] = {
                "min": float(series.min()),
                "q1": float(series.quantile(0.25)),
                "median": float(series.median()),
                "q3": float(series.quantile(0.75)),
                "max": float(series.max()),
            }
    if box_plots:
        charts["boxplots"] = box_plots

    if len(numeric_cols) >= 2:
        col1, col2 = numeric_cols[0], numeric_cols[1]
        scatter_data = df[[col1, col2]].dropna()
        if len(scatter_data) > 0:
            charts["scatter"] = {
                "x_column": col1,
                "y_column": col2,
                "points": scatter_data.values.tolist()[:100],
            }

    return charts


# ==================== MACHINE LEARNING ====================

def compute_ml(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include="number").dropna()

    if numeric_df.shape[1] < 2 or numeric_df.shape[0] < 3:
        return {"message": "Not enough numeric data"}

    scaler = StandardScaler()
    scaled = scaler.fit_transform(numeric_df)

    k = min(3, len(numeric_df))
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = kmeans.fit_predict(scaled)

    correlation = numeric_df.corr().round(3).to_dict()

    return {
        "cluster_count": k,
        "clusters": labels.tolist(),
        "correlation_matrix": correlation,
    }


# ==================== ENDPOINTS ====================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/preview")
async def preview(file: UploadFile = File(...)):
    """Get first 10 rows + column info"""
    contents = await file.read()
    df = load_dataframe(file.filename, contents)
    return sanitize(preview_data(df))


@app.post("/quality-report")
async def quality(file: UploadFile = File(...)):
    """Get comprehensive data quality report"""
    contents = await file.read()
    df = load_dataframe(file.filename, contents)
    return sanitize(quality_report(df))


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), analysis_type: str = Form(...)):
    """Full analysis: stats + ML + charts"""
    contents = await file.read()
    df = load_dataframe(file.filename, contents)

    analysis_type = analysis_type.upper()
    result = {
        "file_name": file.filename,
        "timestamp": datetime.now().isoformat(),
    }

    if analysis_type in ("STATS", "BOTH"):
        result["stats"] = compute_stats(df)
        result["quality"] = quality_report(df)

    if analysis_type in ("ML", "BOTH"):
        result["ml"] = compute_ml(df)

    result["chart_data"] = build_chart_data(df)

    return sanitize(result)


# ==================== EXPORTS (from the saved analysis result) ====================

class ExportRequest(BaseModel):
    result: Dict[str, Any]                      # the analysis JSON already produced by /analyze
    title: Optional[str] = "Data Analysis Report"
    file_name: Optional[str] = None
    export_type: Optional[str] = "stats"        # stats | quality | outliers | clusters


@app.post("/export-pdf")
async def export_pdf(req: ExportRequest):
    """PDF report (stats, quality, ML, charts) built from an existing analysis result."""
    try:
        pdf = build_pdf(req.result, req.title or "Data Analysis Report", req.file_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
    filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/export-csv")
async def export_csv(req: ExportRequest):
    """CSV export built from an existing analysis result."""
    try:
        csv_bytes = build_csv(req.result, req.export_type or "stats")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    filename = f"export_{req.export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )