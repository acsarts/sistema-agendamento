import streamlit as st
import pandas as pd
import re

# Configuração da página
st.set_page_config(page_title="Sistema de Agendamento", layout="wide")

st.title("📅 Sistema de Agendamento Inteligente")
st.markdown("Cole sua lista abaixo. O sistema entende nomes e horários, mesmo que o tipo de aula esteja na linha de baixo.")

# ==========================================
# 1. INPUT DE DADOS NA TELA
# ==========================================
texto_padrao = """Rafael Barbosa 07:30 às 09:30
Aula ao vivo

Claiton Natal 14:00 às 16:00
Aula ao vivo

Mário Elesbão Lima Da Silva 18:30 às 21:00
Aula ao vivo"""

lista_input = st.text_area("Cole a lista aqui:", value=texto_padrao, height=300)

# Botão de Ação
botao_gerar = st.button("🚀 Gerar Grade")

# ==========================================
# 2. CONFIGURAÇÃO (Estúdio 11 REMOVIDO)
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
        # Remove caracteres invisíveis e pega só hh:mm
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
# 4. LÓGICA DE LEITURA E PROCESSAMENTO
# ==========================================
if botao_gerar:
    # Quebra o texto em linhas e remove linhas vazias
    linhas_brutas = [l.strip() for l in lista_input.split('\n') if l.strip()]
    aulas = []
    
    i = 0
    while i < len(linhas_brutas):
        linha = linhas_brutas[i]
        
        # Procura pelo padrão de horário "00:00 às 00:00"
        if 'às' in linha and re.search(r'\d{1,2}:\d{2}', linha):
            # Divide a linha no "às"
            partes_horario = linha.split('às')
            
            # O lado ESQUERDO tem "Nome 00:00"
            lado_esquerdo = partes_horario[0].strip()
            # Encontra onde termina o nome e começa a hora (último espaço)
            ultimo_espaco = lado_esquerdo.rfind(' ')
            
            if ultimo_espaco != -1:
                nome = lado_esquerdo[:ultimo_espaco].replace(',', '').strip() # Tira vírgula se tiver
                inicio_str = lado_esquerdo[ultimo_espaco+1:].strip()
            else:
                # Caso de erro na formatação
                nome = "Desconhecido"
                inicio_str = lado_esquerdo
            
            # O lado DIREITO tem "00:00" e talvez lixo
            lado_direito = partes_horario[1].strip()
            # Pega só a primeira "palavra" que deve ser o horário
            fim_str = lado_direito.split(' ')[0]

            # Tenta pegar o TIPO na próxima linha
            tipo = "Geral"
            if i + 1 < len(linhas_brutas):
                proxima_linha = linhas_brutas[i+1]
                # Se a próxima linha NÃO tem "às", é porque é o tipo da aula
                if 'às' not in proxima_linha:
                    tipo = proxima_linha
                    i += 1 # Pula essa linha pois já lemos
            
            # Salva a aula
            try:
                aulas.append({
                    'prof': nome,
                    'inicio': converte_minutos(inicio_str),
                    'fim': converte_minutos(fim_str),
                    'tipo': tipo,
                    'orig_inicio': inicio_str,
                    'orig_fim': fim_str
                })
            except:
                st.error(f"Erro ao ler linha: {linha}")

        i += 1

    # Ordena e Agenda
    aulas.sort(key=lambda x: x['inicio'])
    agenda_final = []
    nao_agendados = []
    ocupacao_estudios = {k: [] for k in regras_estudios.keys()}

    for aula in aulas:
        agendado = False
        if aula['inicio'] == -1: 
            nao_agendados.append(aula)
            continue

        for nome_estudio, regras in regras_estudios.items():
            abertura = converte_minutos(regras['abertura'])
            fechamento = converte_minutos(regras['fechamento'])
            
            if aula['inicio'] < abertura or aula['fim'] > fechamento: continue
            if any(p.lower() in aula['tipo'].lower() for p in regras['proibido']): continue
            
            if any(verifica_colisao(aula['inicio'], aula['fim'], converte_minutos(i[0]), converte_minutos(i[1])) for i in regras['intervalos']): continue
            if any(verifica_colisao(aula['inicio'], aula['fim'], oc['inicio'], oc['fim']) for oc in ocupacao_estudios[nome_estudio]): continue
            
            ocupacao_estudios[nome_estudio].append(aula)
            agenda_final.append({'Sala': nome_estudio, 'Horário': f"{aula['orig_inicio']} - {aula['orig_fim']}", 'Professor': aula['prof'], 'Tipo': aula['tipo']})
            agendado = True
            break
        
        if not agendado: nao_agendados.append(aula)

    # Mostra Resultados
    if agenda_final:
        st.success("✅ Grade Gerada com Sucesso!")
        df = pd.DataFrame(agenda_final).sort_values(by=['Sala', 'Horário'])
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Nenhuma aula encontrada ou agendada. Verifique se o formato está correto.")

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
