"""
    FIFO - remove o mais antigo
    LRU - remove o menos recentemente usado
    LFU - remove o menos utilizado
"""

from collections import defaultdict
from pathlib import Path

# Tempo para encontrar um bloco descendo cada nivel
TEMPO_L1 = 1
TEMPO_L2 = 3
TEMPO_L3 = 6
TEMPO_RAM = 16

# Usado para respeitar o orcamento da arquitetura
CUSTO_L1 = 200
CUSTO_L2 = 50
CUSTO_L3 = 10
ORCAMENTO_MAXIMO = 1100

POLITICAS = ("FIFO", "LRU", "LFU")


class Cache:
    """
    Representa UM nivel de cache (L1, L2 ou L3).

    Cada cache possui:
        - capacidade maxima (quantos blocos cabem)
        - politica de substituicao
        - estrutura para armazenar blocos

    Estruturas auxiliares:
    - ordem = usada no FIFO (fila de insercao)
    - tempo = usada no LRU (controle de uso recente)
    - freq  = usada no LFU (contagem de acessos)

    Tambem utilizamos um "relogio logico" para simular
    a passagem do tempo entre acessos.
    """

    def __init__(self, capacidade, politica):
        # capacidade maxima da cache (quantidade de blocos)
        self.capacidade = capacidade

        # politica de substituicao
        self.politica = politica

        # Lista principal contendo os blocos atualmente na cache
        self.dados = []

        # FIFO = mantem ordem de chegada dos blocos
        self.ordem = []

        # LRU = armazena o "tempo" do ultimo acesso de cada bloco
        self.tempo = {}

        # LFU = armazena a frequencia de acesso de cada bloco
        self.freq = defaultdict(int)

        # Relogio logico usado para simular o "tempo" de acesso.
        self.relogio = 0

    def contem(self, bloco):
        """
        Verifica se o bloco esta presente na cache.

        - True  = HIT (bloco encontrado)
        - False = MISS (bloco nao esta na cache)
        """
        return bloco in self.dados

    def registrar_acesso(self, bloco):
        """
        O QUE ESTE METODO FAZ?
        Sempre que um bloco e acessado (HIT),
        precisamos atualizar informacoes dependendo da politica.

        LRU = atualiza o tempo do ultimo acesso
        LFU = incrementa a frequencia de uso
        FIFO = nao precisa atualizar nada
        """

        # Avanca o relogio logico
        self.relogio += 1

        if self.politica in ("LRU", "LFU"):
            self.tempo[bloco] = self.relogio

        if self.politica == "LFU":
            # aumenta o numero de acessos desse bloco
            self.freq[bloco] += 1

    def inserir(self, bloco):
        """
        1. Se o bloco ja existe = apenas atualiza (HIT)
        2. Se a cache esta cheia = remove um bloco (substituicao)
        3. Insere o novo bloco
        4. Atualiza estruturas auxiliares
        """

        self.relogio += 1

        # Caso ja exista, apenas atualizamos
        if bloco in self.dados:
            self.registrar_acesso(bloco)
            return

        # Se nao ha espaco, precisamos remover
        if len(self.dados) >= self.capacidade:
            self.remover()

        # Insere o novo bloco
        self.dados.append(bloco)

        # Atualizacao das estruturas auxiliares
        if self.politica == "FIFO":
            # Registra ordem de chegada
            self.ordem.append(bloco)
        elif self.politica == "LRU":
            # Define o tempo inicial como o momento atual
            self.tempo[bloco] = self.relogio
        elif self.politica == "LFU":
            # Inicializa frequencia como 1 (primeiro acesso)
            self.freq[bloco] = 1
            # Corrige desempate LFU com LRU para blocos novos
            self.tempo[bloco] = self.relogio

    def remover(self):
        """
        FIFO = remove o mais antigo (primeiro inserido)
        LRU  = remove o menos recentemente usado
        LFU  = remove o menos frequentemente usado
        """

        if self.politica == "FIFO":
            # FIFO -> First In, First Out - Remove o primeiro que entrou na fila.
            bloco = self.ordem.pop(0)
            self.dados.remove(bloco)

        elif self.politica == "LRU":
            # LRU -> Seleciona o bloco com menor tempo
            bloco = min(self.tempo, key=self.tempo.get)
            self.dados.remove(bloco)
            del self.tempo[bloco]

        elif self.politica == "LFU":
            # Remove o bloco com menor frequencia
            # Em caso de empate, remove o menos recentemente usado (LRU)
            bloco = min(self.dados, key=lambda b: (self.freq[b], self.tempo.get(b, 0)))
            self.dados.remove(bloco)
            del self.freq[bloco]
            if bloco in self.tempo:
                del self.tempo[bloco]


