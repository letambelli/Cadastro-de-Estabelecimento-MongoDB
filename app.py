import streamlit as st
from pymongo import MongoClient
from haversine import haversine
import certifi

# Configuração do MongoDB - agora usando a database "Cadastros" e coleção "Estabelecimentos"
def get_db_connection():
    CONNECTION_STRING = "mongodb+srv://pvitor66:fthCckusnQWvwiPz@estabelecimentos.y9eps6w.mongodb.net/?retryWrites=true&w=majority&appName=Estabelecimentos"
    
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client['Cadastros']  # Alterado para usar a database "Cadastros"
    return db['Estabelecimentos']  # Alterado para usar a coleção "Estabelecimentos"

collection = get_db_connection()

# Função para calcular distância entre coordenadas
def calcular_distancia(lat1, lon1, lat2, lon2):
    return haversine((lat1, lon1), (lat2, lon2))

# Função para verificar distância mínima
def verificar_distancia_minima(lat, lon, min_dist_km=2):
    estabelecimentos = list(collection.find({}, {'_id': 0, 'latitude': 1, 'longitude': 1}))
    
    for estab in estabelecimentos:
        distancia = calcular_distancia(
            lat, lon,
            estab['latitude'], estab['longitude']
        )
        if distancia < min_dist_km:
            return False, distancia
    return True, None

# Interface Streamlit
st.title("Sistema de Cadastro de Estabelecimentos")

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
