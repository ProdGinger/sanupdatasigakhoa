from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="서울 구별 이마트 vs 하이마트 실적 비교", layout="wide")
st.title("서울 구별 이마트와 하이마트 평균 실적 비교")
st.caption("출처: 공시 기반 서울 자치구별 시뮬레이션 데이터(sales.csv) · 2025-1Q ~ 2026-3Q · 금액 단위: 억원")

# 1-3 데이터 경로
HERE = Path(__file__).parent
DATA_PATH = HERE / "sales.csv"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


if not DATA_PATH.exists():
    st.error("sales.csv 파일을 찾을 수 없습니다. app.py와 같은 폴더에 sales.csv가 있는지 확인해 주세요.")
    st.stop()

data = load_data(DATA_PATH)

# 2-2 위젯: 사이드바에 자치구, 기업, 분기 범위, 표시 지표
st.sidebar.header("조회 조건 설정")

districts = sorted(data["district"].unique().tolist())
selected_districts = st.sidebar.multiselect(
    "서울 자치구 선택",
    options=districts,
    default=["강남구", "송파구", "서초구", "영등포구", "마포구"],
)

companies = sorted(data["company"].unique().tolist())
selected_companies = st.sidebar.multiselect(
    "비교할 기업 선택",
    options=companies,
    default=companies,
)

periods = data["period"].unique().tolist()
start_period, end_period = st.sidebar.select_slider(
    "분기 범위 선택",
    options=periods,
    value=(periods[0], periods[-1]),
)

metric_map = {
    "점포당 평균 매출 (억원)": "avg_sales_per_store",
    "점포당 평균 영업이익 (억원)": "avg_profit_per_store",
    "구 전체 매출 (억원)": "sales",
    "구 전체 영업이익 (억원)": "profit",
}
selected_metric_label = st.sidebar.radio(
    "표시 지표 선택",
    options=list(metric_map.keys()),
    index=0,
)
metric = metric_map[selected_metric_label]

# 2-3 빈 선택 처리
start_idx = periods.index(start_period)
end_idx = periods.index(end_period)
selected_periods = periods[start_idx : end_idx + 1]

view = data[
    (data["district"].isin(selected_districts))
    & (data["company"].isin(selected_companies))
    & (data["period"].isin(selected_periods))
].copy()

if view.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다. 사이드바에서 자치구, 기업, 분기 범위를 다시 선택해 주세요.")
    st.stop()

# 3-1 지표 카드: 선택 조건 평균과 표시 관측 수(행 수)
col_kpi1, col_kpi2 = st.columns(2)
with col_kpi1:
    avg_val = view[metric].mean()
    st.metric(
        label=f"선택 조건 평균 · {selected_metric_label}",
        value=f"{avg_val:,.2f} 억원",
    )
with col_kpi2:
    st.metric(
        label="표시 관측 수 (행 수)",
        value=f"{len(view):,} 건",
    )

st.divider()

# 2-9 차트 세 개 (Streamlit 내장 차트 사용, plotly 불필요)
col1, col2, col3 = st.columns(3)

# 차트 1: 분기별 추이 (선 그래프)
with col1:
    st.subheader(f"분기별 {selected_metric_label} 추이")
    trend_pivot = view.pivot_table(
        index="period",
        columns="company",
        values=metric,
        aggfunc="mean",
    ).reindex(selected_periods)
    st.line_chart(trend_pivot)

# 차트 2: 자치구·기업별 평균 실적 (막대 그래프)
with col2:
    st.subheader(f"구별 {selected_metric_label} 평균")
    dist_pivot = view.pivot_table(
        index="district",
        columns="company",
        values=metric,
        aggfunc="mean",
    )
    st.bar_chart(dist_pivot)

# 차트 3: 기업별 기간 영업이익률 (막대 그래프: 영업이익 합계 ÷ 매출 합계 × 100)
with col3:
    st.subheader("기업별 선택 기간 영업이익률 (%)")
    margin_df = view.groupby("company", as_index=True)[["sales", "profit"]].sum()
    margin_df["영업이익률(%)"] = (margin_df["profit"] / margin_df["sales"] * 100).round(2)
    st.bar_chart(margin_df[["영업이익률(%)"]])

# 4-1 표와 CSV 저장
st.subheader("서울 구별 상세 실적 데이터")
display_df = view.rename(
    columns={
        "period": "분기",
        "district": "자치구",
        "company": "기업",
        "sales": "구 전체 매출(억원)",
        "profit": "구 전체 영업이익(억원)",
        "stores": "점포 수(개)",
        "avg_sales_per_store": "점포당 평균 매출(억원)",
        "avg_profit_per_store": "점포당 평균 영업이익(억원)",
    }
)
st.dataframe(display_df, use_container_width=True, hide_index=True)

csv_bytes = view.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="현재 조회 데이터 CSV 다운로드",
    data=csv_bytes,
    file_name="seoul_gu_emart_himart_sales.csv",
    mime="text/csv",
)