class Simulador:
    """
        - cria as caches (L1, L2, L3)
        - Controla os acessos
        - calcula metricas
        - simula tempo
    """

    def __init__(self, X1, X2, X3, politica):
        """
        CONFIGURACAO DA ARQUITETURA
        X1 -> tamanho da L1
        X2 -> tamanho da L2
        X3 -> tamanho da L3
        """

        # validacoes do enunciado
        if not (1 <= X1 <= 5 and 1 <= X2 <= 10 and 1 <= X3 <= 50):
            raise ValueError("Tamanhos invalidos")
        if not (X1 <= X2 <= X3):
            raise ValueError("Hierarquia invalida")
        # criacao das caches, instancias independentes
        self.L1 = Cache(X1, politica)
        self.L2 = Cache(X2, politica)
        self.L3 = Cache(X3, politica)

        # Hits em cada nivel, acessos a RAM
        self.h1 = 0
        self.h2 = 0
        self.h3 = 0
        self.ram = 0

        # Tempo total gasto e numero de acessos
        self.tempo = 0
        self.total = 0

        self.X1 = X1
        self.X2 = X2
        self.X3 = X3
        self.politica = politica
        # Quantidade de blocos unicos acessados
        self.ram_tamanho = 0

    def gerar_blocos(self, texto):
        """
        Converte a string em pares de caracteres.
        "abcdef" -> ["ab", "cd", "ef"]
        """
        texto_limpo = texto.strip()

        if not texto_limpo.isascii() or not texto_limpo.isalpha():
            raise ValueError(
                "Entrada invalida: use apenas caracteres alfabeticos simples (A-Z, a-z)."
            )
        if len(texto_limpo) < 2:
            raise ValueError("Entrada muito curta. Use pelo menos 2 caracteres.")

        blocos = []
        for i in range(0, len(texto_limpo) - 1, 2):
            blocos.append(texto_limpo[i:i + 2])
        return blocos

    def promover(self, bloco, nivel):
        """
        Se encontrou em nivel inferior, sobe para niveis superiores.
        nivel: 2 -> veio da L2 | 3 -> veio da L3 | 4 -> veio da RAM
        """

        if nivel == 4:  # veio da RAM
            self.L3.inserir(bloco)
            self.L2.inserir(bloco)
            self.L1.inserir(bloco)
        elif nivel == 3:  # veio da L3
            self.L2.inserir(bloco)
            self.L1.inserir(bloco)
        elif nivel == 2:  # veio da L2
            self.L1.inserir(bloco)

    def acessar_hierarquia(self, bloco):
        """
        E a funcao mais importante e simula um acesso completo
        Ordem: L1 -> L2 -> L3 -> RAM
        """
        self.total += 1

        # L1
        if self.L1.contem(bloco):
            self.h1 += 1
            self.tempo += TEMPO_L1
            self.L1.registrar_acesso(bloco)
            return

        # L2
        if self.L2.contem(bloco):
            self.h2 += 1
            self.tempo += TEMPO_L1 + TEMPO_L2
            self.L2.registrar_acesso(bloco)
            self.promover(bloco, 2)
            return

        # L3
        if self.L3.contem(bloco):
            self.h3 += 1
            self.tempo += TEMPO_L1 + TEMPO_L2 + TEMPO_L3
            self.L3.registrar_acesso(bloco)
            self.promover(bloco, 3)
            return

        # RAM
        self.ram += 1
        self.tempo += TEMPO_L1 + TEMPO_L2 + TEMPO_L3 + TEMPO_RAM
        self.promover(bloco, 4)

    # rodar a simulacao completa de memoria
    def executar(self, texto):
        blocos = self.gerar_blocos(texto)
        self.ram_tamanho = len(set(blocos))

        # blocos = ["aa", "ab", "ac"], acessa aa, depois ab e assim por diante
        for bloco in blocos:
            self.acessar_hierarquia(bloco)
        return self.resultado()

    def resultado(self):
        """
        Retorna metricas finais
        """
        taxa_l1 = (self.h1 / self.total) if self.total else 0
        taxa_l2 = (self.h2 / self.total) if self.total else 0
        taxa_l3 = (self.h3 / self.total) if self.total else 0
        taxa_global_faltas = (self.ram / self.total) if self.total else 0
        custo_total = CUSTO_L1 * self.X1 + CUSTO_L2 * self.X2 + CUSTO_L3 * self.X3

        return {
            "configuracao": {
                "X1": self.X1,
                "X2": self.X2,
                "X3": self.X3,
                "politica": self.politica,
            },
            "custo_total": custo_total,
            "ram_tamanho_automatico": self.ram_tamanho,
            "acessos": self.total,
            "hits_L1": self.h1,
            "hits_L2": self.h2,
            "hits_L3": self.h3,
            "RAM": self.ram,
            "taxa_hit_L1": taxa_l1,
            "taxa_hit_L2": taxa_l2,
            "taxa_hit_L3": taxa_l3,
            "taxa_global_faltas": taxa_global_faltas,
            "tempo_total": self.tempo,
            "tempo_medio": (self.tempo / self.total) if self.total else 0,
        }


