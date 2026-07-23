import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURAÇÃO E CONEXÃO GOOGLE SHEETS
# ==========================================

st.set_page_config(page_title="Dashboard Finanças Pessoais", layout="wide")

# Inicializa conexão com a Planilha do Google
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    """Lê os dados salvos na aba 'Lançamentos' do Google Sheets."""
    try:
        # Lê os dados da aba Lançamentos com cache desativado (ttl=0) para sempre pegar a versão atualizada
        df_sheet = conn.read(worksheet="Lançamentos", ttl=0)
        
        # Garante que as colunas corretas existam
        colunas_esperadas = ["Data", "Tipo", "Categoria", "Descrição", "Valor", "Status"]
        if df_sheet.empty or not all(col in df_sheet.columns for col in colunas_esperadas):
            return pd.DataFrame(columns=colunas_esperadas)
            
        return df_sheet.dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Descrição", "Valor", "Status"])

def salvar_dados(df_para_salvar):
    """Atualiza a aba 'Lançamentos' na Planilha do Google."""
    # Trata dados de data e numéricos antes de salvar
    df_salvar = df_para_salvar.copy()
    df_salvar = df_salvar[["Data", "Tipo", "Categoria", "Descrição", "Valor", "Status"]]
    
    # Grava na planilha
    conn.update(worksheet="Lançamentos", data=df_salvar)

# Carregamento Inicial
if "df_lancamentos" not in st.session_state:
    st.session_state.df_lancamentos = carregar_dados()

# Lista Fixa de Categorias Base
if "categorias_receita" not in st.session_state:
    st.session_state.categorias_receita = ["Salário", "Freelancer", "Investimentos", "Outras Receitas"]

if "categorias_despesa" not in st.session_state:
    st.session_state.categorias_despesa = ["Recreação", "Elétrica", "Moradia", "Saúde", "Transporte", "Alimentação", "Outras Despesas"]

