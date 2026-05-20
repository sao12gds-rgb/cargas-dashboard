from __future__ import annotations

from io import BytesIO
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Dashboard Controle de Cargas",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# ESTILO VISUAL
# ============================================================
st.markdown(
    """
<style>
    .stApp { background-color: #F5F7FB; }
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

    .hero {
        background: linear-gradient(135deg, #003B71 0%, #005DAA 70%, #FF8A00 140%);
        color: white;
        padding: 24px 28px;
        border-radius: 22px;
        box-shadow: 0 10px 28px rgba(0,0,0,0.12);
        margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-size: 31px; line-height: 1.15; }
    .hero p { margin-top: 8px; margin-bottom: 0; opacity: 0.92; font-size: 15px; }

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
        padding: 18px 18px;
        min-height: 112px;
        border: 1px solid #E7ECF3;
        box-shadow: 0 5px 18px rgba(18,38,63,0.07);
    }
    .kpi-title { color: #627084; font-size: 13px; font-weight: 700; margin-bottom: 8px; }
    .kpi-value { color: #003B71; font-size: 27px; font-weight: 900; line-height: 1.1; }
    .kpi-note { color: #7A869A; font-size: 12px; margin-top: 7px; }

    .alert-card {
        background: #FFF3E8;
        border-left: 6px solid #FF8A00;
        padding: 14px 16px;
        border-radius: 14px;
        color: #5D3200;
        margin: 10px 0 16px 0;
        border-top: 1px solid #FFD1A3;
        border-right: 1px solid #FFD1A3;
        border-bottom: 1px solid #FFD1A3;
    }

    .insight-box {
        background: #FFFFFF;
        border-left: 6px solid #FF8A00;
        padding: 15px 18px;
        border-radius: 16px;
        border-top: 1px solid #E7ECF3;
        border-right: 1px solid #E7ECF3;
        border-bottom: 1px solid #E7ECF3;
        box-shadow: 0 5px 18px rgba(18,38,63,0.06);
        color: #233142;
        margin-bottom: 12px;
    }

    div[data-testid="stMetricValue"] { color: #003B71; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FUNÇÕES DE APOIO
# ============================================================
def remover_acentos(texto: str) -> str:
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in texto if not unicodedata.combining(ch))


def norm_txt(texto: object) -> str:
    return remover_acentos(str(texto).strip().lower())


def format_int(valor: float | int | None) -> str:
    try:
        if valor is None or pd.isna(valor):
            return "0"
        return f"{int(valor):,}".replace(",", ".")
    except Exception:
        return "0"


def format_pct(valor: float | int | None) -> str:
    if valor is None or pd.isna(valor):
        return "-"
    return f"{float(valor):.1f}%".replace(".", ",")


def format_float(valor: float | int | None, casas: int = 1) -> str:
    if valor is None or pd.isna(valor):
        return "-"
    return f"{float(valor):.{casas}f}".replace(".", ",")


def render_kpi(titulo: str, valor: str, nota: str = "") -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{titulo}</div>
            <div class="kpi-value">{valor}</div>
            <div class="kpi-note">{nota}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def encontrar_coluna(df: pd.DataFrame, opcoes: list[str]) -> str | None:
    mapa = {norm_txt(c): c for c in df.columns}
    for opcao in opcoes:
        if norm_txt(opcao) in mapa:
            return mapa[norm_txt(opcao)]
    return None


def normalizar_awb(valor: object) -> str:
    """Normaliza AWB removendo prefixo 577 quando existir (15 -> 8 dígitos)"""
    if pd.isna(valor):
        return ""
    txt = str(valor).strip()
    txt = txt.replace(".0", "") if txt.endswith(".0") else txt
    apenas = "".join(ch for ch in txt if ch.isdigit())
    if apenas.startswith("577") and len(apenas) > 8:
        apenas = apenas[3:]
    return apenas.lstrip("0") or apenas


def gerar_excel_multi(abas: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#003B71", "font_color": "white", "border": 1})
        date_fmt = workbook.add_format({"num_format": "dd/mm/yyyy"})

        for nome_aba, df_export in abas.items():
            if df_export is None or df_export.empty:
                continue
            sheet = nome_aba[:31]
            df_tmp = df_export.copy()
            df_tmp.to_excel(writer, sheet_name=sheet, index=False)
            worksheet = writer.sheets[sheet]
            for col_num, value in enumerate(df_tmp.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
                largura = min(max(len(str(value)) + 2, 12), 45)
                worksheet.set_column(col_num, col_num, largura)
            worksheet.freeze_panes(1, 0)
    return output.getvalue()


@st.cache_data(show_spinner=False)
def carregar_arquivo(uploaded_file) -> pd.DataFrame:
    nome = uploaded_file.name.lower()
    if nome.endswith(".csv"):
        df0 = pd.read_csv(uploaded_file, sep=None, engine="python")
    else:
        df0 = pd.read_excel(uploaded_file)
    df0.columns = [str(c).strip() for c in df0.columns]
    return df0


# ============================================================
# CABEÇALHO
# ============================================================
st.markdown(
    """
    <div class="hero">
        <h1>📦 Dashboard de Controle de Cargas</h1>
        <p>Análise integrada de pendências, avarias e finalizações com classificação automática de status e criticidade.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# UPLOAD
# ============================================================
with st.sidebar:
    st.header("📁 Arquivos")
    st.info("Carregue os arquivos do seu sistema de controle")
    
    arquivo_sistema = st.file_uploader(
        "1) Relatório do Sistema (AWBs ativas)",
        type=["xlsx", "xls", "csv"],
        key="arquivo_sistema",
    )
    arquivo_pendencias = st.file_uploader(
        "2) PENDÊNCIAS (aba PENDENCIAS)",
        type=["xlsx", "xls", "csv"],
        key="arquivo_pendencias",
    )
    arquivo_pendencia_corp = st.file_uploader(
        "3) PENDÊNCIA CORP (aba PENDENCIA CORP)",
        type=["xlsx", "xls", "csv"],
        key="arquivo_pendencia_corp",
    )
    arquivo_avarias = st.file_uploader(
        "4) AVARIAS (aba AVARIAS)",
        type=["xlsx", "xls", "csv"],
        key="arquivo_avarias",
    )
    arquivo_finalizadas = st.file_uploader(
        "5) FINALIZADAS (aba FINALIZADAS)",
        type=["xlsx", "xls", "csv"],
        key="arquivo_finalizadas",
    )

if arquivo_sistema is None:
    st.info("Carregue pelo menos o Relatório do Sistema para iniciar a análise.")
    st.stop()

try:
    df_sistema_raw = carregar_arquivo(arquivo_sistema)
except Exception as exc:
    st.error(f"Erro ao ler o Relatório do Sistema: {exc}")
    st.stop()

if df_sistema_raw.empty:
    st.warning("O arquivo do Sistema está vazio.")
    st.stop()

df_pendencias_raw = pd.DataFrame()
if arquivo_pendencias is not None:
    try:
        df_pendencias_raw = carregar_arquivo(arquivo_pendencias)
    except Exception as exc:
        st.error(f"Erro ao ler PENDÊNCIAS: {exc}")

df_pendencia_corp_raw = pd.DataFrame()
if arquivo_pendencia_corp is not None:
    try:
        df_pendencia_corp_raw = carregar_arquivo(arquivo_pendencia_corp)
    except Exception as exc:
        st.error(f"Erro ao ler PENDÊNCIA CORP: {exc}")

df_avarias_raw = pd.DataFrame()
if arquivo_avarias is not None:
    try:
        df_avarias_raw = carregar_arquivo(arquivo_avarias)
    except Exception as exc:
        st.error(f"Erro ao ler AVARIAS: {exc}")

df_finalizadas_raw = pd.DataFrame()
if arquivo_finalizadas is not None:
    try:
        df_finalizadas_raw = carregar_arquivo(arquivo_finalizadas)
    except Exception as exc:
        st.error(f"Erro ao ler FINALIZADAS: {exc}")


# ============================================================
# MAPEAMENTO DO SISTEMA
# ============================================================
df = df_sistema_raw.copy()

col_awb = encontrar_coluna(df, ["AWB", "Numero AWB", "Número AWB", "AWBNumber"])
col_sla = encontrar_coluna(df, ["SLA", "Data SLA", "Data Prevista", "Prazo"])
col_status = encontrar_coluna(df, ["Status", "Status Sistema"])
col_origem = encontrar_coluna(df, ["Origem", "Origin"])
col_destino = encontrar_coluna(df, ["Destino", "Destination"])

if col_awb is None or col_sla is None:
    st.error("Não encontrei colunas obrigatórias (AWB, SLA). Verifique o arquivo.")
    st.write("Colunas encontradas:", list(df.columns))
    st.stop()

df_work = df.copy()
df_work["AWB"] = df_work[col_awb].apply(normalizar_awb)
df_work["SLA_dt"] = pd.to_datetime(df_work[col_sla], errors="coerce", dayfirst=True)
df_work["Data Hoje"] = pd.Timestamp.now().date()

if col_status:
    df_work["Status Sistema"] = df_work[col_status]
else:
    df_work["Status Sistema"] = "Desconhecido"

if col_origem:
    df_work["Origem"] = df_work[col_origem]
else:
    df_work["Origem"] = "-"
    
if col_destino:
    df_work["Destino"] = df_work[col_destino]
else:
    df_work["Destino"] = "-"


# ============================================================
# PROCESSAR PENDÊNCIAS
# ============================================================
df_pend = pd.DataFrame()
if not df_pendencias_raw.empty:
    df_pend = df_pendencias_raw.copy()
    col_pend_awb = encontrar_coluna(df_pend, ["AWB", "Numero AWB", "Número AWB", "AWBNumber"])
    if col_pend_awb:
        df_pend["AWB_Normalizada"] = df_pend[col_pend_awb].apply(normalizar_awb)

df_pend_corp = pd.DataFrame()
if not df_pendencia_corp_raw.empty:
    df_pend_corp = df_pendencia_corp_raw.copy()
    col_corp_awb = encontrar_coluna(df_pend_corp, ["AWB", "Numero AWB", "Número AWB", "AWBNumber"])
    if col_corp_awb:
        df_pend_corp["AWB_Normalizada"] = df_pend_corp[col_corp_awb].apply(normalizar_awb)

df_avarias = pd.DataFrame()
if not df_avarias_raw.empty:
    df_avarias = df_avarias_raw.copy()
    col_avar_awb = encontrar_coluna(df_avarias, ["AWB", "Numero AWB", "Número AWB", "AWBNumber"])
    if col_avar_awb:
        df_avarias["AWB_Normalizada"] = df_avarias[col_avar_awb].apply(normalizar_awb)

df_finalizadas = pd.DataFrame()
if not df_finalizadas_raw.empty:
    df_finalizadas = df_finalizadas_raw.copy()
    col_fin_awb = encontrar_coluna(df_finalizadas, ["AWB", "Numero AWB", "Número AWB", "AWBNumber"])
    if col_fin_awb:
        df_finalizadas["AWB_Normalizada"] = df_finalizadas[col_fin_awb].apply(normalizar_awb)


# ============================================================
# CLASSIFICAÇÃO AUTOMÁTICA
# ============================================================
def classificar_status_automatico(row: pd.Series) -> str:
    awb = row.get("AWB")
    sla = row.get("SLA_dt")
    hoje = pd.Timestamp.now().normalize()
    
    if not df_finalizadas.empty and "AWB_Normalizada" in df_finalizadas.columns:
        if awb in df_finalizadas["AWB_Normalizada"].values:
            return "FINALIZADO"
    
    em_pend = False
    if not df_pend.empty and "AWB_Normalizada" in df_pend.columns:
        if awb in df_pend["AWB_Normalizada"].values:
            em_pend = True
    if not df_pend_corp.empty and "AWB_Normalizada" in df_pend_corp.columns:
        if awb in df_pend_corp["AWB_Normalizada"].values:
            em_pend = True
    
    if em_pend:
        return "CARGA NA PENDÊNCIA"
    
    if not df_avarias.empty and "AWB_Normalizada" in df_avarias.columns:
        if awb in df_avarias["AWB_Normalizada"].values:
            return "CARGA COM AVARIA"
    
    if pd.isna(sla):
        return "SEM SLA"
    
    sla_norm = sla.normalize()
    if sla_norm == hoje:
        return "CARGA NO PISO"
    elif sla_norm < hoje:
        return "CARGA ATRASADA"
    else:
        return "MONITORAR"


def calcular_criticidade(status: str) -> str:
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


df_work["Status Final"] = df_work.apply(classificar_status_automatico, axis=1)
df_work["Criticidade"] = df_work["Status Final"].apply(calcular_criticidade)
df_work["Dias em Atraso"] = (pd.Timestamp.now().normalize() - df_work["SLA_dt"].dt.normalize()).dt.days
df_work["Dias em Atraso"] = df_work["Dias em Atraso"].apply(lambda x: max(0, int(x)) if not pd.isna(x) else 0)


# ============================================================
# FILTROS
# ============================================================
with st.sidebar:
    st.header("🔎 Filtros")
    
    if "Origem" in df_work.columns:
        origens = ["Todos"] + sorted([x for x in df_work["Origem"].dropna().astype(str).unique() if x != "-"])
        origem_sel = st.selectbox("Origem", origens, index=0)
        if origem_sel != "Todos":
            df_work = df_work[df_work["Origem"].astype(str) == str(origem_sel)]
    
    if "Destino" in df_work.columns:
        destinos = ["Todos"] + sorted([x for x in df_work["Destino"].dropna().astype(str).unique() if x != "-"])
        destino_sel = st.multiselect("Destino", destinos, default=["Todos"])
        if destino_sel and "Todos" not in destino_sel:
            df_work = df_work[df_work["Destino"].astype(str).isin(destino_sel)]
    
    status_opts = ["Todos"] + sorted([x for x in df_work["Status Final"].unique() if pd.notna(x)])
    status_sel = st.multiselect("Status Final", status_opts, default=["Todos"])
    if status_sel and "Todos" not in status_sel:
        df_work = df_work[df_work["Status Final"].isin(status_sel)]
    
    crit_opts = ["Todos"] + sorted([x for x in df_work["Criticidade"].unique() if pd.notna(x)])
    crit_sel = st.multiselect("Criticidade", crit_opts, default=["Todos"])
    if crit_sel and "Todos" not in crit_sel:
        df_work = df_work[df_work["Criticidade"].isin(crit_sel)]

if df_work.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()


# ============================================================
# KPIs
# ============================================================
st.markdown('<div class="section-title">📊 Resumo Geral</div>', unsafe_allow_html=True)

total = len(df_work)
finalizadas = int((df_work["Status Final"] == "FINALIZADO").sum())
pendencias = int((df_work["Status Final"] == "CARGA NA PENDÊNCIA").sum())
avarias = int((df_work["Status Final"] == "CARGA COM AVARIA").sum())
atrasadas = int((df_work["Status Final"] == "CARGA ATRASADA").sum())
piso = int((df_work["Status Final"] == "CARGA NO PISO").sum())
alta = int((df_work["Criticidade"] == "ALTA").sum())

c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi("Total de AWBs", format_int(total), "Cargas processadas")
with c2:
    render_kpi("Finalizadas", format_int(finalizadas), f"{format_pct(finalizadas/total*100 if total else 0)}")
with c3:
    render_kpi("Críticas (ALTA)", format_int(alta), f"{format_pct(alta/total*100 if total else 0)}")
with c4:
    render_kpi("Na Pendência", format_int(pendencias), f"{format_pct(pendencias/total*100 if total else 0)}")

c5, c6, c7, c8 = st.columns(4)
with c5:
    render_kpi("Com Avaria", format_int(avarias), f"{format_pct(avarias/total*100 if total else 0)}")
with c6:
    render_kpi("Atrasadas", format_int(atrasadas), f"{format_pct(atrasadas/total*100 if total else 0)}")
with c7:
    render_kpi("No Piso", format_int(piso), f"{format_pct(piso/total*100 if total else 0)}")
with c8:
    dias_media = df_work[df_work["Dias em Atraso"] > 0]["Dias em Atraso"].mean()
    render_kpi("Dias atrasadas (média)", format_float(dias_media), "Cargas fora SLA")


# ============================================================
# ABAS
# ============================================================
tab_resumo, tab_criticas, tab_pendencias, tab_avarias, tab_finalizadas, tab_exportacao = st.tabs([
    "📊 Resumo Visual",
    "🚨 Cargas Críticas",
    "⏳ Pendências",
    "⚠️ Avarias",
    "✅ Finalizadas",
    "📥 Exportação"
])


# ============================================================
# ABA RESUMO
# ============================================================
with tab_resumo:
    st.markdown('<div class="section-title">Distribuição por Status</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        status_dist = df_work["Status Final"].value_counts().reset_index()
        status_dist.columns = ["Status", "Quantidade"]
        status_dist["Quantidade"] = status_dist["Quantidade"].astype(int)
        if not status_dist.empty:
            fig = px.pie(status_dist, values="Quantidade", names="Status", hole=0.55, 
                         title="Distribuição de Status")
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=55, b=20))
            st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        crit_dist = df_work["Criticidade"].value_counts().reset_index()
        crit_dist.columns = ["Criticidade", "Quantidade"]
        crit_dist["Quantidade"] = crit_dist["Quantidade"].astype(int)
        if not crit_dist.empty:
            fig = px.pie(crit_dist, values="Quantidade", names="Criticidade", hole=0.55,
                         title="Distribuição de Criticidade")
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=55, b=20))
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('<div class="section-title">Distribuição por Faixa de Dias em Atraso</div>', unsafe_allow_html=True)
    
    df_atraso = df_work[df_work["Dias em Atraso"] > 0].copy()
    if not df_atraso.empty:
        def categorizar_dias(dias):
            if dias <= 1:
                return "0-1 dia"
            elif dias <= 3:
                return "2-3 dias"
            elif dias <= 7:
                return "4-7 dias"
            elif dias <= 30:
                return "8-30 dias"
            else:
                return ">30 dias"
        
        df_atraso["Categoria"] = df_atraso["Dias em Atraso"].apply(categorizar_dias)
        dias_atraso = df_atraso.groupby("Categoria").size().reset_index(name="Quantidade")
        dias_atraso["Quantidade"] = dias_atraso["Quantidade"].astype(int)
        
        ordem = ["0-1 dia", "2-3 dias", "4-7 dias", "8-30 dias", ">30 dias"]
        dias_atraso["Categoria"] = pd.Categorical(dias_atraso["Categoria"], categories=ordem, ordered=True)
        dias_atraso = dias_atraso.sort_values("Categoria")
        
        fig = px.bar(dias_atraso, x="Categoria", y="Quantidade", 
                    title="Distribuição de Dias em Atraso")
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=55, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma carga em atraso para exibir.")