def carregar_benchmark_por_padroes(caminho_arquivo):
    """
    Carrega benchmark.txt agrupando entradas por padrao.
    """
    padroes = []
    titulo_atual = None
    entradas_atuais = []

    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            conteudo = linha.strip()
            if not conteudo:
                continue
            if conteudo.startswith("# PADRAO"):
                if titulo_atual is not None:
                    padroes.append({"titulo": titulo_atual, "entradas": entradas_atuais})
                titulo_atual = conteudo.lstrip("# ").strip()
                entradas_atuais = []
                continue
            if conteudo.startswith("#"):
                continue
            if titulo_atual is not None:
                entradas_atuais.append(conteudo)

    if titulo_atual is not None:
        padroes.append({"titulo": titulo_atual, "entradas": entradas_atuais})
    if not padroes:
        raise ValueError("Nenhum padrao valido encontrado no benchmark.")
    return padroes


def calcular_custo_configuracao(X1, X2, X3):
    return CUSTO_L1 * X1 + CUSTO_L2 * X2 + CUSTO_L3 * X3


def resumir_metricas(metricas):
    if not metricas:
        return None

    totais = {
        "acessos": 0,
        "hits_L1": 0,
        "hits_L2": 0,
        "hits_L3": 0,
        "RAM": 0,
        "ram_tamanho_total": 0,
        "ram_tamanho_max": 0,
        "tempo_total": 0,
        "custo_total": metricas[0]["custo_total"],
    }

    for metrica in metricas:
        totais["acessos"] += metrica["acessos"]
        totais["hits_L1"] += metrica["hits_L1"]
        totais["hits_L2"] += metrica["hits_L2"]
        totais["hits_L3"] += metrica["hits_L3"]
        totais["RAM"] += metrica["RAM"]
        # Suporta tanto metrica individual (ram_tamanho_automatico)
        # quanto resumo agregado (ram_tamanho_medio / ram_tamanho_max).
        if "ram_tamanho_automatico" in metrica:
            ram_ref = metrica["ram_tamanho_automatico"]
        else:
            ram_ref = metrica.get("ram_tamanho_medio", 0)
        totais["ram_tamanho_total"] += ram_ref
        totais["ram_tamanho_max"] = max(totais["ram_tamanho_max"], metrica.get("ram_tamanho_max", ram_ref))
        totais["tempo_total"] += metrica["tempo_total"]

    acessos = totais["acessos"]
    totais["taxa_hit_L1"] = (totais["hits_L1"] / acessos) if acessos else 0
    totais["taxa_hit_L2"] = (totais["hits_L2"] / acessos) if acessos else 0
    totais["taxa_hit_L3"] = (totais["hits_L3"] / acessos) if acessos else 0
    totais["taxa_global_faltas"] = (totais["RAM"] / acessos) if acessos else 0
    totais["tempo_medio"] = (totais["tempo_total"] / acessos) if acessos else 0
    totais["ram_tamanho_medio"] = (totais["ram_tamanho_total"] / len(metricas)) if metricas else 0
    return totais


def resolver_benchmark_principal():
    preferido = Path("benchmark.txt")
    if preferido.exists():
        return str(preferido)

    legado = Path("benchmark_padroes_memoria.txt")
    if legado.exists():
        return str(legado)

    raise FileNotFoundError("Arquivo benchmark.txt nao encontrado.")


def ler_inteiro_intervalo(rotulo, minimo, maximo):
    while True:
        valor_str = input(f"{rotulo} ({minimo}-{maximo}): ").strip()
        try:
            valor = int(valor_str)
        except ValueError:
            print("Valor invalido. Digite um numero inteiro.")
            continue

        if minimo <= valor <= maximo:
            return valor

        print(f"Valor fora do intervalo permitido ({minimo}-{maximo}).")


def ler_politica():
    validas = {"FIFO", "LRU", "LFU"}
    while True:
        politica = input("Politica de substituicao (FIFO/LRU/LFU): ").strip().upper()
        if politica in validas:
            return politica
        print("Politica invalida. Use FIFO, LRU ou LFU.")