# ==========================================
# 2. ESTILIZAÇÃO CSS CUSTOMIZADA (NEON DARK)
# ==========================================

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #13151C; border-right: 1px solid #232733; }
    div[data-testid="stMetric"] { background-color: #1A1C24; padding: 15px; border-radius: 12px; border: 1px solid #2A2E3D; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    h1, h2, h3, h4 { color: #FFFFFF !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background: linear-gradient(90deg, #6C5CE7 0%, #A29BFE 100%); color: white; border: none; border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { box-shadow: 0 0 12px #6C5CE7; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. PROCESSAMENTO DE DATAS E FILTROS
# ==========================================

df = st.session_state.df_lancamentos.copy()

if not df.empty and "Data" in df.columns:
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
    df["Data_dt"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Ano"] = df["Data_dt"].dt.year
    df["Mes_Num"] = df["Data_dt"].dt.month
else:
    df = pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Descrição", "Valor", "Status", "Data_dt", "Ano", "Mes_Num"])

meses_nome = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

if not df.empty and "Mes_Num" in df.columns:
    df["Mes_Nome"] = df["Mes_Num"].map(meses_nome)
else:
    df["Mes_Nome"] = pd.Series(dtype='object')

# --- SIDEBAR (MENU LATERAL) ---
st.sidebar.markdown("### 📊 Dashboard\n**Finanças Pessoais**")
st.sidebar.divider()

ano_atual = date.today().year
anos_cadastrados = df["Ano"].dropna().unique().astype(int).tolist() if not df.empty else []
if ano_atual not in anos_cadastrados:
    anos_cadastrados.append(ano_atual)

anos_disponiveis = sorted(anos_cadastrados, reverse=True)
ano_sel = st.sidebar.selectbox("Ano", anos_disponiveis)

meses_disponiveis = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
mes_atual_idx = date.today().month - 1
mes_sel = st.sidebar.selectbox("Mês", meses_disponiveis, index=mes_atual_idx)

mes_num_sel = [k for k, v in meses_nome.items() if v == mes_sel][0]

# ==========================================
# 4. DIÁLOGOS E POPUPS DE AÇÃO
# ==========================================

# Popup 1: Novo Lançamento
@st.dialog("➕ Novo Lançamento")
def novo_lancamento():
    tipo = st.radio("Tipo de Registro", ["Receita", "Despesa"], horizontal=True)
    opcoes_cat = st.session_state.categorias_receita if tipo == "Receita" else st.session_state.categorias_despesa
    
    with st.form("form_lancamento", clear_on_submit=True):
        data_input = st.date_input("Data", date.today())
        categoria = st.selectbox("Categoria", options=opcoes_cat)
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        status = st.selectbox("Status", ["Recebido", "Pendente"] if tipo == "Receita" else ["Pago", "Pendente"])
        
        if st.form_submit_button("Salvar Lançamento", type="primary"):
            novo = {
                "Data": str(data_input), 
                "Tipo": tipo, 
                "Categoria": categoria, 
                "Descrição": descricao, 
                "Valor": float(valor), 
                "Status": status
            }
            st.session_state.df_lancamentos = pd.concat(
                [st.session_state.df_lancamentos, pd.DataFrame([novo])], 
                ignore_index=True
            )
            salvar_dados(st.session_state.df_lancamentos)  # Envia para o Google Sheets
            st.success("Salvo com sucesso na nuvem!")
            st.rerun()

# Popup 2: Gerenciar Categorias
@st.dialog("⚙️ Gerenciar Categorias")
def gerenciar_categorias():
    tipo_gerenciar = st.radio("Selecione o Tipo de Categoria:", ["Receita", "Despesa"], horizontal=True)
    lista_atual = st.session_state.categorias_receita if tipo_gerenciar == "Receita" else st.session_state.categorias_despesa

    st.markdown(f"##### Categorias de {tipo_gerenciar}:")
    for cat in lista_atual:
        st.write(f"• {cat}")
        
    st.divider()
    nova_cat = st.text_input(f"Nova Categoria para {tipo_gerenciar}:")
    if st.button("➕ Adicionar Categoria", use_container_width=True):
        if nova_cat.strip() and nova_cat.strip() not in lista_atual:
            lista_atual.append(nova_cat.strip())
            st.success(f"Categoria '{nova_cat.strip()}' adicionada em {tipo_gerenciar}!")
            st.rerun()

st.sidebar.divider()
if st.sidebar.button("➕ Novo Lançamento", use_container_width=True):
    novo_lancamento()

if st.sidebar.button("⚙️ Gerenciar Categorias", use_container_width=True):
    gerenciar_categorias()

# ==========================================
# 5. FILTRAGEM DE DADOS
# ==========================================

if not df.empty and "Ano" in df.columns:
    df_ano = df[df["Ano"] == ano_sel]
    df_mes = df_ano[df_ano["Mes_Num"] == mes_num_sel]
else:
    df_ano = pd.DataFrame(columns=df.columns)
    df_mes = pd.DataFrame(columns=df.columns)

cores_pie = ["#6C5CE7", "#00CEC9", "#FD79A8", "#00B894", "#FDCB6E", "#E17055"]

# ==========================================
# 6. LAYOUT PRINCIPAL
# ==========================================

col_left, col_right = st.columns([1.8, 1])

# --- COLUNA DA ESQUERDA ---
with col_left:
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    rec_recebidas = df_mes[(df_mes["Tipo"] == "Receita") & (df_mes["Status"] == "Recebido")]["Valor"].sum() if not df_mes.empty else 0.0
    rec_pendentes = df_mes[(df_mes["Tipo"] == "Receita") & (df_mes["Status"] == "Pendente")]["Valor"].sum() if not df_mes.empty else 0.0
    
    desp_pagas = df_mes[(df_mes["Tipo"] == "Despesa") & (df_mes["Status"] == "Pago")]["Valor"].sum() if not df_mes.empty else 0.0
    desp_pendentes = df_mes[(df_mes["Tipo"] == "Despesa") & (df_mes["Status"] == "Pendente")]["Valor"].sum() if not df_mes.empty else 0.0
    
    saldo_atual = rec_recebidas - desp_pagas
    
    with kpi1:
        st.markdown(f"**Saldo ({mes_sel})**\n<h4 style='color: #00CEC9;'>R$ {saldo_atual:,.2f}</h4>", unsafe_allow_html=True)
        fig_spark1 = go.Figure(go.Scatter(y=[0, 0, 0, saldo_atual], mode='lines', fill='tozeroy', line=dict(color='#00CEC9', width=2)))
        fig_spark1.update_layout(height=45, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig_spark1, use_container_width=True, config={'displayModeBar': False}, key="spark_saldo")
        
    with kpi2:
        st.markdown(f"**Despesas Pagas**\n<h4 style='color: #FD79A8;'>R$ {desp_pagas:,.2f}</h4>", unsafe_allow_html=True)
        fig_spark2 = go.Figure(go.Scatter(y=[0, 0, 0, desp_pagas], mode='lines', fill='tozeroy', line=dict(color='#FD79A8', width=2)))
        fig_spark2.update_layout(height=45, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig_spark2, use_container_width=True, config={'displayModeBar': False}, key="spark_desp")

    with kpi3:
        st.markdown(f"**Receitas Pendentes**\n<h4 style='color: #FDCB6E;'>R$ {rec_pendentes:,.2f}</h4>", unsafe_allow_html=True)
        fig_spark3 = go.Figure(go.Scatter(y=[0, 0, 0, rec_pendentes], mode='lines', fill='tozeroy', line=dict(color='#FDCB6E', width=2)))
        fig_spark3.update_layout(height=45, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig_spark3, use_container_width=True, config={'displayModeBar': False}, key="spark_rec_pend")

    with kpi4:
        st.markdown(f"**Despesas Pendentes**\n<h4 style='color: #E17055;'>R$ {desp_pendentes:,.2f}</h4>", unsafe_allow_html=True)
        fig_spark4 = go.Figure(go.Scatter(y=[0, 0, 0, desp_pendentes], mode='lines', fill='tozeroy', line=dict(color='#E17055', width=2)))
        fig_spark4.update_layout(height=45, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig_spark4, use_container_width=True, config={'displayModeBar': False}, key="spark_desp_pend")

    st.markdown(f"### Análise Mensal ({ano_sel})")
    if not df_ano.empty and "Mes_Num" in df_ano.columns and len(df_ano) > 0:
        df_agrup_mes = df_ano.groupby(["Mes_Num", "Tipo"])["Valor"].sum().reset_index()
        df_agrup_mes["Mes_Abrev"] = df_agrup_mes["Mes_Num"].apply(lambda x: list(meses_nome.values())[int(x)-1][:3].lower())
    else:
        df_agrup_mes = pd.DataFrame({"Mes_Abrev": ["jan"], "Valor": [0], "Tipo": ["Sem dados"]})

    fig_barras = px.bar(
        df_agrup_mes, x="Mes_Abrev", y="Valor", color="Tipo",
        barmode="group", color_discrete_map={"Receita": "#6C5CE7", "Despesa": "#FD79A8"},
        labels={"Mes_Abrev": "", "Valor": ""}
    )
    fig_barras.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8A8D9B'), height=280, margin=dict(l=10,r=10,t=10,b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_barras, use_container_width=True, key="barras_mensal")

# --- COLUNA DA DIREITA ---
with col_right:
    pie1, pie2 = st.columns(2)
    
    with pie1:
        st.markdown(f"**Despesas em {mes_sel}**")
        df_desp_m = df_mes[df_mes["Tipo"] == "Despesa"] if not df_mes.empty else pd.DataFrame()
        if not df_desp_m.empty and df_desp_m["Valor"].sum() > 0:
            fig_d1 = px.pie(df_desp_m, names="Categoria", values="Valor", hole=0.6, color_discrete_sequence=cores_pie)
        else:
            fig_d1 = px.pie(names=["Sem Dados"], values=[1], hole=0.6, color_discrete_sequence=["#232733"])
            
        fig_d1.update_layout(showlegend=False, height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)')
        fig_d1.update_traces(textinfo='percent' if not df_desp_m.empty and df_desp_m["Valor"].sum() > 0 else 'none', textfont=dict(size=11))
        st.plotly_chart(fig_d1, use_container_width=True, key="chart_donut_mes")

    with pie2:
        st.markdown(f"**Despesas em {ano_sel}**")
        df_desp_a = df_ano[df_ano["Tipo"] == "Despesa"] if not df_ano.empty else pd.DataFrame()
        if not df_desp_a.empty and df_desp_a["Valor"].sum() > 0:
            fig_d2 = px.pie(df_desp_a, names="Categoria", values="Valor", hole=0.6, color_discrete_sequence=cores_pie)
        else:
            fig_d2 = px.pie(names=["Sem Dados"], values=[1], hole=0.6, color_discrete_sequence=["#232733"])
            
        fig_d2.update_layout(showlegend=False, height=180, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)')
        fig_d2.update_traces(textinfo='percent' if not df_desp_a.empty and df_desp_a["Valor"].sum() > 0 else 'none', textfont=dict(size=11))
        st.plotly_chart(fig_d2, use_container_width=True, key="chart_donut_ano")

    st.markdown("**Participação na base anual**")
    cat_cols = st.columns(6)
    
    if not df_desp_a.empty and df_desp_a["Valor"].sum() > 0:
        cats = df_desp_a.groupby("Categoria")["Valor"].sum()
        total_a = cats.sum() if cats.sum() > 0 else 1
        
        for i, (cat_name, cat_val) in enumerate(cats.items()):
            pct = (cat_val / total_a) * 100
            with cat_cols[i % 6]:
                fig_mini = go.Figure(go.Pie(
                    values=[pct, 100-pct], hole=0.75,
                    marker=dict(colors=[cores_pie[i % len(cores_pie)], '#232733']),
                    textinfo='none'
                ))
                fig_mini.update_layout(
                    showlegend=False, height=70, width=70,
                    margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)',
                    annotations=[dict(text=f"{int(pct)}%", x=0.5, y=0.5, font_size=10, showarrow=False, font_color="white")]
                )
                st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False}, key=f"mini_donut_{i}")
                st.caption(f"<p style='text-align: center; font-size: 10px; color: #8A8D9B;'>{cat_name}</p>", unsafe_allow_html=True)
    else:
        st.info("Sem lançamentos para exibir participação.")

