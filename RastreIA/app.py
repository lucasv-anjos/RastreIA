import re
from collections import Counter
from datetime import datetime

import pandas as pd
import streamlit as st
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(
    page_title="RastreIA | Inteligência Investigativa",
    page_icon="🔎",
    layout="wide",
)

# Protótipo demonstrativo: todos os dados abaixo são fictícios.
STOPWORDS = {
    "a", "o", "as", "os", "de", "do", "da", "dos", "das", "e", "em", "no",
    "na", "nos", "nas", "um", "uma", "para", "por", "com", "que", "foi",
    "ao", "aos", "se", "sua", "seu", "sobre", "durante", "após", "antes",
    "entre", "às", "era", "ter", "tem", "mais", "mas", "não", "relata",
    "informou", "disse", "segundo", "local", "caso", "registro"
}

SAMPLE_RECORDS = [
    {
        "id": "DOC-001", "tipo": "Documento", "data": "2026-09-12",
        "titulo": "Relatório de vistoria do galpão",
        "local": "Galpão Norte",
        "pessoas": "Marina Costa; Paulo Nunes",
        "termos": "galpão norte caminhão azul portão lateral câmera desligada",
        "resumo": "Relatório fictício registra um caminhão azul próximo ao portão lateral. A câmera do acesso estava desligada.",
        "fonte": "Equipe de perícia (simulada)", "confianca": "A confirmar"
    },
    {
        "id": "DEP-002", "tipo": "Depoimento", "data": "2026-09-13",
        "titulo": "Depoimento de testemunha A",
        "local": "Rua das Oficinas",
        "pessoas": "Marina Costa",
        "termos": "rua oficinas caminhão azul 21h portão lateral chuva",
        "resumo": "Testemunha fictícia relata ter visto um caminhão azul por volta das 21h nas proximidades da Rua das Oficinas.",
        "fonte": "Entrevista simulada", "confianca": "Relato não corroborado"
    },
    {
        "id": "OC-003", "tipo": "Ocorrência", "data": "2026-09-12",
        "titulo": "Registro de alarme",
        "local": "Galpão Norte",
        "pessoas": "Paulo Nunes",
        "termos": "galpão norte alarme acesso lateral 20h55 sistema interrompido",
        "resumo": "Registro fictício indica interrupção do sistema de alarme às 20h55. A causa ainda não foi determinada.",
        "fonte": "Sistema de alarme (simulado)", "confianca": "Registro técnico fictício"
    },
    {
        "id": "DOC-004", "tipo": "Documento",
        "data": "2026-09-14", "titulo": "Anotação encontrada no escritório",
        "local": "Escritório Central",
        "pessoas": "Rafael Lima",
        "termos": "escritório central entrega caixa terça caminhão azul inventário",
        "resumo": "Anotação fictícia menciona uma entrega de caixas e um caminhão azul, sem indicar relação confirmada com a ocorrência.",
        "fonte": "Documento simulado", "confianca": "Contexto desconhecido"
    },
    {
        "id": "DEP-005", "tipo": "Depoimento",
        "data": "2026-09-15", "titulo": "Depoimento de testemunha B",
        "local": "Estacionamento Leste",
        "pessoas": "Rafael Lima; Marina Costa",
        "termos": "estacionamento leste caixa inventário entrega terça 21h",
        "resumo": "Testemunha fictícia relata ter visto uma caixa no estacionamento. Horário e finalidade precisam ser confirmados.",
        "fonte": "Entrevista simulada", "confianca": "Relato não corroborado"
    },
    {
        "id": "OC-006", "tipo": "Ocorrência",
        "data": "2026-09-16", "titulo": "Veículo semelhante reportado",
        "local": "Avenida Industrial",
        "pessoas": "Desconhecido",
        "termos": "avenida industrial caminhão azul placa ilegível trânsito 21h",
        "resumo": "Registro fictício menciona um caminhão azul com placa ilegível. Não há confirmação de que seja o mesmo veículo.",
        "fonte": "Registro simulado", "confianca": "Identificação pendente"
    },
]