def ler_configuracao_usuario():
    while True:
        print("\nInforme os tamanhos das caches em blocos:")
        X1 = ler_inteiro_intervalo("L1", 1, 5)
        X2 = ler_inteiro_intervalo("L2", 1, 10)
        X3 = ler_inteiro_intervalo("L3", 1, 50)
        politica = ler_politica()
        custo = calcular_custo_configuracao(X1, X2, X3)

        if not (X1 <= X2 <= X3):
            print("Hierarquia invalida: e necessario L1 <= L2 <= L3. Tente novamente.")
            continue

        if custo > ORCAMENTO_MAXIMO:
            print(
                f"Configuracao invalida: custo {custo} > "
                f"orcamento maximo {ORCAMENTO_MAXIMO}. Tente novamente."
            )
            continue

        return X1, X2, X3, politica


def formatar_percentual(valor):
    return f"{valor * 100:.2f}%"


def colorir(texto, codigo_cor):
    # Aplica cor ANSI ao texto para melhorar legibilidade no terminal.
    reset = "\033[0m"
    return f"{codigo_cor}{texto}{reset}"


def cor_por_taxa(taxa):
    # Escolhe cor com base no valor da taxa.
    if taxa >= 0.80:
        return "\033[92m"  # verde
    if taxa >= 0.50:
        return "\033[93m"  # amarelo
    return "\033[91m"  # vermelho


def estilo_titulo():
    return "\033[1;37;44m"


def estilo_melhor_config():
    return "\033[1;30;46m"


def estilo_vencedor_geral():
    return "\033[1;30;43m"


def estilo_cabecalho():
    return "\033[1;36m"


def estilo_texto():
    return "\033[0;37m"


def estilo_separador():
    return "\033[90m"


def estilo_coluna_verde():
    return "\033[92m"


def estilo_coluna_amarelo():
    return "\033[93m"


def estilo_coluna_rosa():
    return "\033[95m"


def rotulo_curto_padrao(titulo):
    titulo_up = titulo.upper()
    if "PADRAO" in titulo_up:
        partes = titulo_up.split("PADRAO", 1)[1].strip()
        numero = ""
        for ch in partes:
            if ch.isdigit():
                numero += ch
            elif numero:
                break
        if numero:
            return f"Padrao {numero}"
    return "Padrao"


def exibir_resultado_formatado(indice, metrica):
    cfg = metrica["configuracao"]
    separador = "=" * 86
    titulo = colorir(f" ENTRADA {indice} ", estilo_titulo())

    taxa_l1 = metrica["taxa_hit_L1"]
    taxa_l2 = metrica["taxa_hit_L2"]
    taxa_l3 = metrica["taxa_hit_L3"]
    taxa_faltas = metrica["taxa_global_faltas"]
    config_texto = f"L1={cfg['X1']} | L2={cfg['X2']} | L3={cfg['X3']} | Politica={cfg['politica']}"
    tempo_medio_texto = f"{metrica['tempo_medio']:.2f}"

    print(colorir(separador, estilo_separador()))
    print(titulo)
    print(colorir(separador, estilo_separador()))
    print(
        f"{colorir('Config', estilo_cabecalho())}: "
        f"{colorir(config_texto, estilo_texto())}"
    )
    print(f"{colorir('Custo total', estilo_cabecalho())}: {colorir(metrica['custo_total'], estilo_texto())}")
    print(f"{colorir('RAM automatica', estilo_cabecalho())}: {colorir(str(metrica['ram_tamanho_automatico']) + ' blocos', estilo_texto())}")
    print(colorir("-" * 86, estilo_separador()))
    print(
        f"{colorir('Acessos', estilo_cabecalho())}: {colorir(str(metrica['acessos']), estilo_texto())} | "
        f"{colorir('Hits L1', estilo_cabecalho())}: {colorir(str(metrica['hits_L1']), estilo_texto())} | "
        f"{colorir('Hits L2', estilo_cabecalho())}: {colorir(str(metrica['hits_L2']), estilo_texto())} | "
        f"{colorir('Hits L3', estilo_cabecalho())}: {colorir(str(metrica['hits_L3']), estilo_texto())} | "
        f"{colorir('RAM', estilo_cabecalho())}: {colorir(str(metrica['RAM']), estilo_texto())}"
    )
    print(
        f"{colorir('Taxa hit L1', estilo_cabecalho())}: {colorir(formatar_percentual(taxa_l1), estilo_texto())} | "
        f"{colorir('Taxa hit L2', estilo_cabecalho())}: {colorir(formatar_percentual(taxa_l2), estilo_texto())} | "
        f"{colorir('Taxa hit L3', estilo_cabecalho())}: {colorir(formatar_percentual(taxa_l3), estilo_texto())}"
    )
    print(
        f"{colorir('Taxa global de faltas', estilo_cabecalho())}: "
        f"{colorir(formatar_percentual(taxa_faltas), estilo_texto())}"
    )
    print(
        f"{colorir('Tempo total', estilo_cabecalho())}: {colorir(str(metrica['tempo_total']), estilo_texto())} | "
        f"{colorir('Tempo medio', estilo_cabecalho())}: {colorir(tempo_medio_texto, estilo_texto())}"
    )
    print()


