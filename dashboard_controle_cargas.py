from __future__ import annotations
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Dashboard Controle de Cargas",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #F5F7FB; }
    
    .hero {
        background: linear-gradient(135deg, #003B71 0%, #005DAA 70%, #FF8A00 140%);
        color: white;
        padding: 28px 32px;
        border-radius: 15px;
        margin-bottom: 24px;
        box-shadow: 0 6px 18px rgba(0, 59, 113, 0.15);
    }
    
    .hero h1 { 
        margin: 0; 
        font-size: 30px; 
        font-weight: 900;
    }
    
    .hero p { 
        margin: 10px 0 0 0; 
        font-size: 14px;
        opacity: 0.95;
        font-weight: 500;
    }
    
    .gds-badge {
        background: rgba(255, 138, 0, 0.2);
        color: #FFD580;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        float: right;
        margin-top: -8px;
    }
    
    .section-title {
        color: #003B71;
        font-size: 21px;
        font-weight: 800;
        margin-top: 26px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CABEÇALHO
# ============================================================
st.markdown("""
<div class="hero">
    <div class="gds-badge">🚚 GDS LOGÍSTICA</div>
    <h1>📦 Dashboard de Controle de Cargas</h1>
    <p>Análise com destaque em DIAS EM ATRASO e REENTREGA PENDENTE</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÕES
# ============================================================
def normalizar_awb(valor: object) -> str:
    if pd.isna(valor):
        return ""

    txt = str(valor).strip().replace(".0", "")
    apenas = "".join(ch for ch in txt if ch.isdigit())

    if len(apenas) == 15 and apenas.startswith("577"):
        apenas = apenas[3:11]
    elif apenas.startswith("577") and len(apenas) > 8:
        apenas = apenas[3:]

    return apenas.lstrip("0") or apenas


def encontrar_coluna(df: pd.DataFrame, opcoes: list[str]) -> str | None:
    colunas_lower = {col.lower().strip(): col for col in df.columns}

    for opcao in opcoes:
        opcao_lower = opcao.lower().strip()

        if opcao_lower in colunas_lower:
            return colunas_lower[opcao_lower]

        for col_lower, col_original in colunas_lower.items():
            if opcao_lower in col_lower or col_lower in opcao_lower:
                return col_original

    return None

# ============================================================
# UPLOAD
# ============================================================
st.markdown('<div class="section-title">📁 Carregar Dados</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.info("**1️⃣ Relatório do Sistema** (CSV ou Excel)")
    arquivo_sistema = st.file_uploader(
        "Selecione o arquivo",
        type=["xlsx", "xls", "csv"],
        key="sistema"
    )

with col2:
    st.info("**2️⃣ Planilha Consolidada** (Excel com 4 abas)")
    arquivo_consolidado = st.file_uploader(
        "Selecione o arquivo",
        type=["xlsx", "xls"],
        key="consolidado"
    )

# ============================================================
# PROCESSAMENTO
# ============================================================
if arquivo_sistema and arquivo_consolidado:

    with st.spinner("⏳ Carregando Relatório do Sistema..."):
        if "xlsx" in arquivo_sistema.name or "xls" in arquivo_sistema.name:
            df_sistema = pd.read_excel(arquivo_sistema, sheet_name="Report")
        else:
            df_sistema = pd.read_csv(arquivo_sistema)

        st.success(f"✅ {len(df_sistema)} linhas carregadas")

    with st.spinner("⏳ Carregando Planilha Consolidada..."):
        df_pendencias = pd.read_excel(arquivo_consolidado, sheet_name="PENDENCIAS")
        df_pendencias.columns = df_pendencias.columns.str.strip()

        df_pendencia_corp = pd.read_excel(arquivo_consolidado, sheet_name="PENDENCIA CORP")
        df_pendencia_corp.columns = df_pendencia_corp.columns.str.strip()

        df_avarias = pd.read_excel(arquivo_consolidado, sheet_name="AVARIAS", skiprows=1)
        df_avarias.columns = df_avarias.columns.str.strip()

        df_finalizadas = pd.read_excel(arquivo_consolidado, sheet_name="FINALIZADAS")
        df_finalizadas.columns = df_finalizadas.columns.str.strip()

        st.success(
            f"✅ PENDENCIAS: {len(df_pendencias)} | "
            f"CORP: {len(df_pendencia_corp)} | "
            f"AVARIAS: {len(df_avarias)} | "
            f"FINALIZADAS: {len(df_finalizadas)}"
        )

    # ============================================================
    # ENCONTRAR COLUNAS
    # ============================================================
    col_awb_sistema = encontrar_coluna(df_sistema, ["AWB", "awb", "N. Rastreamento", "rastreamento", "numero"])
    col_sla_sistema = encontrar_coluna(df_sistema, ["SLA", "sla", "data", "vencimento", "prazo"])
    col_status_sistema = encontrar_coluna(df_sistema, ["StatusDescription", "status", "situacao", "status description"])

    if not col_awb_sistema or not col_sla_sistema or not col_status_sistema:
        st.error("❌ Colunas obrigatórias não encontradas no relatório do sistema.")
        st.write("**Colunas do Sistema:**", list(df_sistema.columns))
        st.stop()

    df_sistema = df_sistema.rename(columns={
        col_awb_sistema: "AWB",
        col_sla_sistema: "SLA",
        col_status_sistema: "StatusDescription"
    })

    col_awb_pend = encontrar_coluna(df_pendencias, ["AWB", "awb", "N. Rastreamento"])
    col_awb_corp = encontrar_coluna(df_pendencia_corp, ["AWB", "awb", "N. Rastreamento"])
    col_awb_avar = encontrar_coluna(df_avarias, ["AWB", "awb", "N. Rastreamento"])
    col_awb_final = encontrar_coluna(df_finalizadas, ["AWB", "awb", "N. Rastreamento"])

    if not col_awb_final:
        st.error("❌ Coluna AWB não encontrada na aba FINALIZADAS.")
        st.write("**Colunas da aba FINALIZADAS:**", list(df_finalizadas.columns))
        st.stop()

    # ============================================================
    # NORMALIZAR AWB
    # ============================================================
    df_sistema["awb_norm"] = df_sistema["AWB"].apply(normalizar_awb)

    if col_awb_pend:
        df_pendencias["awb_norm"] = df_pendencias[col_awb_pend].apply(normalizar_awb)
    else:
        df_pendencias["awb_norm"] = ""

    if col_awb_corp:
        df_pendencia_corp["awb_norm"] = df_pendencia_corp[col_awb_corp].apply(normalizar_awb)
    else:
        df_pendencia_corp["awb_norm"] = ""

    if col_awb_avar:
        df_avarias["awb_norm"] = df_avarias[col_awb_avar].apply(normalizar_awb)
    else:
        df_avarias["awb_norm"] = ""

    df_finalizadas["awb_norm"] = df_finalizadas[col_awb_final].apply(normalizar_awb)

    # ============================================================
    # FINALIZADAS → TRATADAS PELA TORRE
    # ============================================================
    hoje = datetime.now().date()

    col_data_final = encontrar_coluna(df_finalizadas, [
        "DATA MOV. FINALIZAÇÃO",
        "DATA MOV FINALIZAÇÃO",
        "DATA MOV. FINALIZACAO",
        "DATA MOV FINALIZACAO",
        "DATA FINALIZAÇÃO",
        "DATA FINALIZACAO",
        "DATA"
    ])

    # Todas as AWBs da aba FINALIZADAS entram como tratadas pela Torre
    finalizadas_torre = set(df_finalizadas["awb_norm"])

    # ============================================================
    # FINALIZADAS NO MÊS
    # ============================================================
    if col_data_final:

        df_finalizadas["_data_fin"] = pd.to_datetime(
            df_finalizadas[col_data_final],
            errors="coerce",
            dayfirst=True
        )

        finalizadas_mes = len(
            df_finalizadas[
                (df_finalizadas["_data_fin"].dt.month == hoje.month) &
                (df_finalizadas["_data_fin"].dt.year == hoje.year)
            ]
        )

    else:
        finalizadas_mes = 0

    # ============================================================
    # CLASSIFICAÇÃO
    # ============================================================
    pendencias_set = set(df_pendencias["awb_norm"]) | set(df_pendencia_corp["awb_norm"])
    avarias_set = set(df_avarias["awb_norm"])

    def classificar(row):
        awb = row["awb_norm"]
        sla_str = row.get("SLA")

        if pd.isna(sla_str):
            return "❓ SEM SLA"

        try:
            sla = pd.to_datetime(sla_str).date()
        except:
            return "❓ SEM SLA"

        if awb in finalizadas_torre:
            return "✅ FINALIZADO"

        if awb in pendencias_set:
            return "⏳ PENDÊNCIA"

        if awb in avarias_set:
            return "⚠️ AVARIA"

        if sla == hoje:
            return "🟠 NO PISO"

        if sla < hoje:
            return "🔴 ATRASADA"

        return "🟢 MONITORAR"

    df_sistema["CLASSIFICACAO"] = df_sistema.apply(classificar, axis=1)

    # ============================================================
    # RESUMO EXECUTIVO
    # ============================================================
    st.markdown('<div class="section-title">📊 Resumo Executivo</div>', unsafe_allow_html=True)

    total = len(df_sistema)
    atrasadas = len(df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"])
    finalizado = len(df_sistema[df_sistema["CLASSIFICACAO"] == "✅ FINALIZADO"])
    pendencias = len(df_sistema[df_sistema["CLASSIFICACAO"] == "⏳ PENDÊNCIA"])
    avarias = len(df_sistema[df_sistema["CLASSIFICACAO"] == "⚠️ AVARIA"])
    no_piso = len(df_sistema[df_sistema["CLASSIFICACAO"] == "🟠 NO PISO"])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total AWBs", total)

    with col2:
        st.metric("🔴 Atrasadas", atrasadas)

    with col3:
        st.metric("✅ Tratadas pela Torre", finalizado)

    with col4:
        st.metric("📅 Finalizadas no Mês - Torre", finalizadas_mes)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("⏳ Pendências", pendencias)

    with col2:
        st.metric("⚠️ Avarias", avarias)

    with col3:
        st.metric("🟠 No Piso", no_piso)

    with col4:
        dias_atraso = df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"]

        if len(dias_atraso) > 0:
            try:
                dias_diff = [
                    (hoje - pd.to_datetime(s).date()).days
                    for s in dias_atraso["SLA"]
                    if not pd.isna(s)
                ]
                media = sum(dias_diff) / len(dias_diff) if dias_diff else 0
                st.metric("Média dias atrasadas", f"{media:.1f}".replace(".", ","))
            except:
                st.metric("Média dias atrasadas", "-")
        else:
            st.metric("Média dias atrasadas", "0")

    # ============================================================
    # ABAS
    # ============================================================
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Visual",
        "🔴 Atrasadas",
        "✅ Tratadas pela Torre",
        "⏳ Pendências",
        "⚠️ Avarias",
        "📥 Exportar"
    ])

    with tab1:
        st.markdown('<div class="section-title">Gráficos de Status</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            status_counts = df_sistema["CLASSIFICACAO"].value_counts()
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Distribuição de Status"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            status_counts2 = df_sistema["CLASSIFICACAO"].value_counts()
            fig_bar = px.bar(
                x=status_counts2.index,
                y=status_counts2.values,
                title="Contagem por Status"
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.markdown('<div class="section-title">Cargas Atrasadas</div>', unsafe_allow_html=True)

        df_atraso = df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"].copy()

        if len(df_atraso) > 0:
            df_atraso["dias_atraso"] = df_atraso["SLA"].apply(
                lambda x: (hoje - pd.to_datetime(x).date()).days if not pd.isna(x) else 0
            )

            df_atraso = df_atraso.sort_values("dias_atraso", ascending=False)

            for _, row in df_atraso.iterrows():
                dias = row["dias_atraso"]
                col1, col2, col3 = st.columns([1, 2, 2])

                with col1:
                    st.markdown(
                        f"<div style='font-size:20px;font-weight:900;color:#FF2D2D'>{dias}</div>",
                        unsafe_allow_html=True
                    )

                with col2:
                    st.write(f"**AWB:** {row['awb_norm']}")

                with col3:
                    st.write(f"**SLA:** {row['SLA']}")
        else:
            st.success("✅ Nenhuma carga atrasada!")

    with tab3:
        st.markdown('<div class="section-title">Tratadas pela Torre</div>', unsafe_allow_html=True)

        df_trat = df_sistema[df_sistema["CLASSIFICACAO"] == "✅ FINALIZADO"]

        if len(df_trat) > 0:
            st.dataframe(
                df_trat[["awb_norm", "SLA", "StatusDescription"]].rename(columns={
                    "awb_norm": "AWB",
                    "SLA": "SLA",
                    "StatusDescription": "Status"
                }),
                use_container_width=True
            )
        else:
            st.info("ℹ️ Nenhuma carga tratada pela Torre")

    with tab4:
        st.markdown('<div class="section-title">Pendências</div>', unsafe_allow_html=True)

        df_pend = df_sistema[df_sistema["CLASSIFICACAO"] == "⏳ PENDÊNCIA"]

        if len(df_pend) > 0:
            st.dataframe(
                df_pend[["awb_norm", "SLA", "StatusDescription"]].rename(columns={
                    "awb_norm": "AWB",
                    "SLA": "SLA",
                    "StatusDescription": "Status"
                }),
                use_container_width=True
            )
        else:
            st.info("ℹ️ Nenhuma pendência")

    with tab5:
        st.markdown('<div class="section-title">Avarias</div>', unsafe_allow_html=True)

        df_avar = df_sistema[df_sistema["CLASSIFICACAO"] == "⚠️ AVARIA"]

        if len(df_avar) > 0:
            st.dataframe(
                df_avar[["awb_norm", "SLA", "StatusDescription"]].rename(columns={
                    "awb_norm": "AWB",
                    "SLA": "SLA",
                    "StatusDescription": "Status"
                }),
                use_container_width=True
            )
        else:
            st.info("ℹ️ Nenhuma avaria")

    with tab6:
        st.markdown('<div class="section-title">Exportar Dados</div>', unsafe_allow_html=True)

        output = BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_sistema.to_excel(writer, sheet_name="Todas as Cargas", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"].to_excel(writer, sheet_name="Atrasadas", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "✅ FINALIZADO"].to_excel(writer, sheet_name="Tratadas pela Torre", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "⏳ PENDÊNCIA"].to_excel(writer, sheet_name="Pendências", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "⚠️ AVARIA"].to_excel(writer, sheet_name="Avarias", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "🟠 NO PISO"].to_excel(writer, sheet_name="No Piso", index=False)

        output.seek(0)

        st.download_button(
            label="📥 Baixar Excel (Múltiplas abas)",
            data=output.getvalue(),
            file_name="relatorio_cargas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            label="📄 Baixar CSV",
            data=df_sistema.to_csv(index=False),
            file_name="relatorio_cargas.csv",
            mime="text/csv"
        )

    st.markdown("✅ Dados processados e classificados com sucesso!")
    st.markdown("✅ Dados processados e classificados com sucesso!")
