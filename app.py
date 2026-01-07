import streamlit as st
import pandas as pd
import re

# Configuração da página
st.set_page_config(page_title="Sistema de Agendamento Balanceado", layout="wide")

st.title("⚖️ Sistema de Agendamento (Balanceamento de Carga)")
st.markdown("Este sistema distribui as aulas para garantir que todos os estúdios/operadores trabalhem a mesma quantidade de horas, sempre que possível.")

# ==========================================
# 1. INPUT DE DADOS NA TELA
# ==========================================
texto_padrao = """Rafael Barbosa
07:30 às 09:30
Aula ao vivo

Claiton Natal
14:00 às 16:00
Aula ao vivo

Mário Elesbão Lima Da Silva
18:30 às 21:00
Aula ao vivo

Ana Silva
08:00 às 10:00
Gravação

Pedro Santos
08:00 às 10:00
Gravação"""

lista_input = st.text_area("Cole a lista aqui (Padrão: Nome, Horário, Tipo):", value=texto_padrao, height=300)

# Botão de Ação
botao_gerar = st.button("🚀 Gerar Grade Balanceada")

# ==========================================
# 2. CONFIGURAÇÃO DOS ESTÚDIOS
# ==========================================
regras_estudios = {
    '2 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [], 'proibido': ['Pós-Graduação', 'Graduação']},
    '3 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [], 'proibido': []},
    '4 PKS': {'abertura': '08:30', 'fechamento': '21:00', 'intervalos': [], 'proibido': []},
    '6 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [('12:00', '13:30'), ('17:00', '18:30')], 'proibido': []},
    '7 PKS': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '8 PKS': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '9 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [('12:00', '13:30'), ('17:00', '18:30')], 'proibido': []},
}

# ==========================================
# 3. FUNÇÕES AUXILIARES
# ==========================================
def converte_minutos(horario_str):
    try:
        limpo = re.sub(r'[^\d:]', '', horario_str)
        h, m = map(int, limpo.split(':'))
        return h * 60 + m
    except:
        return -1

def verifica_colisao(inicio1, fim1, inicio2, fim2):
    return max(inicio1, inicio2) < min(fim1, fim2)

def buscar_sugestoes(aula, regras, ocupacoes):
    duracao = aula['fim'] - aula['inicio']
    sugestoes = []
    for nome, regra in regras.items():
        if any(p.lower() in aula['tipo'].lower() for p in regra['proibido']): continue
        abertura = converte_minutos(regra['abertura'])
        fechamento = converte_minutos(regra['fechamento'])
        
        for t_ini in range(abertura, fechamento, 30):
            t_fim = t_ini + duracao
            if t_fim > fechamento: break
            
            if any(verifica_colisao(t_ini, t_fim, converte_minutos(i[0]), converte_minutos(i[1])) for i in regra['intervalos']): continue
            if any(verifica_colisao(t_ini, t_fim, oc['inicio'], oc['fim']) for oc in ocupacoes[nome]): continue
            
            h_txt = f"{t_ini//60:02d}:{t_ini%60:02d}"
            f_txt = f"{t_fim//60:02d}:{t_fim%60:02d}"
            sugestoes.append(f"{h_txt} - {f_txt} ({nome})")
            break 
    return sugestoes