def exibir_tabela_comparativa(titulo, linhas):
    print(colorir("\n" + "=" * 104, estilo_separador()))
    print(colorir(f" {titulo} ", estilo_titulo()))
    print(colorir("=" * 104, estilo_separador()))
    cabecalho = (
        f"{'Politica':<8} | {'Acessos':>7} | {'Hit L1%':>8} | {'Hit L2%':>8} | {'Hit L3%':>8} | "
        f"{'MissGlob%':>9} | {'RAM Tam':>7} | {'Tempo Total':>11} | {'Tempo Medio':>11}"
    )
    print(colorir(cabecalho, estilo_cabecalho()))
    print(colorir("-" * 104, estilo_separador()))

    for linha in linhas:
        texto = (
            f"{linha['politica']:<8} | "
            f"{linha['acessos']:>7} | "
            f"{formatar_percentual(linha['taxa_hit_L1']):>8} | "
            f"{formatar_percentual(linha['taxa_hit_L2']):>8} | "
            f"{formatar_percentual(linha['taxa_hit_L3']):>8} | "
            f"{formatar_percentual(linha['taxa_global_faltas']):>9} | "
            f"{linha.get('ram_tamanho_medio', 0):>7.2f} | "
            f"{linha['tempo_total']:>11} | "
            f"{linha['tempo_medio']:>11.2f}"
        )
        print(colorir(texto, estilo_texto()))
    print()


def exibir_tabela_detalhada_por_entrada(titulo, linhas):
    print(colorir("\n" + "=" * 122, estilo_separador()))
    print(colorir(f" {titulo} ", estilo_titulo()))
    print(colorir("=" * 122, estilo_separador()))
    cabecalho = (
        f"{'Entrada':<7} | {'Politica':<8} | {'Hit L1%':>8} | {'Hit L2%':>8} | {'Hit L3%':>8} | "
        f"{'MissGlob%':>9} | {'RAM Tam':>7} | {'Tempo Total':>11} | {'Tempo Medio':>11}"
    )
    print(colorir(cabecalho, estilo_cabecalho()))
    print(colorir("-" * 122, estilo_separador()))

    for linha in linhas:
        texto = (
            f"{linha['entrada']:<7} | "
            f"{linha['politica']:<8} | "
            f"{formatar_percentual(linha['taxa_hit_L1']):>8} | "
            f"{formatar_percentual(linha['taxa_hit_L2']):>8} | "
            f"{formatar_percentual(linha['taxa_hit_L3']):>8} | "
            f"{formatar_percentual(linha['taxa_global_faltas']):>9} | "
            f"{linha.get('ram_tamanho_automatico', 0):>7} | "
            f"{linha['tempo_total']:>11} | "
            f"{linha['tempo_medio']:>11.2f}"
        )
        print(colorir(texto, estilo_texto()))
    print()


def exibir_menu_principal():
    print(colorir("\n===== MENU PRINCIPAL =====", "\033[1;97;44m"))
    print("1) Avaliar uma string fornecida")
    print("2) Avaliar benchmark completo (comparar FIFO/LRU/LFU)")
    print("3) Avaliar apenas 1 padrao (comparar FIFO/LRU/LFU)")
    print("4) Alterar configuracao (L1, L2, L3, politica)")
    print("5) Mostrar configuracao atual")
    print("6) Relatorio de melhores configuracoes (por padrao)")
    print("0) Sair")


def escolher_padrao(padroes):
    print("\nEscolha um padrao para executar:")
    for i, padrao in enumerate(padroes, start=1):
        print(f"{i}) {padrao['titulo']} ({len(padrao['entradas'])} entradas)")

    while True:
        escolha = input("Digite o numero da opcao: ").strip()
        try:
            idx = int(escolha)
        except ValueError:
            print("Opcao invalida. Digite um numero da lista.")
            continue
        if 1 <= idx <= len(padroes):
            return padroes[idx - 1]
        print("Opcao fora da lista. Tente novamente.")


