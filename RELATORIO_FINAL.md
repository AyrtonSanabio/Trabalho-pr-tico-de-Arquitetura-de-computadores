# Relatório Final — Simulador de Hierarquia de Memória Cache

## 1. Instruções para Execução

### 1.1 Pré-requisitos
- Python 3.10+ instalado.
- Arquivos no mesmo diretório:
  - `main.py`
  - `benchmark_padroes_memoria.txt` (ou `benchmark.txt`)

### 1.2 Execução
No terminal, dentro da pasta do projeto:

```powershell
python main.py
```

### 1.3 Fluxos disponíveis no menu
1. Avaliar uma string fornecida.
2. Avaliar benchmark completo (comparar FIFO/LRU/LFU).
3. Avaliar apenas 1 padrão (comparar FIFO/LRU/LFU).
4. Alterar configuração (L1, L2, L3, política).
5. Mostrar configuração atual.
6. Relatório de melhores configurações (por padrão).

## 2. Conjunto de Entradas dos Experimentos

Foi utilizado o arquivo `benchmark_padroes_memoria.txt`, contendo:
- 10 padrões de acesso.
- 3 strings por padrão.
- 100 acessos por string (pares de 2 letras, leitura de 2 em 2).

## 3. Descrição da Implementação

### 3.1 Modelagem
- Classe `Cache`: representa um nível (L1, L2 ou L3).
- Classe `Simulador`: representa a arquitetura completa e a hierarquia de acesso.

### 3.2 Políticas implementadas
- `FIFO`: remove o bloco mais antigo.
- `LRU`: remove o menos recentemente usado.
- `LFU`: remove o menos frequente; em empate, desempata por recência (LRU).

### 3.3 Hierarquia e tempos
- Acesso L1: `1`
- Acesso L2: `1 + 3`
- Acesso L3: `1 + 3 + 6`
- Acesso RAM: `1 + 3 + 6 + 16`

### 3.4 Restrições
- Tamanhos válidos:
  - `1 <= L1 <= 5`
  - `1 <= L2 <= 10`
  - `1 <= L3 <= 50`
  - `L1 <= L2 <= L3`
- Custo:
  - `200*L1 + 50*L2 + 10*L3 <= 1100`

### 3.5 Geração de blocos
- Leitura em pares de 2 caracteres (não sobreposta), conforme enunciado:
  - Ex.: `abcdef` -> `ab`, `cd`, `ef`

## 4. Testes Realizados

### 4.1 Testes funcionais
- Execução de string única.
- Execução de benchmark completo com 3 políticas.
- Execução de padrão único com 3 políticas.
- Geração de relatório de melhor configuração por padrão.

### 4.2 Testes de consistência
- Verificação de fórmula:
  - `taxa_global_faltas = RAM / acessos`
  - `tempo_medio = tempo_total / acessos`
- Verificação de consistência interna:
  - `tempo_total (resumo)` igual à soma dos `tempo_total` das entradas.

### 4.3 Testes de robustez
- Tratamento de entradas inválidas (não alfabéticas, muito curtas).
- Tratamento de configurações inválidas (hierarquia/custo).

## 5. Métricas Obtidas

## 5.1 Métricas avaliadas
- `acessos`
- `hits_L1`, `hits_L2`, `hits_L3`
- `RAM` (faltas globais)
- `taxa_hit_L1`, `taxa_hit_L2`, `taxa_hit_L3`
- `taxa_global_faltas`
- `tempo_total`
- `tempo_medio`
- `ram_tamanho_automatico` (blocos únicos)

### 5.2 Melhor configuração por padrão (vencedor geral)

| Padrão | Política | L1 | L2 | L3 | Custo | Miss Global | Tempo Total | Tempo Médio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Padrão 1 | FIFO | 1 | 5 | 5 | 500 | 0.05 | 1530 | 5.10 |
| Padrão 2 | FIFO | 1 | 1 | 1 | 260 | 1.00 | 7800 | 26.00 |
| Padrão 3 | FIFO | 1 | 10 | 10 | 800 | 0.30 | 3180 | 10.60 |
| Padrão 4 | FIFO | 1 | 10 | 10 | 800 | 0.10 | 1860 | 6.20 |
| Padrão 5 | FIFO | 1 | 1 | 1 | 260 | 1.00 | 7800 | 26.00 |
| Padrão 6 | FIFO | 1 | 1 | 25 | 500 | 0.25 | 4200 | 14.00 |
| Padrão 7 | FIFO | 1 | 5 | 15 | 600 | 0.15 | 2370 | 7.90 |
| Padrão 8 | FIFO | 1 | 5 | 40 | 850 | 0.43 | 4090 | 13.63 |
| Padrão 9 | LRU | 2 | 2 | 2 | 520 | 0.51 | 4125 | 13.75 |
| Padrão 10 | FIFO | 1 | 5 | 5 | 500 | 0.75 | 6150 | 20.50 |

### 5.3 Melhor configuração global no benchmark completo

Critério: menor `tempo_total` (desempate por menor `miss global`).

- Política: **LRU**
- Configuração: **L1=1, L2=10, L3=40**
- Custo: **1100**
- Acessos totais: **3000**
- Miss global: **0.4543**
- Tempo total: **43546**
- Tempo médio: **14.5153**

6. Análise crítica dos resultados

Nos padrões mais “difíceis” (principalmente os muito sequenciais ou quase aleatórios, como os padrões 2 e 5), quase tudo vira falta de cache. Nesses casos, trocar FIFO por LRU ou LFU muda pouco, porque o problema principal é que os blocos não ficam tempo suficiente para serem reaproveitados.

Já nos padrões com repetição e fases mais previsíveis, a cache consegue aproveitar melhor a localidade, e isso reduz bastante o tempo total. Aí o tamanho dos níveis (principalmente L2 e L3) passa a fazer diferença real.

Outro ponto importante: não existe uma política perfeita para todo cenário. Em alguns padrões, FIFO acabou empatando ou até vencendo. Mas quando juntamos tudo (visão global), LRU foi a mais consistente, com melhor resultado final.

Também apareceu um trade-off bem direto: para conseguir o melhor desempenho global, foi preciso usar uma configuração no limite do orçamento. Ou seja, mais desempenho custou mais recursos de memória.

Com base nos experimentos, a recomendação geral para este benchmark foi:
- **LRU com L1=1, L2=10, L3=40** (custo 1100), por apresentar o menor tempo total agregado.
