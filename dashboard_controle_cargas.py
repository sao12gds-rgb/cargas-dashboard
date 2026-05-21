from __future__ import annotations
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Dashboard Controle de Cargas - GDS Logística",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    * { margin: 0; padding: 0; }
    .stApp { background-color: #F5F7FB; }
    
    /* CABEÇALHO PROFISSIONAL */
    .header-container {
        background: linear-gradient(135deg, #003B71 0%, #005DAA 100%);
        color: white;
        padding: 30px 40px;
        border-radius: 12px;
        margin: 0 0 30px 0;
        box-shadow: 0 6px 20px rgba(0, 59, 113, 0.2);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 30px;
    }
    
    .header-left {
        display: flex;
        align-items: center;
        gap: 20px;
        flex: 1;
    }
    
    .header-logo-box {
        width: 70px;
        height: 70px;
        background: white;
        border-radius: 10px;
        padding: 5px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .header-logo-box img {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    
    .header-text h1 {
        font-size: 28px;
        font-weight: 900;
        margin: 0;
        line-height: 1.3;
    }
    
    .header-text p {
        font-size: 14px;
        margin: 8px 0 0 0;
        opacity: 0.95;
        font-weight: 500;
    }
    
    .header-badge {
        background: rgba(255, 138, 0, 0.2);
        color: #FFD580;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
        white-space: nowrap;
        flex-shrink: 0;
    }
    
    /* SEÇÕES */
    .section-title {
        color: #003B71;
        font-size: 20px;
        font-weight: 800;
        margin-top: 28px;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 3px solid #FF8A00;
        display: inline-block;
    }
    
    .kpi-value { 
        color: #003B71; 
        font-size: 28px; 
        font-weight: 900; 
    }
    
    .dias-atraso { 
        color: #FF2D2D; 
        font-weight: 900; 
        font-size: 24px; 
    }
    
    .reentrega-alert {
        background: #FFF3E8;
        border-left: 4px solid #FF8A00;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CABEÇALHO PROFISSIONAL COM LOGO
# ============================================================
st.markdown("""
<div class="header-container">
    <div class="header-left">
        <div class="header-logo-box">
            <img src="data:image/png;base64,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" alt="GDS Logística">
        </div>
        <div class="header-text">
            <h1>📦 Dashboard de Controle de Cargas</h1>
            <p>Monitoramento em tempo real • DIAS EM ATRASO & REENTREGA PENDENTE</p>
        </div>
    </div>
    <div class="header-badge">🚚 GDS LOGÍSTICA</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÕES
# ============================================================
def normalizar_awb(valor: object) -> str:
    """Normaliza AWB para 8 dígitos"""
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
    """Encontra coluna de forma flexível"""
    colunas_lower = {col.lower().strip(): col for col in df.columns}
    
    for opcao in opcoes:
        opcao_lower = opcao.lower().strip()
        if opcao_lower in colunas_lower:
            return colunas_lower[opcao_lower]
        for col_lower, col_original in colunas_lower.items():
            if opcao_lower in col_lower or col_lower in opcao_lower:
                return col_original
    return None


def format_int(valor) -> str:
    try:
        return f"{int(valor):,}".replace(",", ".") if not pd.isna(valor) else "0"
    except:
        return "0"


def format_pct(valor) -> str:
    return f"{float(valor):.1f}%".replace(".", ",") if not pd.isna(valor) else "-"


# ============================================================
# UPLOAD DOS ARQUIVOS
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
    
    # CARREGAMENTO
    with st.spinner("⏳ Carregando Relatório do Sistema..."):
        df_sistema = pd.read_excel(arquivo_sistema, sheet_name="Report") \
            if "xlsx" in arquivo_sistema.name or "xls" in arquivo_sistema.name \
            else pd.read_csv(arquivo_sistema)
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
        
        st.success(f"✅ PENDENCIAS: {len(df_pendencias)} | CORP: {len(df_pendencia_corp)} | AVARIAS: {len(df_avarias)} | FINALIZADAS: {len(df_finalizadas)}")
    
    # NORMALIZAR AWB
    df_sistema["awb_norm"] = df_sistema["AWB"].apply(normalizar_awb)
    df_pendencias["awb_norm"] = df_pendencias["AWB"].apply(normalizar_awb)
    df_pendencia_corp["awb_norm"] = df_pendencia_corp["AWB"].apply(normalizar_awb)
    df_avarias["awb_norm"] = df_avarias["AWB"].apply(normalizar_awb)
    df_finalizadas["awb_norm"] = df_finalizadas["AWB"].apply(normalizar_awb)
    
    # CLASSIFICAÇÃO
    def classificar(row):
        awb = row["awb_norm"]
        sla_str = row.get("SLA")
        
        if pd.isna(sla_str):
            return "❓ SEM SLA"
        
        try:
            sla = pd.to_datetime(sla_str).date()
            hoje = datetime.now().date()
        except:
            return "❓ SEM SLA"
        
        em_finalizadas = awb in df_finalizadas["awb_norm"].values
        em_pendencias = awb in df_pendencias["awb_norm"].values or awb in df_pendencia_corp["awb_norm"].values
        em_avarias = awb in df_avarias["awb_norm"].values
        
        status_sistema = df_sistema[df_sistema["awb_norm"] == awb]["StatusDescription"].values
        tem_pendente_entrega = any("Pendente" in str(s) and "Entrega" in str(s) for s in status_sistema) if len(status_sistema) > 0 else False
        
        if em_finalizadas and tem_pendente_entrega:
            return "🔄 REENTREGA PENDENTE"
        elif em_finalizadas:
            return "✅ FINALIZADO"
        elif em_pendencias:
            return "⏳ PENDÊNCIA"
        elif em_avarias:
            return "⚠️ AVARIA"
        elif sla < hoje:
            return "🔴 ATRASADA"
        elif sla == hoje:
            return "🟠 NO PISO"
        else:
            return "🟢 MONITORAR"
    
    df_sistema["CLASSIFICACAO"] = df_sistema.apply(classificar, axis=1)
    
    # RESUMO
    st.markdown('<div class="section-title">📊 Resumo Executivo</div>', unsafe_allow_html=True)
    
    total = len(df_sistema)
    atrasadas = len(df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"])
    reentrega = len(df_sistema[df_sistema["CLASSIFICACAO"] == "🔄 REENTREGA PENDENTE"])
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
        st.metric("🔄 Reentrega", reentrega)
    with col4:
        st.metric("✅ Finalizadas", finalizado)
    
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
                dias_diff = [(datetime.now().date() - pd.to_datetime(s).date()).days for s in dias_atraso["SLA"] if not pd.isna(s)]
                media = sum(dias_diff) / len(dias_diff) if dias_diff else 0
                st.metric("Média dias atrasadas", f"{media:.1f}".replace(".", ","))
            except:
                st.metric("Média dias atrasadas", "-")
        else:
            st.metric("Média dias atrasadas", "0")
    
    # ABAS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Visual",
        "🔴 Atrasadas",
        "🔄 Reentrega",
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
                title="Contagem por Status",
                labels={"x": "Status", "y": "Quantidade"}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab2:
        st.markdown('<div class="section-title">Cargas Atrasadas</div>', unsafe_allow_html=True)
        
        df_atraso = df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"].copy()
        
        if len(df_atraso) > 0:
            df_atraso["dias_atraso"] = df_atraso["SLA"].apply(
                lambda x: (datetime.now().date() - pd.to_datetime(x).date()).days if not pd.isna(x) else 0
            )
            df_atraso = df_atraso.sort_values("dias_atraso", ascending=False)
            
            for _, row in df_atraso.iterrows():
                dias = row["dias_atraso"]
                col1, col2, col3 = st.columns([1, 2, 2])
                with col1:
                    st.markdown(f"<div style='font-size:20px;font-weight:900;color:#FF2D2D'>{dias}</div>", unsafe_allow_html=True)
                with col2:
                    st.write(f"**AWB:** {row['awb_norm']}")
                with col3:
                    st.write(f"**SLA:** {row['SLA']}")
        else:
            st.success("✅ Nenhuma carga atrasada!")
    
    with tab3:
        st.markdown('<div class="section-title">Reentrega Pendente</div>', unsafe_allow_html=True)
        
        df_reen = df_sistema[df_sistema["CLASSIFICACAO"] == "🔄 REENTREGA PENDENTE"].copy()
        
        if len(df_reen) > 0:
            df_reen_dados = []
            for awb in df_reen["awb_norm"]:
                fin = df_finalizadas[df_finalizadas["awb_norm"] == awb]
                if len(fin) > 0:
                    df_reen_dados.append({
                        "AWB": awb,
                        "Data Finalização": fin.iloc[0].get("DATA MOV. FINALIZAÇÃO", "-")
                    })
            
            if df_reen_dados:
                st.dataframe(pd.DataFrame(df_reen_dados), use_container_width=True)
        else:
            st.info("ℹ️ Nenhuma reentrega pendente")
    
    with tab4:
        st.markdown('<div class="section-title">Pendências</div>', unsafe_allow_html=True)
        
        df_pend = df_sistema[df_sistema["CLASSIFICACAO"] == "⏳ PENDÊNCIA"].copy()
        
        if len(df_pend) > 0:
            st.dataframe(df_pend[["awb_norm", "SLA", "StatusDescription"]].rename(columns={
                "awb_norm": "AWB",
                "SLA": "SLA",
                "StatusDescription": "Status"
            }), use_container_width=True)
        else:
            st.info("ℹ️ Nenhuma pendência")
    
    with tab5:
        st.markdown('<div class="section-title">Avarias</div>', unsafe_allow_html=True)
        
        df_avar = df_sistema[df_sistema["CLASSIFICACAO"] == "⚠️ AVARIA"].copy()
        
        if len(df_avar) > 0:
            st.dataframe(df_avar[["awb_norm", "SLA", "StatusDescription"]].rename(columns={
                "awb_norm": "AWB",
                "SLA": "SLA",
                "StatusDescription": "Status"
            }), use_container_width=True)
        else:
            st.info("ℹ️ Nenhuma avaria")
    
    with tab6:
        st.markdown('<div class="section-title">Exportar Dados</div>', unsafe_allow_html=True)
        
        # Exportar completo
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_sistema.to_excel(writer, sheet_name="Todas as Cargas", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "🔴 ATRASADA"].to_excel(writer, sheet_name="Atrasadas", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "🔄 REENTREGA PENDENTE"].to_excel(writer, sheet_name="Reentrega", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "⏳ PENDÊNCIA"].to_excel(writer, sheet_name="Pendências", index=False)
            df_sistema[df_sistema["CLASSIFICACAO"] == "⚠️ AVARIA"].to_excel(writer, sheet_name="Avarias", index=False)
        
        output.seek(0)
        st.download_button(
            label="📥 Baixar Excel (Múltiplas abas)",
            data=output.getvalue(),
            file_name="relatorio_cargas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # CSV
        st.download_button(
            label="📄 Baixar CSV (Todas as cargas)",
            data=df_sistema.to_csv(index=False),
            file_name="relatorio_cargas.csv",
            mime="text/csv"
        )
    
    st.markdown("✅ Dados processados e classificados com sucesso!")