# ============================================================
# ABA CRÍTICAS
# ============================================================
with tab_criticas:
    st.markdown('<div class="section-title">🚨 Cargas Críticas (Prioridade ALTA)</div>', unsafe_allow_html=True)
    
    df_criticas = df_work[df_work["Criticidade"] == "ALTA"].copy()
    
    st.markdown(
        f"""
        <div class="alert-card">
            <b>{format_int(len(df_criticas))}</b> cargas com criticidade ALTA encontradas.
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    colunas_vis = ["AWB", "Status Final", "Criticidade", "Dias em Atraso", "Status Sistema"]
    if "Origem" in df_criticas.columns:
        colunas_vis.insert(2, "Origem")
    if "Destino" in df_criticas.columns:
        colunas_vis.insert(3, "Destino")
    
    colunas_vis = [c for c in colunas_vis if c in df_criticas.columns]
    
    if not df_criticas.empty:
        st.dataframe(
            df_criticas[colunas_vis].sort_values("Dias em Atraso", ascending=False),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# ABA PENDÊNCIAS
# ============================================================
with tab_pendencias:
    st.markdown('<div class="section-title">⏳ Cargas na Pendência</div>', unsafe_allow_html=True)
    
    df_pend_vis = df_work[df_work["Status Final"] == "CARGA NA PENDÊNCIA"].copy()
    
    st.markdown(
        f"""
        <div class="insight-box">
            <b>{format_int(len(df_pend_vis))}</b> cargas na pendência.
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    colunas_vis = ["AWB", "Status Final", "Criticidade", "Status Sistema"]
    if "Origem" in df_pend_vis.columns:
        colunas_vis.insert(2, "Origem")
    
    colunas_vis = [c for c in colunas_vis if c in df_pend_vis.columns]
    
    if not df_pend_vis.empty:
        st.dataframe(df_pend_vis[colunas_vis], use_container_width=True, hide_index=True)


# ============================================================
# ABA AVARIAS
# ============================================================
with tab_avarias:
    st.markdown('<div class="section-title">⚠️ Cargas com Avaria</div>', unsafe_allow_html=True)
    
    df_avar_vis = df_work[df_work["Status Final"] == "CARGA COM AVARIA"].copy()
    
    st.markdown(
        f"""
        <div class="alert-card">
            <b>{format_int(len(df_avar_vis))}</b> cargas com avaria registrada.
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    colunas_vis = ["AWB", "Status Final", "Criticidade", "Status Sistema"]
    if "Origem" in df_avar_vis.columns:
        colunas_vis.insert(2, "Origem")
    
    colunas_vis = [c for c in colunas_vis if c in df_avar_vis.columns]
    
    if not df_avar_vis.empty:
        st.dataframe(df_avar_vis[colunas_vis], use_container_width=True, hide_index=True)


# ============================================================
# ABA FINALIZADAS
# ============================================================
with tab_finalizadas:
    st.markdown('<div class="section-title">✅ Cargas Finalizadas</div>', unsafe_allow_html=True)
    
    df_fin_vis = df_work[df_work["Status Final"] == "FINALIZADO"].copy()
    
    st.markdown(
        f"""
        <div class="insight-box">
            <b>{format_int(len(df_fin_vis))}</b> cargas já finalizadas.
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    colunas_vis = ["AWB", "Status Final", "Status Sistema"]
    if "Origem" in df_fin_vis.columns:
        colunas_vis.insert(2, "Origem")
    
    colunas_vis = [c for c in colunas_vis if c in df_fin_vis.columns]
    
    if not df_fin_vis.empty:
        st.dataframe(df_fin_vis[colunas_vis], use_container_width=True, hide_index=True)


# ============================================================
# ABA EXPORTAÇÃO
# ============================================================
with tab_exportacao:
    st.markdown('<div class="section-title">📥 Base Completa & Exportações</div>', unsafe_allow_html=True)
    
    colunas_export = ["AWB", "Status Final", "Criticidade", "Dias em Atraso", "Status Sistema"]
    if "Origem" in df_work.columns:
        colunas_export.insert(2, "Origem")
    
    colunas_export = [c for c in colunas_export if c in df_work.columns]
    
    st.dataframe(df_work[colunas_export], use_container_width=True, hide_index=True)
    
    abas_export = {
        "Base Filtrada": df_work[colunas_export],
        "Críticas": df_work[df_work["Criticidade"] == "ALTA"][colunas_export],
        "Pendências": df_work[df_work["Status Final"] == "CARGA NA PENDÊNCIA"][colunas_export],
        "Avarias": df_work[df_work["Status Final"] == "CARGA COM AVARIA"][colunas_export],
        "Finalizadas": df_work[df_work["Status Final"] == "FINALIZADO"][colunas_export],
    }
    
    excel_bytes = gerar_excel_multi(abas_export)
    st.download_button(
        label="📥 Baixar relatório completo em Excel",
        data=excel_bytes,
        file_name="relatorio_controle_cargas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    
    csv_bytes = df_work[colunas_export].to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        label="📥 Baixar base filtrada em CSV",
        data=csv_bytes,
        file_name="base_controle_cargas.csv",
        mime="text/csv",
    )


st.caption("Dashboard de Controle de Cargas — Análise integrada com classificação automática de status, criticidade e exportação de relatórios.")
