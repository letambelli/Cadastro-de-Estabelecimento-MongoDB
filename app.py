import streamlit as st
from pymongo import MongoClient
from haversine import haversine
import certifi
import re

# MongoDB Configuration
def get_db_connection():
    CONNECTION_STRING = "mongodb+srv://pvitor66:fthCckusnQWvwiPz@estabelecimentos.y9eps6w.mongodb.net/?retryWrites=true&w=majority&appName=Estabelecimentos"
    client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client['Cadastros']
    return db['Estabelecimentos']

collection = get_db_connection()

# Establishment types
TIPOS_ESTABELECIMENTOS = [
    "Restaurante",
    "Bar",
    "Cafeteria",
    "Loja de Conveniência",
    "Farmácia",
    "Supermercado",
    "Posto de Gasolina",
    "Hotel",
    "Clínica Médica",
    "Outro"
]

# Phone validation
def validar_telefone(telefone):
    padrao = re.compile(r'^\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}$')
    return bool(padrao.match(telefone))

# Distance calculation
def calcular_distancia(lat1, lon1, lat2, lon2):
    return haversine((lat1, lon1), (lat2, lon2))

# Minimum distance verification
def verificar_distancia_minima(lat, lon, min_dist_km=2, exclude_id=None):
    query = {} if exclude_id is None else {'_id': {'$ne': exclude_id}}
    estabelecimentos = list(collection.find(query, {'_id': 0, 'latitude': 1, 'longitude': 1}))
    
    for estab in estabelecimentos:
        distancia = calcular_distancia(lat, lon, estab['latitude'], estab['longitude'])
        if distancia < min_dist_km:
            return False, distancia
    return True, None

# Report functions
def relatorio_estabelecimentos_raio(nome_estabelecimento, raio_km):
    estabelecimento_ref = collection.find_one({'nome': nome_estabelecimento}, 
                                            {'_id': 0, 'latitude': 1, 'longitude': 1})
    if not estabelecimento_ref:
        return None
    
    estabelecimentos = list(collection.find({}, {'_id': 0, 'nome': 1, 'tipo': 1, 'latitude': 1, 'longitude': 1}))
    resultados = []
    
    for estab in estabelecimentos:
        if estab['nome'] != nome_estabelecimento:
            distancia = calcular_distancia(estabelecimento_ref['latitude'], estabelecimento_ref['longitude'],
                                         estab['latitude'], estab['longitude'])
            if distancia <= raio_km:
                resultados.append({
                    'Estabelecimento': estab['nome'],
                    'Tipo': estab.get('tipo', 'Não informado'),
                    'Distância (km)': round(distancia, 2)
                })
    
    return resultados

def relatorio_estabelecimento_mais_proximo(lat, lon):
    estabelecimentos = list(collection.find({}, {'_id': 0, 'nome': 1, 'tipo': 1, 'latitude': 1, 'longitude': 1}))
    if not estabelecimentos:
        return None
    
    mais_proximo = None
    menor_distancia = float('inf')
    tipo_estabelecimento = None
    
    for estab in estabelecimentos:
        distancia = calcular_distancia(lat, lon, estab['latitude'], estab['longitude'])
        if distancia < menor_distancia:
            menor_distancia = distancia
            mais_proximo = estab['nome']
            tipo_estabelecimento = estab.get('tipo', 'Não informado')
    
    return {
        'Estabelecimento mais próximo': mais_proximo,
        'Tipo': tipo_estabelecimento,
        'Distância (km)': round(menor_distancia, 2)
    }

# Streamlit Interface
st.title("Sistema de Cadastro de Estabelecimentos")

# Tabs organization
tab1, tab2, tab3 = st.tabs(["Cadastro", "Relatórios Geográficos", "Gerenciar Estabelecimentos"])

