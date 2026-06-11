import os
import pandas as pd
import numpy as np
import networkx as nx
import folium


# ------------------------------------------------------------------ #
# Criação do grafo
# ------------------------------------------------------------------ #

def criar_grafo(geograf, internacoes):
    G = nx.DiGraph()

    for _, row in internacoes.iterrows():
        municipio = row["MUNICIPIO"]
        hospital  = row["HOSPITAL"]

        if not G.has_node(municipio):
            dados = geograf[geograf["Nome"] == municipio]
            if not dados.empty:
                G.add_node(municipio, bipartite=0,
                           latitude=dados["Latitude"].values[0],
                           longitude=dados["Longitude"].values[0])
            else:
                print(f"[AVISO] Coordenadas não encontradas: {municipio}")

        if not G.has_node(hospital):
            dados = geograf[geograf["Nome"] == hospital]
            if not dados.empty:
                G.add_node(hospital, bipartite=1,
                           latitude=dados["Latitude"].values[0],
                           longitude=dados["Longitude"].values[0])
            else:
                print(f"[AVISO] Coordenadas não encontradas: {hospital}")

        if G.has_node(municipio) and G.has_node(hospital):
            if G.has_edge(municipio, hospital):
                G[municipio][hospital]["weight"] += 1
            else:
                G.add_edge(municipio, hospital, weight=1)

    return G


def criar_grafo_por_tipo(geograf, internacoes, tipo):

    df_filtrado = internacoes[internacoes["TIPO_PROC"] == tipo]
    return criar_grafo(geograf, df_filtrado)


# ------------------------------------------------------------------ #
# Estatísticas
# ------------------------------------------------------------------ #

def estatisticas_grafo(G, titulo="Grafo"):

    municipios = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 0]
    hospitais  = [n for n, d in G.nodes(data=True) if d.get("bipartite") == 1]
    graus      = [grau for _, grau in G.degree()]

    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print(f"{'='*50}")
    print(f"  Nós (total):      {G.number_of_nodes()}")
    print(f"  Municípios:       {len(municipios)}")
    print(f"  Hospitais:        {len(hospitais)}")
    print(f"  Arestas:          {G.number_of_edges()}")
    print(f"  Grau médio:       {np.mean(graus):.4f}")
    print(f"  Densidade:        {nx.density(G):.6f}")
    print(f"  Comp. fracas:     {nx.number_weakly_connected_components(G)}")
    print(f"  Comp. fortes:     {nx.number_strongly_connected_components(G)}")
    print(f"{'='*50}\n")


def plotar_grafo_folium(G, output_path="output/grafo.html", sobrecarregados=None):

    sobrecarregados = sobrecarregados or []

    latitudes  = [d["latitude"]  for _, d in G.nodes(data=True)]
    longitudes = [d["longitude"] for _, d in G.nodes(data=True)]

    m = folium.Map(
        location=[np.mean(latitudes), np.mean(longitudes)],
        zoom_start=7
    )

    # Arestas
    for u, v, data in G.edges(data=True):
        folium.PolyLine(
            locations=[
                [G.nodes[u]["latitude"], G.nodes[u]["longitude"]],
                [G.nodes[v]["latitude"], G.nodes[v]["longitude"]]
            ],
            color="gray",
            weight=1.5,
            opacity=0.5,
            tooltip=f"Internações: {data['weight']}"
        ).add_to(m)

    # Nós
    for node, data in G.nodes(data=True):
        if data.get("bipartite") == 0:
            color = "blue"
        elif node in sobrecarregados:
            color = "orange"
        else:
            color = "red"

        folium.CircleMarker(
            location=[data["latitude"], data["longitude"]],
            radius=5,
            popup=node,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8
        ).add_to(m)

    m.fit_bounds([[-7.5, -41.5], [-2.5, -37.0]])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    m.save(output_path)
    print(f"Mapa salvo em: {output_path}")
    return m

def criar_grafo_reestruturado(df):

    G = nx.DiGraph()

    for _, row in df.iterrows():

        municipio = row['MUNICIPIO']
        hospital = row['HOSPITAL_CANDIDATO']

        G.add_node(
            municipio,
            bipartite=0,
            latitude=row['LAT_MUNICIPIO'],
            longitude=row['LON_MUNICIPIO']
        )

        G.add_node(
            hospital,
            bipartite=1,
            latitude=row['LAT_HOSPITAL_CANDIDATO'],
            longitude=row['LON_HOSPITAL_CANDIDATO']
        )

        G.add_edge(
            municipio,
            hospital,
            weight=row['INTERNACOES_PARA_SOBRECARREGADO']
        )

    return G