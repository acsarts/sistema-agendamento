import streamlit as st
import pandas as pd
import re

# Configuração da página
st.set_page_config(page_title="Sistema de Agendamento", layout="wide")

st.title("📅 Sistema de Agendamento Inteligente")
st.markdown("Cole sua lista abaixo seguindo o padrão vertical: **Nome** (linha 1), **Horário** (linha 2), **Tipo** (linha 3).")

# ==========================================
# 1. INPUT DE DADOS NA TELA (Exemplo atualizado)
# ==========================================
texto_padrao = """Rafael Barbosa
07:30 às 09:30
Aula ao vivo

Claiton Natal
14:00 às 16:00
Aula ao vivo

Mário Elesbão Lima Da Silva
18:30 às 21:00
Aula ao vivo"""

lista_input = st.text_area("Cole a lista aqui:", value=texto_padrao, height=300)

# Botão de Ação
botao_gerar = st.button("🚀 Gerar Grade")

# ==========================================
# 2. CONFIGURAÇÃO (Sem o estúdio 11)
# ==========================================
regras_estudios = {
    '2 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [], 'proibido': ['Pós-Graduação', 'Graduação']},
    '3 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [], 'proibido': []},
    '4 PKS': {'abertura': '08:30', 'fechamento': '21:00', 'intervalos': [], 'proibido': []},
    '6 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [('12:00', '13:30'), ('17:00', '18:30')], 'proibido': []},
    '7 PKS': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '8 PKS': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []},
    '9 PKS': {'abertura': '07:30', 'fechamento': '22:30', 'intervalos': [('12:00', '13:30'), ('17:00', '18:30')], 'proibido': []},
    '12 SE//DE': {'abertura': '07:00', 'fechamento': '23:00', 'intervalos': [], 'proibido': []}
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
# 4. LÓGICA DE LEITURA (NOVA INTELEGÊNCIA VERTICAL)
# ==========================================
if botao_gerar:
    # Limpa as linhas vazias e espaços extras
    linhas = [l.strip() for l in lista_input.split('\n') if l.strip()]
    aulas = []
    
    # Percorre todas as linhas procurando por horários
    for i, linha in enumerate(linhas):
        # A âncora é a linha que tem "às" e números (formato de horário)
        if 'às' in linha and re.search(r'\d{1,2}:\d{2}', linha):
            
            # 1. Pega o NOME (Linha anterior)
            nome = "Desconhecido"
            if i > 0:
                nome = linhas[i-1] # Pega a linha de cima
            
            # 2. Pega o HORÁRIO (Linha atual)
            try:
                partes_h = linha.split('às')
                inicio_str = partes_h[0].strip()
                fim_str = partes_h[1].strip().split(' ')[0] # Garante pegar só a hora
            except:
                st.error(f"Erro na formatação do horário: {linha}")
                continue

            # 3. Pega o TIPO (Linha posterior)
            tipo = "Geral"
            if i + 1 < len(linhas):
                proxima = linhas[i+1]
                # Verifica se a próxima linha não é outro horário (caso tenha esquecido o tipo)
                if 'às' not in proxima:
                    tipo = proxima

            # Salva
            aulas.append({
                'prof': nome,
                'inicio': converte_minutos(inicio_str),
                'fim': converte_minutos(fim_str),
                'tipo': tipo,
                'orig_inicio': inicio_str,
                'orig_fim': fim_str
            })

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
        st.warning("Nenhuma aula identificada. Verifique se há uma linha com 'Nome', depois 'Horário', depois 'Tipo'.")

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