st.divider()

# ==========================================
# 7. TABELA EDITÁVEL E SINCRONIZADA
# ==========================================

st.markdown(f"### Detalhamento dos Lançamentos de {mes_sel}/{ano_sel} (Editável)")

df_exibicao = df_mes.drop(columns=["Data_dt", "Ano", "Mes_Num", "Mes_Nome"], errors="ignore")
todas_categorias = list(set(st.session_state.categorias_receita + st.session_state.categorias_despesa))

df_editado = st.data_editor(
    df_exibicao,
    column_config={
        "Categoria": st.column_config.SelectboxColumn("Categoria", options=todas_categorias, required=True),
        "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Receita", "Despesa"], required=True),
        "Status": st.column_config.SelectboxColumn("Status", options=["Recebido", "Pago", "Pendente"], required=True)
    },
    num_rows="dynamic",
    use_container_width=True,
    key="editor_dark"
)

# Sincroniza e envia alterações para o Google Sheets
if not df_editado.equals(df_exibicao):
    if not st.session_state.df_lancamentos.empty:
        st.session_state.df_lancamentos["Data_temp"] = pd.to_datetime(st.session_state.df_lancamentos["Data"], errors="coerce")
        df_outros_meses = st.session_state.df_lancamentos[
            (st.session_state.df_lancamentos["Data_temp"].dt.month != mes_num_sel) | 
            (st.session_state.df_lancamentos["Data_temp"].dt.year != ano_sel)
        ].drop(columns=["Data_temp"], errors="ignore")
        
        st.session_state.df_lancamentos = pd.concat([df_outros_meses, df_editado], ignore_index=True)
    else:
        st.session_state.df_lancamentos = df_editado.copy()
        
    salvar_dados(st.session_state.df_lancamentos)  # Atualiza a planilha
    st.rerun()