with tab1:
    with st.form("cadastro_form"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Estabelecimento*")
            tipo = st.selectbox("Tipo de Estabelecimento*", TIPOS_ESTABELECIMENTOS)
            telefone = st.text_input("Telefone", placeholder="(XX) XXXX-XXXX")
            
        with col2:
            lat = st.number_input("Latitude*", format="%.6f")
            lon = st.number_input("Longitude*", format="%.6f")
        
        endereco = st.text_input("Endereço Completo")
        descricao = st.text_area("Descrição")
        horario_funcionamento = st.text_input("Horário de Funcionamento")
        
        submitted = st.form_submit_button("Cadastrar")
        
        if submitted:
            erros = []
            if not nome:
                erros.append("Por favor, insira um nome para o estabelecimento")
            if not tipo:
                erros.append("Por favor, selecione um tipo de estabelecimento")
            if telefone and not validar_telefone(telefone):
                erros.append("Formato de telefone inválido. Use (XX) XXXX-XXXX ou similar")
            
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                valido, distancia = verificar_distancia_minima(lat, lon)
                
                if valido:
                    estabelecimento = {
                        'nome': nome,
                        'tipo': tipo,
                        'telefone': telefone if telefone else None,
                        'endereco': endereco if endereco else None,
                        'descricao': descricao if descricao else None,
                        'horario_funcionamento': horario_funcionamento if horario_funcionamento else None,
                        'latitude': lat,
                        'longitude': lon
                    }
                    collection.insert_one(estabelecimento)
                    st.success("Estabelecimento cadastrado com sucesso!")
                else:
                    st.error(f"Não é possível cadastrar. Existe um estabelecimento a {distancia:.2f} km de distância (mínimo 2 km requerido).")

with tab2:
    st.header("Relatórios Geográficos")
    
    # Get establishments list
    lista_estabelecimentos = [e['nome'] for e in collection.find({}, {'_id': 0, 'nome': 1})]
    
    if not lista_estabelecimentos:
        st.warning("Nenhum estabelecimento cadastrado para gerar relatórios.")
    else:
        # Radius report
        st.subheader("Estabelecimentos em raio de um local")
        col1, col2 = st.columns(2)
        with col1:
            estabelecimento_base = st.selectbox(
                "Selecione o estabelecimento base:",
                lista_estabelecimentos,
                index=0,
                key="select_base"
            )
        with col2:
            raio_km = st.selectbox(
                "Raio de busca (km):",
                [1, 2, 5, 10, 15, 20],
                index=3,
                key="select_raio"
            )
        
        if st.button("Gerar Relatório de Raio", key="btn_raio"):
            resultado = relatorio_estabelecimentos_raio(estabelecimento_base, raio_km)
            if resultado is not None:
                if resultado:
                    st.table(resultado)
                    st.info(f"Total de estabelecimentos em {raio_km}km de {estabelecimento_base}: {len(resultado)}")
                else:
                    st.info(f"Não há estabelecimentos num raio de {raio_km}km de {estabelecimento_base}.")
            else:
                st.error("Estabelecimento não encontrado.")
        
        # Nearest establishment
        st.subheader("Estabelecimento mais próximo de um ponto")
        col1, col2 = st.columns(2)
        with col1:
            lat_consulta = st.number_input("Latitude do ponto", format="%.6f", key="lat_consulta")
        with col2:
            lon_consulta = st.number_input("Longitude do ponto", format="%.6f", key="lon_consulta")
        
        if st.button("Encontrar mais próximo", key="btn_mais_proximo"):
            resultado = relatorio_estabelecimento_mais_proximo(lat_consulta, lon_consulta)
            if resultado:
                st.success(f"Estabelecimento mais próximo: {resultado['Estabelecimento mais próximo']} ({resultado['Distância (km)']} km)")
                st.info(f"Tipo: {resultado['Tipo']}")
            else:
                st.warning("Nenhum estabelecimento encontrado.")

with tab3:
    st.header("Gerenciar Estabelecimentos Cadastrados")
    
    estabelecimentos = list(collection.find({}, {'_id': 1, 'nome': 1, 'tipo': 1, 'telefone': 1, 
                                               'endereco': 1, 'descricao': 1, 'horario_funcionamento': 1,
                                               'latitude': 1, 'longitude': 1}))
    
    if not estabelecimentos:
        st.info("Nenhum estabelecimento cadastrado.")
    else:
        estabelecimento_selecionado = st.selectbox(
            "Selecione um estabelecimento para gerenciar",
            [f"{estab['nome']} ({estab.get('tipo', 'Tipo não informado')})" for estab in estabelecimentos],
            index=0
        )
        
        estab_id = None
        estab_dados = None
        for estab in estabelecimentos:
            if f"{estab['nome']} ({estab.get('tipo', 'Tipo não informado')})" == estabelecimento_selecionado:
                estab_id = estab['_id']
                estab_dados = estab
                break
        
        tab_editar, tab_excluir, tab_detalhes = st.tabs(["Editar", "Excluir", "Detalhes"])
        
        with tab_detalhes:
            st.subheader("Detalhes do Estabelecimento")
            st.write(f"**Nome:** {estab_dados['nome']}")
            st.write(f"**Tipo:** {estab_dados.get('tipo', 'Não informado')}")
            st.write(f"**Telefone:** {estab_dados.get('telefone', 'Não informado')}")
            st.write(f"**Endereço:** {estab_dados.get('endereco', 'Não informado')}")
            st.write(f"**Descrição:** {estab_dados.get('descricao', 'Não informada')}")
            st.write(f"**Horário de Funcionamento:** {estab_dados.get('horario_funcionamento', 'Não informado')}")
            st.write(f"**Latitude:** {estab_dados['latitude']}")
            st.write(f"**Longitude:** {estab_dados['longitude']}")
        
        with tab_editar:
            st.subheader("Editar Estabelecimento")
            with st.form("editar_form"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome*", value=estab_dados['nome'])
                    novo_tipo = st.selectbox("Tipo de Estabelecimento*", 
                                           TIPOS_ESTABELECIMENTOS,
                                           index=TIPOS_ESTABELECIMENTOS.index(estab_dados.get('tipo', 'Outro')))
                    novo_telefone = st.text_input("Telefone", 
                                                value=estab_dados.get('telefone', ''),
                                                placeholder="(XX) XXXX-XXXX")
                
                with col2:
                    nova_lat = st.number_input("Latitude*", format="%.6f", value=estab_dados['latitude'])
                    nova_lon = st.number_input("Longitude*", format="%.6f", value=estab_dados['longitude'])
                
                novo_endereco = st.text_input("Endereço Completo", value=estab_dados.get('endereco', ''))
                nova_descricao = st.text_area("Descrição", value=estab_dados.get('descricao', ''))
                novo_horario = st.text_input("Horário de Funcionamento", value=estab_dados.get('horario_funcionamento', ''))
                
                submitted = st.form_submit_button("Salvar Alterações")
                
                if submitted:
                    erros = []
                    if not novo_nome:
                        erros.append("Por favor, insira um nome para o estabelecimento")
                    if not novo_tipo:
                        erros.append("Por favor, selecione um tipo de estabelecimento")
                    if novo_telefone and not validar_telefone(novo_telefone):
                        erros.append("Formato de telefone inválido. Use (XX) XXXX-XXXX ou similar")
                    
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        valido, distancia = verificar_distancia_minima(nova_lat, nova_lon, exclude_id=estab_id)
                        
                        if valido:
                            collection.update_one(
                                {'_id': estab_id},
                                {'$set': {
                                    'nome': novo_nome,
                                    'tipo': novo_tipo,
                                    'telefone': novo_telefone if novo_telefone else None,
                                    'endereco': novo_endereco if novo_endereco else None,
                                    'descricao': nova_descricao if nova_descricao else None,
                                    'horario_funcionamento': novo_horario if novo_horario else None,
                                    'latitude': nova_lat,
                                    'longitude': nova_lon
                                }}
                            )
                            st.success("Estabelecimento atualizado com sucesso!")
                            st.experimental_rerun()
                        else:
                            st.error(f"Não é possível atualizar. Existe um estabelecimento a {distancia:.2f} km de distância (mínimo 2 km requerido).")
        
        with tab_excluir:
            st.subheader("Excluir Estabelecimento")
            st.warning("Esta ação é irreversível. Tem certeza que deseja excluir este estabelecimento?")
            
            if st.button("Confirmar Exclusão"):
                collection.delete_one({'_id': estab_id})
                st.success("Estabelecimento excluído com sucesso!")
                st.experimental_rerun()