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
- **Funções:** Limpa tela, mostra menus, ações, resultados de batalha, mods carregados, relatório de patches ativos e falhas de mods.

### `mods/loader.py` — Sistema de Mods
- **Funções:**
    - `load_mods()`: Carrega mods do diretório `mods/`, aplica o `apply()` de cada um e compõe os patches registrados.
    - `register_patch(mod_id, patch_type, target, priority, conflict_policy, patch_fn)`: Registra patch com alvo fully-qualified e metadados obrigatórios.
    - `apply_registered_patches()`: Compõe os patches ativos por alvo.
    - `get_patch_report()`: Retorna relatório dos patches ativos por alvo.
    - `LOADED_MODS`: Dicionário com mods carregados.
    - `FAILED_MODS`: Registro de mods rejeitados ou com erro.
    - `PATCH_REGISTRY`: Tabela indexada por alvo contendo a lista ordenada de patches registrados.

---

## Como Criar e Incorporar um MOD

### 1. Estrutura de um MOD

Você pode criar mods de duas formas:
- **Pacote (pasta com `__init__.py`)**
- **Arquivo único `.py`**

#### Exemplo de MOD simples (`meumod.py`):
```python
from mods.loader import register_patch

PRIORITY = 10


def apply():
    def before_attack(self, who):
        print(f"[meumod] antes de atacar {who}")

    register_patch(
        mod_id="meumod",
        patch_type="before",
        target="libs.battle.BattleSystem.attack",
        priority=PRIORITY,
        conflict_policy="ignore",
        patch_fn=before_attack,
    )
def apply(ctx):
        ctx.log("info", "Meu MOD foi aplicado!")
```

#### Exemplo de `replace` em cadeia explícita:
```python
from mods.loader import register_patch

MOD_INFO = {
    "name": "Meu Mod",
    "PRIORITY": 5,
}


def apply():
    def replace_attack(self, who, next_fn=None):
        print("Executando replace encadeado")
        return next_fn(self, who)

    register_patch(
        mod_id="meu_mod",
        patch_type="replace",
        target="libs.battle.BattleSystem.attack",
        priority=MOD_INFO["PRIORITY"],
        conflict_policy="chain",
        patch_fn=replace_attack,
    )
def apply(ctx):
        ctx.log("info", "Meu MOD pacote foi aplicado!")
```

### 2. Regras de Composição

- **`before`**: executa em ordem crescente de prioridade.
- **`after`**: executa em ordem decrescente de prioridade.
- **`replace`**: é exclusivo por alvo, exceto quando os patches usam `conflict_policy="chain"` e recebem `next_fn` explicitamente.
- Se dois `replace` exclusivos competirem pelo mesmo alvo, o primeiro permanece ativo e o conflito rejeitado é registrado em `FAILED_MODS`.
- O menu de mods mostra um relatório por alvo com os patches ativos e uma seção separada com falhas registradas.

### 3. Como Incorporar um MOD

1. **Coloque seu arquivo `.py` ou pasta de mod dentro do diretório `mods/`.**
2. **Implemente a função obrigatória `apply()`** (executada ao carregar o mod).
3. **Registre patches via `register_patch(...)`**, informando mod, tipo, alvo, prioridade e política de conflito.
4. **Execute o jogo normalmente.** O sistema de mods irá carregar, validar e compor todos os patches automaticamente.
5. **Verifique os mods carregados** pelo menu "Mods", que agora também exibe patches ativos por alvo e falhas.
2. **Implemente a função obrigatória `apply(ctx)`** (executada ao carregar o mod). Mods legados com `apply()` sem argumentos continuam funcionando temporariamente.
3. **(Opcional) Defina a prioridade** usando `PRIORITY` (arquivo simples) ou `MOD_INFO["PRIORITY"]` (pacote).
4. **Execute o jogo normalmente.** O sistema de mods irá carregar e aplicar todos os mods automaticamente.
5. **Verifique os mods carregados** pelo menu "Mods" no jogo.

---

## Observações

- Mods podem alterar qualquer aspecto do jogo, desde que apontem para alvos chamáveis via nome fully-qualified.
- Patches `after` podem retornar um novo resultado; se retornarem `None`, o resultado anterior é preservado.
- Use `conflict_policy="exclusive"` para `replace` isolado e `conflict_policy="chain"` quando o mod aceitar compor com `next_fn`.
- Mods podem alterar qualquer aspecto do jogo, desde que importem e modifiquem variáveis/funções desejadas.
- Use a função `apply(ctx)` para aplicar mudanças ao jogo e acessar hooks, patches, APIs exportadas e estatísticas compartilhadas.
- Mods com prioridade menor são aplicados antes.
