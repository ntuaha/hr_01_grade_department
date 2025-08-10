#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pandas import ExcelFile, DataFrame


DATA_FILES = [
    "2023.H2.xlsx",
    "2024.H1.xlsx",
    "2024.H2.xlsx",
    "2025.H1.xlsx",
]

# 部門名稱：以 2025.H1 的唯一值中對應到「技術中心」為準
TARGET_DEPARTMENT = "智能技術中心"

OUTPUT_DIR = "2025H1_技術中心"

# 13 指標（以規範化後的欄名為準）
CATEGORY_KEYS = [
    "1.分析與邏輯思考能力",
    "2.專業知識",
    "3.溝通",
    "4.口頭溝通",
    "5.團隊合作",
    "6.合作意願",
    "7.持續、努力不懈",
    "8.個人紀律",
    "9.主動、積極進取",
    "10.成熟度",
    "11.領導能力、潛力",
    "12.說到做到",
    "13.綜合表現",
]


def normalize_col(col: str) -> str:
    # 去除所有空白（含全形/半形）與控制字元
    if col is None:
        return ""
    s = str(col)
    s = re.sub(r"\s+", "", s)
    # 統一一些常見符號的全半形差異
    s = s.replace("．", ".").replace("，", ",")
    return s


def build_column_mapping(df: DataFrame) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    normalized = {normalize_col(c): c for c in df.columns}
    # 必要欄位對應
    for canonical in ["受評者", "部", "平均"] + CATEGORY_KEYS:
        key = normalize_col(canonical)
        # 有些資料會在 13. 綜合表現 中出現空白，normalize 後即可匹配
        if key in normalized:
            mapping[canonical] = normalized[key]
        else:
            # 某些檔案可能把 13. 前面加空白或不同寫法，嘗試鬆綁匹配
            # 例如：13. 綜合表現 / 13.綜合表現 / 13. 綜 合 表 現
            found = None
            for nkey, orig in normalized.items():
                if key.replace(".", "") == nkey.replace(".", ""):
                    found = orig
                    break
            if found is not None:
                mapping[canonical] = found
            else:
                # 允許缺少個別指標（先不 raise）
                mapping[canonical] = None
    return mapping


def load_total_scores(xlsx_path: str) -> DataFrame:
    xf = ExcelFile(xlsx_path)
    # 優先找「總評分」工作表
    sheet = None
    for name in xf.sheet_names:
        if "總評分" in str(name):
            sheet = name
            break
    if sheet is None:
        raise RuntimeError(f"檔案 {xlsx_path} 找不到『總評分』工作表")
    df = xf.parse(sheet)
    return df


def filter_department(df: DataFrame, dept_name: str) -> DataFrame:
    col_map = build_column_mapping(df)
    dept_col = col_map.get("部")
    if dept_col is None:
        raise RuntimeError("找不到『部』欄位，無法篩選部門")
    fdf = df[df[dept_col] == dept_name].copy()
    return fdf


def get_people_2025h1(df_2025: DataFrame) -> List[str]:
    col_map = build_column_mapping(df_2025)
    person_col = col_map.get("受評者")
    if person_col is None:
        raise RuntimeError("找不到『受評者』欄位")
    names = (
        df_2025[person_col].dropna().astype(str).str.strip().unique().tolist()
    )
    return names


def compute_rank_table(df_all: DataFrame, person_col: str, score_col: str) -> DataFrame:
    # 回傳包含『受評者』『__rank』『__scoreHigherBetter』『__n』『__percentile』欄位的表
    tmp = df_all[[person_col, score_col]].copy()
    tmp = tmp.dropna(subset=[score_col])
    tmp["__rank"] = tmp[score_col].rank(ascending=False, method="min").astype(int)
    tmp["__n"] = len(tmp)
    # 讓數值越高越好（名次分數）
    tmp["__scoreHigherBetter"] = tmp["__n"] - tmp["__rank"] + 1
    tmp["__percentile"] = (1.0 - (tmp["__rank"] - 1) / tmp["__n"]) * 100.0
    return tmp[[person_col, "__rank", "__scoreHigherBetter", "__n", "__percentile"]]


def extract_person_row(df_all: DataFrame, col_map: Dict[str, str], person: str) -> Optional[pd.Series]:
    person_col = col_map.get("受評者")
    if person_col is None:
        return None
    rows = df_all[df_all[person_col] == person]
    if rows.empty:
        return None
    return rows.iloc[0]


