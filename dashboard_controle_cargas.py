from __future__ import annotations

from io import BytesIO
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st


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
        padding: 24px 28px;
        border-radius: 22px;
        margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-size: 31px; }
    .section-title {
        color: #003B71;
        font-size: 21px;
        font-weight: 800;
        margin-top: 26px;
        margin-bottom: 12px;
    }
    .kpi-card {
        background: #FFFFFF;
        border-radius: 18px;
        padding: 18px;
        border: 1px solid #E7ECF3;
    }
    .kpi-value { color: #003B71; font-size: 27px; font-weight: 900; }
    .alert-card {
        background: #FFF3E8;
        border-left: 6px solid #FF8A00;
        padding: 14px 16px;
        border-radius: 14px;
    }
</style>
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
    
    # Se tem 15 dígitos (577XXXXXXXX0001), remove 577 e últimos 4
    if len(apenas) == 15 and apenas.startswith("577"):
        apenas = apenas[3:11]
    # Se tem prefixo 577 e mais de 8, remove prefixo
    elif apenas.startswith("577") and len(apenas) > 8:
        apenas = apenas[3:]
    
    return apenas.lstrip("0") or apenas


def encontrar_coluna(df: pd.DataFrame, opcoes: list[str]) -> str | None:
    """Encontra coluna de forma flexível, ignorando maiúsculas/minúsculas e espaços"""
    colunas_lower = {col.lower().strip(): col for col in df.columns}
    
    for opcao in opcoes:
        opcao_lower = opcao.lower().strip()
        if opcao_lower in colunas_lower:
            return colunas_lower[opcao_lower]
        # Busca parcial também
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


@st.cache_data
def carregar_arquivo(uploaded_file):
    nome = uploaded_file.name.lower()
    if nome.endswith(".csv"):
        return pd.read_csv(uploaded_file, sep=None, engine="python")
    else:
        return pd.read_excel(uploaded_file, sheet_name=None)


# ============================================================
# CABEÇALHO
# ============================================================
st.markdown("""
    <div class="hero">
        <h1>📦 Dashboard de Controle de Cargas</h1>
        <p>Análise integrada com classificação automática de status e criticidade.</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# UPLOAD
# ============================================================
with st.sidebar:
    st.header("📁 Arquivos")
    
    arquivo_sistema = st.file_uploader(
        "1️⃣ Relatório do Sistema",
        type=["xlsx", "xls", "csv"],
        key="sistema",
    )
    
    arquivo_consolidado = st.file_uploader(
        "2️⃣ Planilha Consolidada (abas: PENDÊNCIAS, PENDÊNCIA CORP, AVARIAS, FINALIZADAS)",
        type=["xlsx", "xls"],
        key="consolidada",
    )

if arquivo_sistema is None:
    st.info("📂 Carregue o Relatório do Sistema para iniciar.")
    st.stop()

# Carregar Sistema
with st.spinner("⏳ Processando Relatório do Sistema..."):
    try:
        df_sistema_raw = pd.read_csv(arquivo_sistema, sep=None, engine="python") if arquivo_sistema.name.endswith(".csv") else pd.read_excel(arquivo_sistema)
        # Normalizar nomes de colunas (remover espaços)
        df_sistema_raw.columns = df_sistema_raw.columns.str.strip()
        st.success(f"✅ Relatório do Sistema carregado! ({len(df_sistema_raw)} linhas)")
    except Exception as e:
        st.error(f"❌ Erro ao ler Sistema: {e}")
        st.stop()

if df_sistema_raw.empty:
    st.error("❌ Arquivo vazio!")
    st.stop()

# Carregar Consolidada (opcional)
abas_consolidadas = {}
if arquivo_consolidado is not None:
    with st.spinner("⏳ Processando Planilha Consolidada..."):
        try:
            excel_file = pd.ExcelFile(arquivo_consolidado)
            abas_consolidadas = {}
            
            for sheet_name in excel_file.sheet_names:
                if sheet_name.lower() == "avarias":
                    # AVARIAS tem header estranho, pula primeira linha
                    df_aba = pd.read_excel(arquivo_consolidado, sheet_name=sheet_name, skiprows=1)
                else:
                    df_aba = pd.read_excel(arquivo_consolidado, sheet_name=sheet_name)
                
                # Normalizar nomes de colunas (remover espaços)
                df_aba.columns = df_aba.columns.str.strip()
                abas_consolidadas[sheet_name] = df_aba
            
            st.success(f"✅ Planilha Consolidada carregada! ({len(abas_consolidadas)} abas encontradas)")
        except Exception as e:
            st.error(f"❌ Erro ao ler Consolidada: {e}")
else:
    st.warning("⚠️ Nenhuma planilha consolidada carregada. Usando apenas Relatório do Sistema.")


# ============================================================
# PROCESSAMENTO
# ============================================================
df = df_sistema_raw.copy()

col_awb = encontrar_coluna(df, ["AWB", "numero", "awb"])
col_sla = encontrar_coluna(df, ["SLA", "data", "prazo"])
col_status = encontrar_coluna(df, ["status"])
col_origem = encontrar_coluna(df, ["origem", "origin"])
col_destino = encontrar_coluna(df, ["destino", "destination"])

if col_awb is None or col_sla is None:
    st.error("Colunas obrigatórias não encontradas (AWB, SLA)")
    st.write("Colunas disponíveis:", list(df.columns))
    st.stop()

# Normalizar Sistema
df_work = df.copy()
df_work["AWB"] = df_work[col_awb].apply(normalizar_awb)
df_work["SLA_dt"] = pd.to_datetime(df_work[col_sla], errors="coerce", dayfirst=True)

if col_status:
    df_work["Status Sistema"] = df_work[col_status]
else:
    df_work["Status Sistema"] = "-"

if col_origem:
    df_work["Origem"] = df_work[col_origem]
else:
    df_work["Origem"] = "-"

if col_destino:
    df_work["Destino"] = df_work[col_destino]
else:
    df_work["Destino"] = "-"


# ============================================================
# PROCESSAR ABAS CONSOLIDADAS
# ============================================================
df_pendencias = pd.DataFrame()
df_pendencia_corp = pd.DataFrame()
df_avarias = pd.DataFrame()
df_finalizadas = pd.DataFrame()

if abas_consolidadas:
    st.info("🔄 Processando abas consolidadas...")
    
    # Localizar abas
    abas_encontradas = []
    for nome_aba, df_aba in abas_consolidadas.items():
        # Normalizar nomes de colunas (remover espaços)
        df_aba.columns = df_aba.columns.str.strip()
        
        nome_lower = nome_aba.lower()
        
        # Procurar coluna AWB (com espaços ou sem)
        col_aba_awb = None
        for col in df_aba.columns:
            if "awb" in col.lower():
                col_aba_awb = col
                break
        
        if col_aba_awb:
            df_aba["AWB_Norm"] = df_aba[col_aba_awb].apply(normalizar_awb)
        
        if "pend" in nome_lower and "corp" not in nome_lower:
            df_pendencias = df_aba.copy()
            abas_encontradas.append(f"✅ PENDÊNCIAS ({len(df_aba)} linhas)")
        elif "corp" in nome_lower:
            df_pendencia_corp = df_aba.copy()
            abas_encontradas.append(f"✅ PENDÊNCIA CORP ({len(df_aba)} linhas)")
        elif "avaria" in nome_lower:
            df_avarias = df_aba.copy()
            abas_encontradas.append(f"✅ AVARIAS ({len(df_aba)} linhas)")
        elif "finaliza" in nome_lower:
            df_finalizadas = df_aba.copy()
            abas_encontradas.append(f"✅ FINALIZADAS ({len(df_aba)} linhas)")
    
    if abas_encontradas:
        st.success("Abas processadas:")
        for aba in abas_encontradas:
            st.write(aba)


# ============================================================
# CLASSIFICAÇÃO
# ============================================================
def classificar(row):
    awb = row.get("AWB")
    sla = row.get("SLA_dt")
    hoje = pd.Timestamp.now().normalize()
    
    # Finalizadas
    if not df_finalizadas.empty and "AWB_Norm" in df_finalizadas.columns:
        if awb in df_finalizadas["AWB_Norm"].values:
            return "FINALIZADO"
    
    # Pendências
    em_pend = False
    if not df_pendencias.empty and "AWB_Norm" in df_pendencias.columns:
        if awb in df_pendencias["AWB_Norm"].values:
            em_pend = True
    if not df_pendencia_corp.empty and "AWB_Norm" in df_pendencia_corp.columns:
        if awb in df_pendencia_corp["AWB_Norm"].values:
            em_pend = True
    
    if em_pend:
        return "CARGA NA PENDÊNCIA"
    
    # Avarias
    if not df_avarias.empty and "AWB_Norm" in df_avarias.columns:
        if awb in df_avarias["AWB_Norm"].values:
            return "CARGA COM AVARIA"
    
    # SLA
    if pd.isna(sla):
        return "SEM SLA"
    
    sla_norm = sla.normalize()
    if sla_norm == hoje:
        return "CARGA NO PISO"
    elif sla_norm < hoje:
        return "CARGA ATRASADA"
    else:
        return "MONITORAR"


def criticidade(status):
    mapa = {
        "CARGA ATRASADA": "ALTA",
        "CARGA NO PISO": "MÉDIA",
        "CARGA NA PENDÊNCIA": "CONTROLADA",
        "CARGA COM AVARIA": "AVARIA",
        "FINALIZADO": "OK",
        "MONITORAR": "BAIXA",
        "SEM SLA": "-",
    }
    return mapa.get(status, "-")


df_work["Status Final"] = df_work.apply(classificar, axis=1)
df_work["Criticidade"] = df_work["Status Final"].apply(criticidade)
df_work["Dias em Atraso"] = (pd.Timestamp.now().normalize() - df_work["SLA_dt"].dt.normalize()).dt.days
df_work["Dias em Atraso"] = df_work["Dias em Atraso"].apply(lambda x: max(0, int(x)) if not pd.isna(x) else 0)

st.success("✅ Dados processados e classificados com sucesso!")


# ============================================================
# FILTROS
# ============================================================
with st.sidebar:
    st.header("🔎 Filtros")
    
    status_opts = ["Todos"] + sorted([x for x in df_work["Status Final"].unique() if pd.notna(x)])
    status_sel = st.multiselect("Status Final", status_opts, default=["Todos"])
    if status_sel and "Todos" not in status_sel:
        df_work = df_work[df_work["Status Final"].isin(status_sel)]
    
    crit_opts = ["Todos"] + sorted([x for x in df_work["Criticidade"].unique() if pd.notna(x)])
    crit_sel = st.multiselect("Criticidade", crit_opts, default=["Todos"])
    if crit_sel and "Todos" not in crit_sel:
        df_work = df_work[df_work["Criticidade"].isin(crit_sel)]

if df_work.empty:
    st.warning("Nenhum dado para filtros selecionados.")
    st.stop()

# Mostrar resumo de processamento
st.info(f"📊 Dashboard processado com **{len(df_work)}** AWBs | **{(df_work['Criticidade'] == 'ALTA').sum()}** críticas | **{(df_work['Criticidade'] == 'AVARIA').sum()}** avarias | **{(df_work['Status Final'] == 'FINALIZADO').sum()}** finalizadas")


# ============================================================
# KPIs
# ============================================================
st.markdown('<div class="section-title">📊 Resumo</div>', unsafe_allow_html=True)

total = len(df_work)
finalizadas = int((df_work["Status Final"] == "FINALIZADO").sum())
pendencias = int((df_work["Status Final"] == "CARGA NA PENDÊNCIA").sum())
avarias = int((df_work["Status Final"] == "CARGA COM AVARIA").sum())
atrasadas = int((df_work["Status Final"] == "CARGA ATRASADA").sum())
alta = int((df_work["Criticidade"] == "ALTA").sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total AWBs", format_int(total))
with c2:
    st.metric("Finalizadas", f"{format_int(finalizadas)} ({format_pct(finalizadas/total*100 if total else 0)})")
with c3:
    st.metric("Críticas", f"{format_int(alta)} ({format_pct(alta/total*100 if total else 0)})")
with c4:
    st.metric("Pendências", f"{format_int(pendencias)} ({format_pct(pendencias/total*100 if total else 0)})")

c5, c6, c7, c8 = st.columns(4)
with c5:
    st.metric("Avarias", f"{format_int(avarias)} ({format_pct(avarias/total*100 if total else 0)})")
with c6:
    st.metric("Atrasadas", f"{format_int(atrasadas)} ({format_pct(atrasadas/total*100 if total else 0)})")
with c7:
    piso = int((df_work["Status Final"] == "CARGA NO PISO").sum())
    st.metric("No Piso", format_int(piso))
with c8:
    dias_media = df_work[df_work["Dias em Atraso"] > 0]["Dias em Atraso"].mean()
    st.metric("Média dias atrasadas", f"{dias_media:.1f}".replace(".", ","))


# ============================================================
# ABAS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Visual",
    "🚨 Críticas",
    "⏳ Pendências",
    "⚠️ Avarias",
    "✅ Finalizadas",
    "📥 Exportação"
])


# ============================================================
# ABA 1: VISUAL
# ============================================================
with tab1:
    st.markdown('<div class="section-title">Status</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        status_dist = df_work["Status Final"].value_counts().reset_index()
        status_dist.columns = ["Status", "Quantidade"]
        if not status_dist.empty:
            fig = px.pie(status_dist, values="Quantidade", names="Status", hole=0.55)
            st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        crit_dist = df_work["Criticidade"].value_counts().reset_index()
        crit_dist.columns = ["Criticidade", "Quantidade"]
        if not crit_dist.empty:
            fig = px.pie(crit_dist, values="Quantidade", names="Criticidade", hole=0.55)
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# ABA 2: CRÍTICAS
# ============================================================
with tab2:
    st.markdown('<div class="section-title">🚨 Cargas Críticas (ALTA)</div>', unsafe_allow_html=True)
    
    df_criticas = df_work[df_work["Criticidade"] == "ALTA"].copy()
    st.write(f"**{len(df_criticas)} cargas críticas encontradas**")
    
    colunas = ["AWB", "Status Final", "Criticidade", "Dias em Atraso", "Status Sistema"]
    colunas = [c for c in colunas if c in df_criticas.columns]
    
    if not df_criticas.empty:
        st.dataframe(df_criticas[colunas].sort_values("Dias em Atraso", ascending=False), use_container_width=True, hide_index=True)


# ============================================================
# ABA 3: PENDÊNCIAS
# ============================================================
with tab3:
    st.markdown('<div class="section-title">⏳ Pendências</div>', unsafe_allow_html=True)
    
    df_pend_vis = df_work[df_work["Status Final"] == "CARGA NA PENDÊNCIA"].copy()
    st.write(f"**{len(df_pend_vis)} cargas em pendência**")
    
    colunas = ["AWB", "Status Final", "Criticidade", "Status Sistema"]
    colunas = [c for c in colunas if c in df_pend_vis.columns]
    
    if not df_pend_vis.empty:
        st.dataframe(df_pend_vis[colunas], use_container_width=True, hide_index=True)


# ============================================================
# ABA 4: AVARIAS
# ============================================================
with tab4:
    st.markdown('<div class="section-title">⚠️ Avarias</div>', unsafe_allow_html=True)
    
    df_avar = df_work[df_work["Status Final"] == "CARGA COM AVARIA"].copy()
    st.write(f"**{len(df_avar)} cargas com avaria**")
    
    colunas = ["AWB", "Status Final", "Criticidade", "Status Sistema"]
    colunas = [c for c in colunas if c in df_avar.columns]
    
    if not df_avar.empty:
        st.dataframe(df_avar[colunas], use_container_width=True, hide_index=True)


# ============================================================
# ABA 5: FINALIZADAS
# ============================================================
with tab5:
    st.markdown('<div class="section-title">✅ Finalizadas</div>', unsafe_allow_html=True)
    
    df_fin = df_work[df_work["Status Final"] == "FINALIZADO"].copy()
    st.write(f"**{len(df_fin)} cargas finalizadas**")
    
    colunas = ["AWB", "Status Final", "Status Sistema"]
    colunas = [c for c in colunas if c in df_fin.columns]
    
    if not df_fin.empty:
        st.dataframe(df_fin[colunas], use_container_width=True, hide_index=True)


# ============================================================
# ABA 6: EXPORTAÇÃO
# ============================================================
with tab6:
    st.markdown('<div class="section-title">📥 Exportação</div>', unsafe_allow_html=True)
    
    colunas_export = ["AWB", "Status Final", "Criticidade", "Dias em Atraso", "Status Sistema"]
    colunas_export = [c for c in colunas_export if c in df_work.columns]
    
    st.dataframe(df_work[colunas_export], use_container_width=True, hide_index=True)
    
    # Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#003B71", "font_color": "white"})
        
        abas = {
            "Base Filtrada": df_work[colunas_export],
            "Críticas": df_work[df_work["Criticidade"] == "ALTA"][colunas_export],
            "Pendências": df_work[df_work["Status Final"] == "CARGA NA PENDÊNCIA"][colunas_export],
            "Avarias": df_work[df_work["Status Final"] == "CARGA COM AVARIA"][colunas_export],
            "Finalizadas": df_work[df_work["Status Final"] == "FINALIZADO"][colunas_export],
        }
        
        for nome_aba, df_aba in abas.items():
            if df_aba.empty:
                continue
            sheet = nome_aba[:31]
            df_aba.to_excel(writer, sheet_name=sheet, index=False)
            worksheet = writer.sheets[sheet]
            for col_num, value in enumerate(df_aba.columns):
                worksheet.write(0, col_num, value, header_fmt)
    
    st.download_button(
        "📥 Excel",
        output.getvalue(),
        "relatorio.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # CSV
    csv = df_work[colunas_export].to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        "📥 CSV",
        csv,
        "relatorio.csv",
        "text/csv"
    )


st.caption("Dashboard Controle de Cargas")