# ==========================================
# 4. LÓGICA DE BALANCEAMENTO
# ==========================================
if botao_gerar:
    # 1. Leitura dos dados
    linhas = [l.strip() for l in lista_input.split('\n') if l.strip()]
    aulas = []
    
    for i, linha in enumerate(linhas):
        if 'às' in linha and re.search(r'\d{1,2}:\d{2}', linha):
            nome = linhas[i-1] if i > 0 else "Desconhecido"
            try:
                partes_h = linha.split('às')
                inicio_str = partes_h[0].strip()
                fim_str = partes_h[1].strip().split(' ')[0]
            except: continue
            
            tipo = "Geral"
            if i + 1 < len(linhas):
                proxima = linhas[i+1]
                if 'às' not in proxima: tipo = proxima

            aulas.append({
                'prof': nome,
                'inicio': converte_minutos(inicio_str),
                'fim': converte_minutos(fim_str),
                'tipo': tipo,
                'orig_inicio': inicio_str,
                'orig_fim': fim_str,
                'duracao': converte_minutos(fim_str) - converte_minutos(inicio_str)
            })

    # Ordena por horário (para garantir cronologia), mas também poderia ordenar por duração (do maior pro menor) para encaixar os grandes primeiro
    # Vamos manter por horário de início para respeitar a fila do dia
    aulas.sort(key=lambda x: x['inicio'])
    
    agenda_final = []
    nao_agendados = []
    ocupacao_estudios = {k: [] for k in regras_estudios.keys()}
    
    # NOVO: Rastreador de Carga Horária (em minutos) para Balanceamento
    carga_estudios = {k: 0 for k in regras_estudios.keys()}

    for aula in aulas:
        agendado = False
        if aula['inicio'] == -1: 
            nao_agendados.append(aula)
            continue

        # --- A MÁGICA DO BALANCEAMENTO ACONTECE AQUI ---
        # 1. Encontra TODOS os estúdios possíveis para esta aula
        candidatos_validos = []

        for nome_estudio, regras in regras_estudios.items():
            abertura = converte_minutos(regras['abertura'])
            fechamento = converte_minutos(regras['fechamento'])
            
            # Checagens Básicas
            if aula['inicio'] < abertura or aula['fim'] > fechamento: continue
            if any(p.lower() in aula['tipo'].lower() for p in regras['proibido']): continue
            
            # Checagem de Intervalos do Estúdio
            if any(verifica_colisao(aula['inicio'], aula['fim'], converte_minutos(i[0]), converte_minutos(i[1])) for i in regras['intervalos']): continue
            
            # Checagem de Conflito com Agenda Existente
            if any(verifica_colisao(aula['inicio'], aula['fim'], oc['inicio'], oc['fim']) for oc in ocupacao_estudios[nome_estudio]): continue
            
            # Se passou por tudo, é um candidato
            candidatos_validos.append(nome_estudio)

        # 2. Escolhe o candidato que tem MENOS carga horária acumulada
        if candidatos_validos:
            # Ordena os candidatos baseados em quem trabalhou menos até agora
            candidatos_validos.sort(key=lambda x: carga_estudios[x])
            
            melhor_estudio = candidatos_validos[0] # O primeiro é o mais vazio
            
            # Agenda
            ocupacao_estudios[melhor_estudio].append(aula)
            carga_estudios[melhor_estudio] += aula['duracao'] # Soma a carga
            
            agenda_final.append({
                'Sala': melhor_estudio, 
                'Horário': f"{aula['orig_inicio']} - {aula['orig_fim']}", 
                'Professor': aula['prof'], 
                'Tipo': aula['tipo']
            })
            agendado = True
        
        if not agendado: nao_agendados.append(aula)

    # Mostra Resultados
    if agenda_final:
        st.success("✅ Grade Gerada e Balanceada!")
        
        # Exibe a tabela principal
        df = pd.DataFrame(agenda_final).sort_values(by=['Sala', 'Horário'])
        st.dataframe(df, use_container_width=True)
        
        # --- RELATÓRIO DE EQUILÍBRIO ---
        st.markdown("### 📊 Relatório de Carga Horária (Equilíbrio)")
        dados_carga = []
        for sala, minutos in carga_estudios.items():
            horas = minutos // 60
            mins = minutos % 60
            dados_carga.append({'Sala': sala, 'Tempo Total': f"{horas}h {mins}min", 'Minutos': minutos})
        
        df_carga = pd.DataFrame(dados_carga).sort_values(by='Minutos', ascending=False)
        st.dataframe(df_carga[['Sala', 'Tempo Total']], use_container_width=True)
        
    else:
        st.warning("Nenhuma aula identificada.")

    if nao_agendados:
        st.error(f"🚨 Conflitos Encontrados: {len(nao_agendados)}")
        for a in nao_agendados:
            with st.expander(f"❌ {a['prof']} ({a['orig_inicio']} - {a['orig_fim']})"):
                st.write(f"**Tipo:** {a['tipo']}")
                sugs = buscar_sugestoes(a, regras_estudios, ocupacao_estudios)
                if sugs:
                    st.write("💡 **Sugestões:**")
                    for s in sugs: st.code(s, language="text")
                else:
                    st.write("⚠️ Sem vagas alternativas.")