def tokenize(text):
    words = re.findall(r"[a-záàâãéèêíïóôõöúçñ0-9]+", str(text).lower(), re.UNICODE)
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}

def similarity(a, b):
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0, []
    common = sorted(ta & tb)
    score = len(common) / len(ta | tb)
    return score, common

def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
.hero {padding: 1.25rem 1.4rem; border-radius: 16px; background: linear-gradient(120deg,#10243a,#1c4860); color: white; margin-bottom: 1rem;}
.hero h1 {margin:0; font-size:2rem;}
.hero p {margin:.45rem 0 0 0; opacity:.9;}
.small-muted {color: #6b7280; font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🔎 RastreIA — Inteligência Investigativa</h1>
  <p>Organize registros, explore conexões e transforme informações dispersas em linhas de investigação verificáveis.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Painel do caso")
    case_name = st.text_input("Nome do caso", "Operação Horizonte (simulada)")
    st.caption("Ambiente de demonstração com dados 100% fictícios.")
    st.divider()
    st.subheader("Filtros")
    type_options = ["Documento", "Depoimento", "Ocorrência"]
    selected_types = st.multiselect("Tipo de registro", type_options, default=type_options)
    query = st.text_input("Buscar por palavra, pessoa ou local", "")
    st.divider()
    st.subheader("Adicionar registro")
    submitted = False
    with st.form("add_record", clear_on_submit=True):
        new_type = st.selectbox("Tipo", type_options)
        new_title = st.text_input("Título")
        new_date = st.date_input("Data", value=datetime.today().date())
        new_location = st.text_input("Local")
        new_people = st.text_input("Pessoas mencionadas", help="Use ponto e vírgula para separar nomes.")
        new_terms = st.text_area("Palavras-chave / conteúdo")
        new_summary = st.text_area("Resumo objetivo")
        new_source = st.text_input("Fonte do registro")
        submitted = st.form_submit_button("Adicionar ao painel")
    if submitted:
        if not new_title.strip() or not new_summary.strip():
            st.error("Preencha pelo menos o título e o resumo.")
        else:
            st.session_state.setdefault("extra_records", [])
            st.session_state.extra_records.append({
                "id": f"USR-{len(st.session_state.extra_records)+1:03d}",
                "tipo": new_type, "data": str(new_date), "titulo": new_title.strip(),
                "local": new_location.strip() or "Não informado",
                "pessoas": new_people.strip() or "Não informado",
                "termos": new_terms.strip(), "resumo": new_summary.strip(),
                "fonte": new_source.strip() or "Fonte não informada",
                "confianca": "Revisão humana necessária"
            })
            st.success("Registro adicionado à sessão atual.")

records = SAMPLE_RECORDS + st.session_state.get("extra_records", [])
df = pd.DataFrame(records)
df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
filtered = df[df["tipo"].isin(selected_types)].copy()
if query.strip():
    mask = filtered.apply(
        lambda row: query.lower() in " ".join(str(row.get(c, "")) for c in
        ["id", "titulo", "local", "pessoas", "termos", "resumo", "fonte"]).lower(),
        axis=1
    )
    filtered = filtered[mask]

tab_overview, tab_records, tab_connections, tab_timeline, tab_assistant = st.tabs(
    ["📊 Visão geral", "🗂️ Registros", "🕸️ Conexões", "🕒 Linha do tempo", "✨ Assistente de análise"]
)

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros visíveis", len(filtered))
    c2.metric("Documentos", int((filtered["tipo"] == "Documento").sum()))
    c3.metric("Depoimentos", int((filtered["tipo"] == "Depoimento").sum()))
    c4.metric("Ocorrências", int((filtered["tipo"] == "Ocorrência").sum()))
    st.subheader(case_name)
    st.write("Use o painel para pesquisar e organizar evidências documentais. O sistema aponta **possíveis relações textuais**, não conclusões sobre culpa ou autoria.")
    if not filtered.empty:
        counts = filtered["tipo"].value_counts().reindex(type_options, fill_value=0)
        col_a, col_b = st.columns([1, 1.3])
        with col_a:
            st.markdown("**Registros por categoria**")
            st.bar_chart(counts)
        with col_b:
            st.markdown("**Registros recentes**")
            show = filtered.sort_values("data_dt", ascending=False)[["data", "id", "tipo", "titulo", "local"]]
            st.dataframe(show, use_container_width=True, hide_index=True)
    st.info("Dica para a apresentação: demonstre uma busca por “caminhão azul” e depois abra a aba Conexões para mostrar quais registros compartilham termos.")

with tab_records:
    st.subheader("Catálogo de registros")
    if filtered.empty:
        st.warning("Nenhum registro corresponde aos filtros.")
    else:
        for _, row in filtered.sort_values("data_dt", ascending=False).iterrows():
            with st.expander(f"{row['id']} · {row['tipo']} · {row['titulo']}"):
                a, b = st.columns([1, 2])
                with a:
                    st.write(f"**Data:** {row['data']}")
                    st.write(f"**Local:** {row['local']}")
                    st.write(f"**Pessoas mencionadas:** {row['pessoas']}")
                    st.write(f"**Fonte:** {row['fonte']}")
                    st.caption(f"Status: {row['confianca']}")
                with b:
                    st.write(row["resumo"])
                    st.write("**Termos / conteúdo indexado**")
                    st.write(row["termos"] or "Nenhum termo informado")
    st.download_button(
        "⬇️ Exportar registros filtrados (CSV)",
        data=filtered.drop(columns=["data_dt"], errors="ignore").to_csv(index=False).encode("utf-8-sig"),
        file_name="registros_caso.csv",
        mime="text/csv",
    )

with tab_connections:
    st.subheader("Mapa de possíveis conexões")
    st.caption("As conexões são calculadas por sobreposição de palavras-chave, locais e pessoas mencionadas. São pistas para revisão, não prova de relação causal.")
    threshold = st.slider("Exibir conexão a partir desta similaridade", 0.05, 0.80, 0.15, 0.05)
    graph_records = filtered.to_dict("records")
    G = nx.Graph()
    for row in graph_records:
        G.add_node(row["id"], label=f"{row['id']}\\n{row['titulo'][:24]}", tipo=row["tipo"])
    edges = []
    for i in range(len(graph_records)):
        for j in range(i + 1, len(graph_records)):
            a, b = graph_records[i], graph_records[j]
            text_a = f"{a['titulo']} {a['local']} {a['pessoas']} {a['termos']} {a['resumo']}"
            text_b = f"{b['titulo']} {b['local']} {b['pessoas']} {b['termos']} {b['resumo']}"
            score, common = similarity(text_a, text_b)
            # Shared exact location/person names can surface even when text similarity is low.
            shared_places = set(str(a["local"]).lower().split(";")) & set(str(b["local"]).lower().split(";"))
            shared_people = set(x.strip().lower() for x in str(a["pessoas"]).split(";")) & set(x.strip().lower() for x in str(b["pessoas"]).split(";"))
            boosted = min(1.0, score + (0.25 if shared_places and "não informado" not in shared_places else 0) +
                          (0.20 if shared_people and "não informado" not in shared_people else 0))
            if boosted >= threshold and (common or shared_places or shared_people):
                G.add_edge(a["id"], b["id"], weight=boosted, common=common[:8],
                           shared_places=list(shared_places), shared_people=list(shared_people))
                edges.append((a["id"], b["id"], boosted, common, shared_places, shared_people))
    if len(G.nodes) == 0:
        st.info("Não há registros para desenhar com os filtros atuais.")
    else:
        pos = nx.spring_layout(G, seed=8, k=1.15)
        edge_x, edge_y = [], []
        for u, v in G.edges():
            x0, y0 = pos[u]; x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
        node_x, node_y, node_text, node_color = [], [], [], []
        color_map = {"Documento": "#4f86c6", "Depoimento": "#d99a35", "Ocorrência": "#3b9b83"}
        record_map = {r["id"]: r for r in graph_records}
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x); node_y.append(y)
            r = record_map[node]
            node_text.append(f"{node} — {r['titulo']}<br>Tipo: {r['tipo']}<br>Local: {r['local']}")
            node_color.append(color_map.get(r["tipo"], "#888888"))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                                 line=dict(width=1.5, color="#9aa6b2"),
                                 hoverinfo="none"))
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text", text=list(G.nodes()),
            textposition="bottom center", hovertext=node_text, hoverinfo="text",
            marker=dict(size=22, color=node_color, line=dict(width=1, color="white"))
        ))
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(visible=False), yaxis=dict(visible=False),
                          height=500, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        if edges:
            edge_df = pd.DataFrame([
                {"Registro A": e[0], "Registro B": e[1], "Similaridade estimada": round(e[2], 2),
                 "Termos em comum": ", ".join(e[3][:8]) or "—",
                 "Locais compartilhados": ", ".join(e[4]) or "—",
                 "Pessoas compartilhadas": ", ".join(e[5]) or "—"}
                for e in sorted(edges, key=lambda x: x[2], reverse=True)
            ])
            st.dataframe(edge_df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma conexão atingiu o limite atual. Reduza o controle ou revise os termos indexados.")

with tab_timeline:
    st.subheader("Linha do tempo")
    timeline = filtered.dropna(subset=["data_dt"]).sort_values("data_dt")
    if timeline.empty:
        st.info("Não há datas válidas nos registros filtrados.")
    else:
        for _, row in timeline.iterrows():
            st.markdown(f"**{row['data']} · {row['id']} · {row['tipo']}**")
            st.write(f"{row['titulo']} — {row['resumo']}")
            st.caption(f"Local: {row['local']} | Fonte: {row['fonte']}")
            st.divider()

with tab_assistant:
    st.subheader("Assistente de análise textual")
    st.write("Escolha um registro e veja termos compartilhados com os demais. O assistente não determina autoria, intenção ou culpa.")
    if not filtered.empty:
        selected_id = st.selectbox("Registro de referência", filtered["id"].tolist())
        matched = filtered[filtered["id"] == selected_id]
        if matched.empty:
            st.warning("Registro selecionado não encontrado nos filtros atuais.")
            st.stop()
        selected = matched.iloc[0]
        base_text = f"{selected['titulo']} {selected['local']} {selected['pessoas']} {selected['termos']} {selected['resumo']}"
        suggestions = []
        for _, other in filtered[filtered["id"] != selected_id].iterrows():
            other_text = f"{other['titulo']} {other['local']} {other['pessoas']} {other['termos']} {other['resumo']}"
            score, common = similarity(base_text, other_text)
            if common:
                suggestions.append({
                    "ID": other["id"], "Tipo": other["tipo"], "Título": other["titulo"],
                    "Similaridade textual": round(score, 2),
                    "Termos compartilhados": ", ".join(common[:10]),
                    "Pergunta para o investigador": (
                        f"É possível confirmar independentemente a ocorrência de {', '.join(common[:3])}?"
                    )
                })
        suggestions.sort(key=lambda x: x["Similaridade textual"], reverse=True)
        st.markdown("**Perguntas úteis para validação**")
        st.markdown("- Os horários usam o mesmo fuso e relógio sincronizado?")
        st.markdown("- A informação vem de fonte independente ou foi repetida de outro relato?")
        st.markdown("- Há explicações alternativas para o termo, local ou objeto compartilhado?")
        st.markdown("- Que informação está faltando para confirmar ou descartar a conexão?")
        if suggestions:
            st.dataframe(pd.DataFrame(suggestions), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum termo relevante em comum foi encontrado nos registros visíveis.")
    else:
        st.info("Adicione ou filtre registros para começar.")

st.divider()
st.caption(
    "⚠️ Protótipo para hackathon. Não use dados pessoais ou informações reais de investigação nesta demonstração. "
    "Similaridade textual não comprova vínculo entre pessoas ou eventos. Qualquer hipótese deve ser revisada por "
    "profissional autorizado, com verificação das fontes, registro de incertezas e respeito à legislação aplicável."
)