def executar_fluxo_string_unica(X1, X2, X3, politica):
    while True:
        entrada = input("\nDigite a string de acessos (apenas letras A-Z, sem espacos): ").strip()

        if not entrada:
            print("Entrada vazia. Digite uma string com pelo menos 2 caracteres.")
            continue

        sim = Simulador(X1, X2, X3, politica)
        try:
            metrica = sim.executar(entrada)
        except ValueError as erro:
            print(f"Entrada invalida: {erro}")
            continue

        print("\nResultado da avaliacao da string fornecida:")
        exibir_resultado_formatado(1, metrica)
        break


def executar_politica_em_padrao(padrao, X1, X2, X3, politica):
    metricas = []
    for entrada in padrao["entradas"]:
        sim = Simulador(X1, X2, X3, politica)
        metricas.append(sim.executar(entrada))
    resumo = resumir_metricas(metricas)
    resumo["politica"] = politica
    return resumo, metricas


def executar_fluxo_benchmark_completo(X1, X2, X3):
    caminho = resolver_benchmark_principal()
    padroes = carregar_benchmark_por_padroes(caminho)
    resumo_geral_por_politica = {politica: [] for politica in POLITICAS}

    print(f"\nArquivo benchmark usado: {caminho}")
    print(f"Configuracao base: L1={X1}, L2={X2}, L3={X3}")
    print("Comparacao automatica entre politicas: FIFO, LRU, LFU")

    for padrao in padroes:
        print(colorir(f"\n### {padrao['titulo']} ###", "\033[1;34m"))
        linhas_tabela = []
        linhas_detalhadas = []

        for politica in POLITICAS:
            resumo, metricas = executar_politica_em_padrao(padrao, X1, X2, X3, politica)
            resumo_geral_por_politica[politica].append(resumo)
            linhas_tabela.append(resumo)
            for entrada_idx, metrica in enumerate(metricas, start=1):
                linhas_detalhadas.append({
                    "entrada": entrada_idx,
                    "politica": politica,
                    "taxa_hit_L1": metrica["taxa_hit_L1"],
                    "taxa_hit_L2": metrica["taxa_hit_L2"],
                    "taxa_hit_L3": metrica["taxa_hit_L3"],
                    "taxa_global_faltas": metrica["taxa_global_faltas"],
                    "ram_tamanho_automatico": metrica["ram_tamanho_automatico"],
                    "tempo_total": metrica["tempo_total"],
                    "tempo_medio": metrica["tempo_medio"],
                })

        exibir_tabela_detalhada_por_entrada(f"DETALHE POR ENTRADA - {padrao['titulo']}", linhas_detalhadas)
        exibir_tabela_comparativa(f"COMPARATIVO - {padrao['titulo']}", linhas_tabela)

    linhas_tabela_geral = []
    for politica in POLITICAS:
        resumao = resumir_metricas(resumo_geral_por_politica[politica])
        resumao["politica"] = politica
        linhas_tabela_geral.append(resumao)
    exibir_tabela_comparativa("COMPARATIVO GERAL - TODOS OS PADROES", linhas_tabela_geral)

def executar_fluxo_padrao_unico(X1, X2, X3):
    caminho = resolver_benchmark_principal()
    padroes = carregar_benchmark_por_padroes(caminho)
    padrao = escolher_padrao(padroes)

    print(f"\nPadrao selecionado: {padrao['titulo']}")
    print(f"Configuracao base: L1={X1}, L2={X2}, L3={X3}")
    print("Comparacao automatica entre politicas: FIFO, LRU, LFU")

    linhas_tabela = []
    linhas_detalhadas = []
    for politica in POLITICAS:
        resumo, metricas = executar_politica_em_padrao(padrao, X1, X2, X3, politica)
        linhas_tabela.append(resumo)
        for entrada_idx, metrica in enumerate(metricas, start=1):
            linhas_detalhadas.append({
                "entrada": entrada_idx,
                "politica": politica,
                "taxa_hit_L1": metrica["taxa_hit_L1"],
                "taxa_hit_L2": metrica["taxa_hit_L2"],
                "taxa_hit_L3": metrica["taxa_hit_L3"],
                "taxa_global_faltas": metrica["taxa_global_faltas"],
                "ram_tamanho_automatico": metrica["ram_tamanho_automatico"],
                "tempo_total": metrica["tempo_total"],
                "tempo_medio": metrica["tempo_medio"],
            })

    exibir_tabela_detalhada_por_entrada(f"DETALHE POR ENTRADA - {padrao['titulo']}", linhas_detalhadas)
    exibir_tabela_comparativa(f"COMPARATIVO - {padrao['titulo']}", linhas_tabela)


