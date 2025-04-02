import streamlit as st
from pymongo import MongoClient
from haversine import haversine
import certifi

# Configuração do MongoDB
def get_db_connection():
    CONNECTION_STRING = "mongodb+srv://pvitor66:fthCckusnQWvwiPz@estabelecimentos.y9eps6w.mongodb.net/?retryWrites=true&w=majority&appName=Estabelecimentos"
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client['Cadastros']
    return db['Estabelecimentos']

collection = get_db_connection()

# Função para calcular distância entre coordenadas
def calcular_distancia(lat1, lon1, lat2, lon2):
    return haversine((lat1, lon1), (lat2, lon2))

# Função para verificar distância mínima
def verificar_distancia_minima(lat, lon, min_dist_km=2):
    estabelecimentos = list(collection.find({}, {'_id': 0, 'latitude': 1, 'longitude': 1}))
    
    for estab in estabelecimentos:
        distancia = calcular_distancia(lat, lon, estab['latitude'], estab['longitude'])
        if distancia < min_dist_km:
            return False, distancia
    return True, None

# Funções para os relatórios geográficos
def relatorio_estabelecimentos_raio_10km():
    estabelecimentos = list(collection.find({}, {'_id': 0, 'nome': 1, 'latitude': 1, 'longitude': 1}))
    resultados = []
    
    for estab in estabelecimentos:
        count = 0
        for outro_estab in estabelecimentos:
            if estab['nome'] != outro_estab['nome']:
                distancia = calcular_distancia(estab['latitude'], estab['longitude'],
                                            outro_estab['latitude'], outro_estab['longitude'])
                if distancia <= 10:
                    count += 1
        resultados.append({
            'Estabelecimento': estab['nome'],
            'Estabelecimentos em 10km': count
        })
    
    return resultados

def relatorio_estabelecimentos_5km_por_nome(nome_estabelecimento):
    estabelecimento_ref = collection.find_one({'nome': nome_estabelecimento}, 
                                            {'_id': 0, 'latitude': 1, 'longitude': 1})
    if not estabelecimento_ref:
        return None
    
    estabelecimentos = list(collection.find({}, {'_id': 0, 'nome': 1, 'latitude': 1, 'longitude': 1}))
    resultados = []
    
    for estab in estabelecimentos:
        if estab['nome'] != nome_estabelecimento:
            distancia = calcular_distancia(estabelecimento_ref['latitude'], estabelecimento_ref['longitude'],
                                         estab['latitude'], estab['longitude'])
            if distancia <= 5:
                resultados.append({
                    'Estabelecimento': estab['nome'],
                    'Distância (km)': round(distancia, 2)
                })
    
    return resultados

def relatorio_estabelecimento_mais_proximo(lat, lon):
    estabelecimentos = list(collection.find({}, {'_id': 0, 'nome': 1, 'latitude': 1, 'longitude': 1}))
    if not estabelecimentos:
        return None
    
    mais_proximo = None
    menor_distancia = float('inf')
    
    for estab in estabelecimentos:
        distancia = calcular_distancia(lat, lon, estab['latitude'], estab['longitude'])
        if distancia < menor_distancia:
            menor_distancia = distancia
            mais_proximo = estab['nome']
    
    return {
        'Estabelecimento mais próximo': mais_proximo,
        'Distância (km)': round(menor_distancia, 2)
    }

# Interface Streamlit
st.title("Sistema de Cadastro de Estabelecimentos")

# Abas para organização
tab1, tab2 = st.tabs(["Cadastro", "Relatórios Geográficos"])

with tab1:
    # Formulário de cadastro
    with st.form("cadastro_form"):
        nome = st.text_input("Nome do Estabelecimento")
        lat = st.number_input("Latitude", format="%.6f")
        lon = st.number_input("Longitude", format="%.6f")
        
        submitted = st.form_submit_button("Cadastrar")
        
        if submitted:
            if not nome:
                st.error("Por favor, insira um nome para o estabelecimento")
            else:
                valido, distancia = verificar_distancia_minima(lat, lon)
                
                if valido:
                    estabelecimento = {
                        'nome': nome,
                        'latitude': lat,
                        'longitude': lon
                    }
                    collection.insert_one(estabelecimento)
                    st.success("Estabelecimento cadastrado com sucesso na coleção 'Estabelecimentos'!")
                else:
                    st.error(f"Não é possível cadastrar. Existe um estabelecimento a {distancia:.2f} km de distância (mínimo 2 km requerido).")

with tab2:
    st.header("Relatórios Geográficos")
    
    # Relatório 1: Estabelecimentos em raio de 10km
    st.subheader("1. Quantidade de estabelecimentos em 10km de cada")
    if st.button("Gerar Relatório de 10km"):
        resultado = relatorio_estabelecimentos_raio_10km()
        if resultado:
            st.table(resultado)
        else:
            st.warning("Nenhum estabelecimento cadastrado para gerar o relatório.")
    
    # Relatório 2: Estabelecimentos em 5km de um específico
    st.subheader("2. Estabelecimentos em 5km de um determinado")
    nome_consulta = st.selectbox(
        "Selecione o estabelecimento de referência",
        [e['nome'] for e in collection.find({}, {'_id': 0, 'nome': 1})] if collection.count_documents({}) > 0 else [],
        index=0
    )
    if st.button("Gerar Relatório de 5km"):
        if nome_consulta:
            resultado = relatorio_estabelecimentos_5km_por_nome(nome_consulta)
            if resultado is not None:
                if resultado:
                    st.table(resultado)
                else:
                    st.info(f"Não há estabelecimentos num raio de 5km de {nome_consulta}.")
            else:
                st.error("Estabelecimento não encontrado.")
        else:
            st.warning("Selecione um estabelecimento para consulta.")
    
    # Relatório 3: Estabelecimento mais próximo de um ponto
    st.subheader("3. Estabelecimento mais próximo de um ponto")
    col1, col2 = st.columns(2)
    with col1:
        lat_consulta = st.number_input("Latitude do ponto", format="%.6f", key="lat_consulta")
    with col2:
        lon_consulta = st.number_input("Longitude do ponto", format="%.6f", key="lon_consulta")
    
    if st.button("Encontrar mais próximo"):
        resultado = relatorio_estabelecimento_mais_proximo(lat_consulta, lon_consulta)
        if resultado:
            st.success(f"Estabelecimento mais próximo: {resultado['Estabelecimento mais próximo']} ({resultado['Distância (km)']} km)")
        else:
            st.warning("Nenhum estabelecimento cadastrado para consulta.")