def row_to_categories(row: pd.Series, col_map: Dict[str, str]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for key in CATEGORY_KEYS:
        col = col_map.get(key)
        out[key] = float(row[col]) if col and pd.notna(row[col]) else None
    return out


def safe_float(v: Optional[float]) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def gather_dept_category_averages_2025h1() -> Dict[str, Dict[str, Optional[float]]]:
    # 計算 2025.H1 各部門與全體的各項指標與平均的平均值
    df = load_total_scores("2025.H1.xlsx")
    col_map = build_column_mapping(df)
    dept_col = col_map.get("部")
    person_col = col_map.get("受評者")
    avg_col = col_map.get("平均")
    if dept_col is None or person_col is None:
        return {}
    categories = CATEGORY_KEYS + (["平均"] if avg_col else [])

    out: Dict[str, Dict[str, Optional[float]]] = {}
    # 全體
    out["ALL"] = {}
    for c in categories:
        col = avg_col if c == "平均" else col_map.get(c)
        out["ALL"][c] = float(df[col].mean()) if col and col in df.columns else None

    # 各部門
    for dept_name, gdf in df.groupby(dept_col):
        out.setdefault(str(dept_name), {})
        for c in categories:
            col = avg_col if c == "平均" else col_map.get(c)
            out[str(dept_name)][c] = float(gdf[col].mean()) if col and col in gdf.columns else None

    return out


def gather_dept_category_averages_for_df(df: DataFrame) -> Dict[str, Dict[str, Optional[float]]]:
    col_map = build_column_mapping(df)
    dept_col = col_map.get("部")
    avg_col = col_map.get("平均")
    if dept_col is None:
        return {}
    categories = CATEGORY_KEYS + (["平均"] if avg_col else [])

    out: Dict[str, Dict[str, Optional[float]]] = {}
    # 全體
    out["ALL"] = {}
    for c in categories:
        col = avg_col if c == "平均" else col_map.get(c)
        out["ALL"][c] = float(df[col].mean()) if col and col in df.columns else None

    # 各部門
    for dept_name, gdf in df.groupby(dept_col):
        out.setdefault(str(dept_name), {})
        for c in categories:
            col = avg_col if c == "平均" else col_map.get(c)
            out[str(dept_name)][c] = float(gdf[col].mean()) if col and col in gdf.columns else None

    return out


def get_response_counts_2025(df_2025: DataFrame, person: str) -> Dict[str, Optional[int]]:
    # 從 2025.H1 的總評分表找出該人的問卷回收份數（必填/邀請/主動/總份數）
    cols = {normalize_col(c): c for c in df_2025.columns}
    name_cols = [c for c in df_2025.columns if normalize_col(c) == normalize_col("受評者")]
    if not name_cols:
        return {"必填份數": None, "邀請份數": None, "主動份數": None, "總份數": None}
    name_col = name_cols[0]
    row = df_2025[df_2025[name_col] == person]
    if row.empty:
        return {"必填份數": None, "邀請份數": None, "主動份數": None, "總份數": None}
    row = row.iloc[0]
    def read_int(label: str) -> Optional[int]:
        c = cols.get(normalize_col(label))
        if not c:
            return None
        v = row.get(c)
        try:
            return int(v) if pd.notna(v) else None
        except Exception:
            try:
                return int(float(v)) if pd.notna(v) else None
            except Exception:
                return None

    return {
        "必填份數": read_int("必填份數"),
        "邀請份數": read_int("邀請份數"),
        "主動份數": read_int("主動份數"),
        "總份數": read_int("總份數"),
    }


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 讀 2025.H1 作為名單來源
    df_2025 = load_total_scores("2025.H1.xlsx")
    df_2025_dept = filter_department(df_2025, TARGET_DEPARTMENT)
    people = get_people_2025h1(df_2025_dept)

    # 預先把所有年份的 df 與欄位對應抓好
    year_to_df_all: Dict[str, DataFrame] = {}
    year_to_colmap: Dict[str, Dict[str, str]] = {}
    year_to_dept_means: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    for fname in DATA_FILES:
        if not os.path.exists(fname):
            continue
        df = load_total_scores(fname)
        year = os.path.splitext(os.path.basename(fname))[0]
        year_to_df_all[year] = df
        year_to_colmap[year] = build_column_mapping(df)
        year_to_dept_means[year] = gather_dept_category_averages_for_df(df)

    # 為各年份、各欄位計算排名資料表（全體，不限部門）
    year_to_rankings: Dict[str, Dict[str, DataFrame]] = {}
    for year, df_all in year_to_df_all.items():
        col_map = year_to_colmap[year]
        person_col = col_map.get("受評者")
        avg_col = col_map.get("平均")
        if not person_col:
            continue
        rankers: Dict[str, DataFrame] = {}
        if avg_col:
            rankers["平均"] = compute_rank_table(df_all, person_col, avg_col)
        for cat in CATEGORY_KEYS:
            ccol = col_map.get(cat)
            if ccol:
                rankers[cat] = compute_rank_table(df_all, person_col, ccol)
        year_to_rankings[year] = rankers

    # 逐人輸出 CSV 與 HTML
    dept_avgs_2025 = gather_dept_category_averages_2025h1()

    index_entries: List[Dict[str, object]] = []

    for person in people:
        rows: List[Dict[str, object]] = []
        radar_series: List[Dict[str, object]] = []
        headcounts_per_year: Dict[str, Dict[str, Optional[int]]] = {}

        for year in sorted(year_to_df_all.keys()):
            df_all = year_to_df_all[year]
            col_map = year_to_colmap[year]

            person_row = extract_person_row(df_all, col_map, person)
            avg_col = col_map.get("平均")
            person_col = col_map.get("受評者")
            dept_col = col_map.get("部")

            avg_val: Optional[float] = None
            rank_val: Optional[int] = None  # 名次（1 為最佳）
            rank_score: Optional[int] = None  # 排名分數（數值越高越好）
            pct_val: Optional[float] = None  # 百分比（數值越高越好）
            categories: Dict[str, Optional[float]] = {k: None for k in CATEGORY_KEYS}
            cat_rank: Dict[str, Optional[int]] = {k: None for k in CATEGORY_KEYS}
            cat_rank_score: Dict[str, Optional[int]] = {k: None for k in CATEGORY_KEYS}
            cat_pct: Dict[str, Optional[float]] = {k: None for k in CATEGORY_KEYS}
            group_rank: Dict[str, Optional[int]] = {k: None for k in ["平均"] + CATEGORY_KEYS}
            n_all: Optional[int] = None
            n_group: Optional[int] = None

            if person_row is not None:
                if avg_col:
                    avg_val = safe_float(person_row.get(avg_col))
                categories = row_to_categories(person_row, col_map)

                # 從各欄位的排名表取對應紀錄（全體）
                rankers = year_to_rankings.get(year, {})
                if avg_col and "平均" in rankers and person_col in rankers["平均"].columns:
                    r = rankers["平均"][rankers["平均"][person_col] == person]
                    if not r.empty:
                        rv = r.iloc[0]
                        rank_val = int(rv["__rank"]) if pd.notna(rv["__rank"]) else None
                        rank_score = int(rv["__scoreHigherBetter"]) if pd.notna(rv["__scoreHigherBetter"]) else None
                        pct_val = float(rv["__percentile"]) if pd.notna(rv["__percentile"]) else None
                        # 全體人數（同一表中的 __n 相同）
                        try:
                            n_all = int(rankers["平均"]["__n"].iloc[0])
                        except Exception:
                            n_all = None

                for cat in CATEGORY_KEYS:
                    tbl = rankers.get(cat)
                    if tbl is None or person_col not in tbl.columns:
                        continue
                    rr = tbl[tbl[person_col] == person]
                    if rr.empty:
                        continue
                    r0 = rr.iloc[0]
                    cat_rank[cat] = int(r0["__rank"]) if pd.notna(r0["__rank"]) else None
                    cat_rank_score[cat] = (
                        int(r0["__scoreHigherBetter"]) if pd.notna(r0["__scoreHigherBetter"]) else None
                    )
                    cat_pct[cat] = (
                        float(r0["__percentile"]) if pd.notna(r0["__percentile"]) else None
                    )

                # 組內排名（依該年該人部門）
                if dept_col and person_col:
                    dept_val = person_row.get(dept_col)
                    if pd.notna(dept_val):
                        dept_df = df_all[df_all[dept_col] == dept_val]
                        # 平均
                        if avg_col:
                            gr = compute_rank_table(dept_df, person_col, avg_col)
                            rr = gr[gr[person_col] == person]
                            if not rr.empty and pd.notna(rr.iloc[0]["__rank"]):
                                group_rank["平均"] = int(rr.iloc[0]["__rank"])  # 名次
                            try:
                                n_group = int(gr["__n"].iloc[0])
                            except Exception:
                                n_group = None
                        # 各指標
                        for cat in CATEGORY_KEYS:
                            ccol = col_map.get(cat)
                            if ccol:
                                grc = compute_rank_table(dept_df, person_col, ccol)
                                rr2 = grc[grc[person_col] == person]
                                if not rr2.empty and pd.notna(rr2.iloc[0]["__rank"]):
                                    group_rank[cat] = int(rr2.iloc[0]["__rank"])  # 名次

            row = {
                "年度": year,
                "受評者": person,
                "平均": avg_val,
                "平均_名次": rank_val,
                "平均_排名分數": rank_score,
                "平均_排名百分比": pct_val,
                "全體人數": n_all,
                "組內人數": n_group,
            }
            for k in CATEGORY_KEYS:
                row[k] = categories.get(k)
                row[f"{k}_名次"] = cat_rank.get(k)
                row[f"{k}_排名分數"] = cat_rank_score.get(k)
                row[f"{k}_排名百分比"] = cat_pct.get(k)
            # 組內排名
            row["平均_組內名次"] = group_rank.get("平均")
            for k in CATEGORY_KEYS:
                row[f"{k}_組內名次"] = group_rank.get(k)
            rows.append(row)

            # 累計 headcount
            headcounts_per_year[year] = {"all": n_all, "group": n_group}

            # 提供給雷達圖使用
            radar_series.append(
                {
                    "year": year,
                    "categories": {k: categories.get(k) for k in CATEGORY_KEYS},
                }
            )

        # 排序 rows 依年度
        rows_sorted = sorted(rows, key=lambda x: x["年度"])  # type: ignore
        csv_path = os.path.join(OUTPUT_DIR, f"{person}.csv")
        pd.DataFrame(rows_sorted).to_csv(csv_path, index=False)

        # 2025.H1 個人各項分數
        person_scores_2025: Dict[str, Optional[float]] = {}
        row2025 = next((r for r in rows_sorted if r["年度"] == "2025.H1"), None)
        if row2025 is not None:
            person_scores_2025["平均"] = row2025.get("平均")  # type: ignore
            for k in CATEGORY_KEYS:
                person_scores_2025[k] = row2025.get(k)  # type: ignore

        # 2025.H1 問卷回收份數
        resp_counts = get_response_counts_2025(df_2025, person)

        # 產出 HTML
        html_path = os.path.join(OUTPUT_DIR, f"{person}.html")
        page_data = {
            "person": person,
            "department": TARGET_DEPARTMENT,
            "series": radar_series,
            "tableRows": rows_sorted,
            "categories": CATEGORY_KEYS,
            "deptCategoryAverages2025H1": dept_avgs_2025,
            "personScores2025H1": person_scores_2025,
            "yearDeptMeans": year_to_dept_means,
            "headcounts": headcounts_per_year,
            "responses2025": resp_counts,
        }
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("person_report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(tmpl.render(**page_data))

        # 準備首頁摘要
        latest = next((r for r in rows_sorted if r["年度"] == "2025.H1"), None)
        prev_candidates = [r for r in rows_sorted if r["年度"] != "2025.H1" and r.get("平均") is not None]
        prev = prev_candidates[-1] if prev_candidates else None
        avg_2025 = latest.get("平均") if latest else None
        avg_prev = prev.get("平均") if prev else None
        trend = (avg_2025 - avg_prev) if (avg_2025 is not None and avg_prev is not None) else None

        all_mean_2025 = dept_avgs_2025.get("ALL", {}).get("平均")
        dept_mean_2025 = dept_avgs_2025.get(TARGET_DEPARTMENT, {}).get("平均")
        diff_all = (avg_2025 - all_mean_2025) if (avg_2025 is not None and all_mean_2025 is not None) else None
        diff_dept = (avg_2025 - dept_mean_2025) if (avg_2025 is not None and dept_mean_2025 is not None) else None

        # 優勢/留意項目（以相對 ALL 與部門平均的平均差作為排序）
        strengths: List[Tuple[str, float]] = []
        weaknesses: List[Tuple[str, float]] = []
        for cat in CATEGORY_KEYS:
            v = person_scores_2025.get(cat)
            a = dept_avgs_2025.get("ALL", {}).get(cat)
            d = dept_avgs_2025.get(TARGET_DEPARTMENT, {}).get(cat)
            if v is None or (a is None and d is None):
                continue
            diffs: List[float] = []
            if a is not None:
                diffs.append(v - a)
            if d is not None:
                diffs.append(v - d)
            if not diffs:
                continue
            score = sum(diffs) / len(diffs)
            if score >= 0:
                strengths.append((cat, score))
            else:
                weaknesses.append((cat, score))
        strengths.sort(key=lambda x: x[1], reverse=True)
        weaknesses.sort(key=lambda x: x[1])

        index_entries.append(
            {
                "name": person,
                "avg_2025": avg_2025,
                "trend_from_prev": trend,
                "diff_vs_all": diff_all,
                "diff_vs_dept": diff_dept,
                "strengths": strengths[:3],
                "weaknesses": weaknesses[:3],
            }
        )

    print(f"完成，輸出於 {OUTPUT_DIR}/ 下的 CSV 與 HTML 檔案。")

    # 產出首頁 index.html
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=select_autoescape(["html"]),
        )
        tmpl = env.get_template("index.html")
        with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(
                tmpl.render(
                    department=TARGET_DEPARTMENT,
                    entries=index_entries,
                    categories=CATEGORY_KEYS,
                )
            )
    except Exception:
        pass


if __name__ == "__main__":
    main()


