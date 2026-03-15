# Jogo Goblin

Um jogo de batalha por turnos em Python, onde o jogador enfrenta um goblin controlado por IA. O sistema suporta mods para personalização e expansão.

---

## Como o Jogo Funciona

- **Objetivo:** Derrote o goblin inimigo em batalhas por turnos.
- **Turnos:** O jogador e o goblin alternam turnos. Cada um pode atacar, defender ou usar uma poção.
- **Ações disponíveis:**
    - **Atacar:** Causa dano ao inimigo.
    - **Defender:** Tenta reduzir o dano recebido no próximo ataque.
    - **Usar Poção:** Recupera vida (50 pontos), limitado ao número de poções disponíveis.
- **Condições de vitória:** O jogo termina quando a vida de um dos participantes chega a zero. O vencedor é anunciado.

---

## Bibliotecas do Projeto

### `libs/battle.py` — Sistema de Batalha
- **Classe:** `BattleSystem`
- **Principais variáveis:** 
    - `battle`: Instância de `BattleState` (estado atual da batalha).
- **Funções:**
    - `new_battle()`: Inicia uma nova batalha.
    - `use_potion(who)`: Usa uma poção para o jogador (`'pl'`) ou inimigo (`'en'`).
    - `cur_stats(who)`: Retorna vida e poções do participante.
    - `all_stats()`: Retorna todos os atributos relevantes.
    - `defend(who)`: Executa ação de defesa.
    - `attack(who)`: Executa ataque.
    - `next_round()`: Alterna o turno.

### `libs/variables.py` — Estado da Batalha
- **Classe:** `BattleState`
- **Principais variáveis:**
    - `ATK_PL`, `ATK_EN`: Ataque do jogador/inimigo.
    - `DEF_PL`, `DEF_EN`: Defesa do jogador/inimigo.
    - `HL_PL`, `HL_EN`: Vida atual.
    - `POTIONS_PL`, `POTIONS_EN`: Poções disponíveis.
    - `POTION_HEAL_AMOUNT`: Valor de cura da poção.
    - `PLAYER_MAX_HP`, `ENEMY_MAX_HP`: Vida máxima.
    - `IS_WON`, `WHO_WON`: Controle de vitória.
    - `CUR_ROUND`: Turno atual.

### `libs/goblin_ai.py` — IA do Goblin
- **Classe:** `Goblin`
- **Principais variáveis:** 
    - `LOCAL_HEALTH`, `LOCAL_POTIONS`: Vida e poções do goblin.
- **Funções:**
    - `upd_stats(stats)`: Atualiza vida/poções.
    - `mk_choice()`: Decide ação do goblin.

### `libs/ui.py` — Interface de Usuário
- **Classe:** `UI_Renderer`
- **Funções:** Limpa tela, mostra menus, ações, resultados de batalha, mods carregados, etc.

### `mods/loader.py` — Sistema de Mods
- **Funções:**
    - `load_mods()`: Carrega e aplica mods do diretório `mods/`.
    - `LOADED_MODS`: Dicionário com mods carregados.

---

## Como Criar e Incorporar um MOD

### 1. Estrutura de um MOD

Você pode criar mods de duas formas:
- **Pacote (pasta com `__init__.py`)**
- **Arquivo único `.py`**

#### Exemplo de MOD simples (`meumod.py`):
```python
PRIORITY = 10  # Opcional, define a ordem de carregamento

def apply():
        print("Meu MOD foi aplicado!")
```

#### Exemplo de MOD pacote:
```
mods/
└── meu_mod/
        └── __init__.py
```
No `__init__.py`:
```python
MOD_INFO = {
        "name": "Meu Mod",
        "PRIORITY": 5
}

def apply():
        print("Meu MOD pacote foi aplicado!")
```

### 2. Como Incorporar um MOD

1. **Coloque seu arquivo `.py` ou pasta de mod dentro do diretório `mods/`.**
2. **Implemente a função obrigatória `apply()`** (executada ao carregar o mod).
3. **(Opcional) Defina a prioridade** usando `PRIORITY` (arquivo simples) ou `MOD_INFO["PRIORITY"]` (pacote).
4. **Execute o jogo normalmente.** O sistema de mods irá carregar e aplicar todos os mods automaticamente.
5. **Verifique os mods carregados** pelo menu "Mods" no jogo.

---

## Observações

- Mods podem alterar qualquer aspecto do jogo, desde que importem e modifiquem variáveis/funções desejadas.
- Use a função `apply()` para aplicar mudanças ao jogo.
- Mods com prioridade menor são aplicados antes.