def gerar_configuracoes_validas():
    configuracoes = []
    for X1 in range(1, 6):
        for X2 in range(1, 11):
            for X3 in range(1, 51):
                if not (X1 <= X2 <= X3):
                    continue
                custo = calcular_custo_configuracao(X1, X2, X3)
                if custo > ORCAMENTO_MAXIMO:
                    continue
                configuracoes.append((X1, X2, X3, custo))
    return configuracoes


def avaliar_configuracao_no_padrao(padrao, X1, X2, X3, politica):
    resumo, metricas = executar_politica_em_padrao(padrao, X1, X2, X3, politica)
    # Verifica consistencia do tempo: resumo deve ser soma dos tempos das entradas.
    tempo_somado = sum(m["tempo_total"] for m in metricas)
    if resumo["tempo_total"] != tempo_somado:
        raise ValueError(
            f"Inconsistencia de tempo detectada: resumo={resumo['tempo_total']} soma_entradas={tempo_somado}"
        )
    return resumo


def buscar_melhores_por_padrao(padrao, configuracoes):
    melhores_por_politica = {}
    melhor_geral = None

    for politica in POLITICAS:
        melhor = None
        for X1, X2, X3, custo in configuracoes:
            resumo = avaliar_configuracao_no_padrao(padrao, X1, X2, X3, politica)
            candidato = {
                "politica": politica,
                "X1": X1,
                "X2": X2,
                "X3": X3,
                "custo": custo,
                "acessos": resumo["acessos"],
                "hits_L1": resumo["hits_L1"],
                "hits_L2": resumo["hits_L2"],
                "hits_L3": resumo["hits_L3"],
                "RAM": resumo["RAM"],
                "tempo_total": resumo["tempo_total"],
                "tempo_medio": resumo["tempo_medio"],
                "taxa_global_faltas": resumo["taxa_global_faltas"],
                "taxa_hit_L1": resumo["taxa_hit_L1"],
                "taxa_hit_L2": resumo["taxa_hit_L2"],
                "taxa_hit_L3": resumo["taxa_hit_L3"],
                "ram_tamanho_medio": resumo.get("ram_tamanho_medio", 0),
            }
            if (
                melhor is None
                or candidato["tempo_total"] < melhor["tempo_total"]
                or (
                    candidato["tempo_total"] == melhor["tempo_total"]
                    and candidato["taxa_global_faltas"] < melhor["taxa_global_faltas"]
                )
            ):
                melhor = candidato

        melhores_por_politica[politica] = melhor
        if (
            melhor_geral is None
            or melhor["tempo_total"] < melhor_geral["tempo_total"]
            or (
                melhor["tempo_total"] == melhor_geral["tempo_total"]
                and melhor["taxa_global_faltas"] < melhor_geral["taxa_global_faltas"]
            )
        ):
            melhor_geral = melhor

    return melhores_por_politica, melhor_geral


def exibir_tabela_melhores_configuracoes(titulo, linhas, estilo=None):
    if estilo is None:
        estilo = estilo_titulo()
    print(colorir("\n" + "=" * 130, estilo_separador()))
    print(colorir(f" {titulo} ", estilo))
    print(colorir("=" * 130, estilo_separador()))
    cabecalho = (
        f"{'Politica':<8} | {'L1':>2} | {'L2':>2} | {'L3':>2} | {'Custo':>5} | "
        f"{'Hit L1%':>8} | {'Hit L2%':>8} | {'Hit L3%':>8} | {'MissGlob%':>9} | "
        f"{'RAM Tam':>7} | {'Tempo Total':>11} | {'Tempo Medio':>11}"
    )
    print(colorir(cabecalho, estilo_cabecalho()))
    print(colorir("-" * 130, estilo_separador()))

    for linha in linhas:
        texto = (
            f"{linha['politica']:<8} | "
            f"{linha['X1']:>2} | {linha['X2']:>2} | {linha['X3']:>2} | {linha['custo']:>5} | "
            f"{formatar_percentual(linha['taxa_hit_L1']):>8} | "
            f"{formatar_percentual(linha['taxa_hit_L2']):>8} | "
            f"{formatar_percentual(linha['taxa_hit_L3']):>8} | "
            f"{formatar_percentual(linha['taxa_global_faltas']):>9} | "
            f"{linha.get('ram_tamanho_medio', 0):>7.2f} | "
            f"{linha['tempo_total']:>11} | "
            f"{linha['tempo_medio']:>11.2f}"
        )
        print(colorir(texto, estilo_texto()))
    print()


def executar_fluxo_relatorio_melhores_configuracoes():
    caminho = resolver_benchmark_principal()
    padroes = carregar_benchmark_por_padroes(caminho)
    configuracoes = gerar_configuracoes_validas()

    print(f"\nArquivo benchmark usado: {caminho}")
    print("Gerando melhores configuracoes por padrao e por politica...")
    print(f"Total de configuracoes validas avaliadas por politica: {len(configuracoes)}")

    linhas_melhor_geral_todos = []

    for padrao in padroes:
        melhores_por_politica, melhor_geral = buscar_melhores_por_padrao(padrao, configuracoes)
        linhas = [melhores_por_politica[pol] for pol in POLITICAS]
        exibir_tabela_melhores_configuracoes(
            f"MELHOR CONFIGURACAO - {padrao['titulo']}",
            linhas,
            estilo_melhor_config(),
        )

        print(colorir("Melhor geral deste padrao:", estilo_cabecalho()))
        exibir_tabela_melhores_configuracoes(
            f"VENCEDOR GERAL - {padrao['titulo']}",
            [melhor_geral],
            estilo_vencedor_geral(),
        )
        linhas_melhor_geral_todos.append({
            "padrao": rotulo_curto_padrao(padrao["titulo"]),
            **melhor_geral,
        })

    print(colorir("\n" + "=" * 170, estilo_separador()))
    print(colorir(" RESUMO FINAL - MELHOR GERAL POR PADRAO ", estilo_vencedor_geral()))
    print(colorir("=" * 170, estilo_separador()))
    cabecalho = (
        f"{'Padrao':<10} {'X1':>3} {'X2':>3} {'X3':>3} {'Politica':<9} {'Custo':>6} {'Acessos':>8} "
        f"{'Hit_L1':>7} {'Hit_L2':>7} {'Hit_L3':>7} {'RAM':>5} "
        f"{'Taxa_L1':>8} {'Taxa_L2':>8} {'Taxa_L3':>8} {'Miss_Global':>11} "
        f"{'Tempo_Total':>11} {'Tempo_Medio':>11}"
    )
    print(colorir(cabecalho, estilo_cabecalho()))
    print(colorir("-" * 170, estilo_separador()))
    for item in linhas_melhor_geral_todos:
        taxa_l1 = f"{item['taxa_hit_L1']:.2f}"
        taxa_l2 = f"{item['taxa_hit_L2']:.2f}"
        taxa_l3 = f"{item['taxa_hit_L3']:.2f}"
        miss_global = f"{item['taxa_global_faltas']:.2f}"
        ram_tam = int(round(item.get("ram_tamanho_medio", 0)))

        linha_base = (
            f"{item['padrao']:<10} "
            f"{item['X1']:>3} {item['X2']:>3} {item['X3']:>3} "
            f"{item['politica']:<9} "
            f"{item['custo']:>6} "
            f"{item['acessos']:>8} "
            f"{item['hits_L1']:>7} {item['hits_L2']:>7} {item['hits_L3']:>7} {item['RAM']:>5} "
            f"{taxa_l1:>8} {taxa_l2:>8} {taxa_l3:>8} {miss_global:>11} "
            f"{item['tempo_total']:>11} {item['tempo_medio']:>11.2f}"
        )
        # Colore por grupos para manter leitura constante e padronizada.
        print(
            colorir(linha_base[:10], estilo_coluna_verde()) +
            colorir(linha_base[10:24], estilo_coluna_verde()) +
            colorir(linha_base[24:34], estilo_coluna_rosa()) +
            colorir(linha_base[34:87], estilo_coluna_verde()) +
            colorir(linha_base[87:123], estilo_coluna_amarelo()) +
            colorir(linha_base[123:], estilo_coluna_verde())
        )
    print()


if __name__ == "__main__":
    X1, X2, X3, politica = ler_configuracao_usuario()

    while True:
        exibir_menu_principal()
        opcao = input("Escolha uma opcao: ").strip()

        if opcao == "1":
            executar_fluxo_string_unica(X1, X2, X3, politica)
        elif opcao == "2":
            executar_fluxo_benchmark_completo(X1, X2, X3)
        elif opcao == "3":
            executar_fluxo_padrao_unico(X1, X2, X3)
        elif opcao == "4":
            X1, X2, X3, politica = ler_configuracao_usuario()
        elif opcao == "5":
            custo = calcular_custo_configuracao(X1, X2, X3)
            print(
                f"\nConfiguracao atual: L1={X1}, L2={X2}, L3={X3}, politica={politica}, "
                f"custo={custo}/{ORCAMENTO_MAXIMO}"
            )
        elif opcao == "6":
            executar_fluxo_relatorio_melhores_configuracoes()
        elif opcao == "0":
            print("Encerrando programa.")
            break
        else:
            print("Opcao invalida. Tente novamente.")
