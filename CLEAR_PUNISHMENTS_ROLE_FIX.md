# Alterações de Permissões Separadas para o Comando /limpar-punicoes

## Resumo das Alterações

Foram realizadas alterações para criar permissões separadas para o comando `/limpar-punicoes`, permitindo que apenas membros com cargos específicos de limpeza possam usar este comando, independentemente dos cargos que podem usar os demais comandos de punição.

## Comandos Modificados

### 1. `/limpar-punicoes`
**Problema:** Usava a mesma validação de cargos permitidos que os demais comandos de punição
**Solução:** Alterado para usar uma validação de cargos de limpeza separada

## Arquivos Modificados

### 1. `.env`
**Adicionada nova variável de configuração:**
```env
# IDs dos cargos permitidos para usar o comando /limpar-punicoes (separados por vírgula)
# Substitua pelos IDs dos cargos que podem limpar o histórico de punições
# Ex: 123456789012345678,987654321098765432
CLEAR_PUNISHMENTS_ROLE_IDS=1476431045241999445, 1478135428690219049
```

### 2. `config.py`
**Adicionada nova configuração de cargos de limpeza:**
```python
# IDs dos cargos permitidos para usar o comando /limpar-punicoes (separados por vírgula)
CLEAR_PUNISHMENTS_ROLE_IDS_STR = os.getenv("CLEAR_PUNISHMENTS_ROLE_IDS", "")
CLEAR_PUNISHMENTS_ROLE_IDS: List[int] = []

# Converte a string de IDs para lista de inteiros
if CLEAR_PUNISHMENTS_ROLE_IDS_STR:
    try:
        CLEAR_PUNISHMENTS_ROLE_IDS = [int(role_id.strip()) for role_id in CLEAR_PUNISHMENTS_ROLE_IDS_STR.split(',') if role_id.strip()]
    except ValueError:
        print("⚠️  Aviso: CLEAR_PUNISHMENTS_ROLE_IDS contém valores inválidos. Use IDs numéricos separados por vírgula.")
        CLEAR_PUNISHMENTS_ROLE_IDS = []
```

### 3. `main.py`
**Adicionada nova função de validação de permissões:**
```python
def validate_clear_punishments_permissions(self, user: disnake.Member) -> Tuple[bool, str]:
    """
    Valida se o usuário tem permissão para usar o comando /limpar-punicoes.
    
    Args:
        user: Membro a ser validado
        
    Returns:
        Tuple[bool, str]: (tem_permissão, mensagem_de_erro_ou_sucesso)
    """
    # Se não houver cargos de limpeza configurados, permite qualquer usuário
    if not BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS:
        return True, "Permissão concedida (nenhum cargo de limpeza configurado)"
    
    # Verifica se o usuário tem algum dos cargos de limpeza
    user_role_ids = [role.id for role in user.roles]
    has_permission = any(role_id in BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS for role_id in user_role_ids)
    
    if has_permission:
        return True, "Permissão concedida"
    else:
        # Cria a lista de cargos de limpeza para a mensagem de erro
        clear_roles_mentions = []
        for role_id in BotConfig.PunishmentSystem.CLEAR_PUNISHMENTS_ROLE_IDS:
            role = user.guild.get_role(role_id)
            if role:
                clear_roles_mentions.append(role.mention)
            else:
                clear_roles_mentions.append(f"<@&{role_id}>")
        
        clear_roles_str = ", ".join(clear_roles_mentions) if clear_roles_mentions else "cargos de limpeza configurados"
        
        return False, f"❌ **Acesso Negado!**\nApenas membros com um dos seguintes cargos podem usar este comando:\n{clear_roles_str}"
```

**Modificado o comando `/limpar-punicoes` para usar a nova validação:**
```python
@commands.slash_command(
    name="limpar-punicoes",
    description="Limpa o histórico de punições (Cargos de limpeza apenas)."
)
async def limpar_punicoes(
    self,
    interaction: ApplicationCommandInteraction
):
    """
    Comando slash para limpar o histórico de punições.
    Apenas membros com cargos de limpeza podem usar este comando.
    
    Args:
        interaction: Interação do comando
    """
    # Defer a resposta como efêmera para não poluir o canal
    await interaction.response.defer(ephemeral=True)
    
    # Verifica se o usuário tem permissão para usar este comando (cargos de limpeza)
    has_permission, permission_message = self.validate_clear_punishments_permissions(interaction.author)
    if not has_permission:
        await interaction.followup.send(permission_message, ephemeral=True)
        return
    
    # ... resto do código do comando
```

## Comandos que Agora Têm Permissões Separadas

### Comandos que usam `ALLOWED_ROLES_IDS` (cargos permitidos):
✅ **`/punir`** - Aplica punição em JJ's
✅ **`/solicitar-punicao`** - Solicita punição em JJ's
✅ **`/punicoes`** - Mostra as punições do militar
✅ **`/historico-punicoes`** - Mostra histórico de punições de um usuário específico

### Comandos que usam `CLEAR_PUNISHMENTS_ROLE_IDS` (cargos de limpeza):
✅ **`/limpar-punicoes`** - Limpa o histórico de punições

## Benefícios das Alterações

1. **Segurança:** Permite restringir o comando de limpeza a cargos específicos de alta confiança
2. **Flexibilidade:** Permite configurar diferentes conjuntos de cargos para diferentes funções
3. **Controle:** Evita que membros comuns possam limpar o histórico de punições
4. **Manutenção:** Facilita a gestão de permissões diferentes para funções diferentes

## Configuração de Cargos

### Cargos Permitidos (para comandos de punição)
- **Variável:** `ALLOWED_ROLES_IDS`
- **Comandos:** `/punir`, `/solicitar-punicao`, `/punicoes`, `/historico-punicoes`
- **Uso:** Define quem pode solicitar e aplicar punições

### Cargos de Limpeza (para comando de limpeza)
- **Variável:** `CLEAR_PUNISHMENTS_ROLE_IDS`
- **Comandos:** `/limpar-punicoes`
- **Uso:** Define quem pode limpar o histórico de punições (geralmente cargos de alta hierarquia)

## Exemplo de Configuração

```env
# Cargos que podem usar comandos de punição (ex: Moderadores, Sargentos)
ALLOWED_ROLES_IDS=1476429646697463902, 1476429488249110580, 1478135428690219049

# Cargos que podem limpar o histórico de punições (ex: Comandantes, Administradores)
CLEAR_PUNISHMENTS_ROLE_IDS=1476431045241999445, 1478135428690219049
```

## Resultado Final

Com estas alterações, o comando `/limpar-punicoes` agora tem uma política de permissões separada, permitindo que apenas membros com cargos específicos de limpeza possam usar este comando crítico, enquanto os demais comandos de punição continuam usando a política de cargos permitidos.

## Compatibilidade

As alterações são totalmente compatíveis e não quebram funcionalidades existentes:

- ✅ Mantém fallback para caso nenhum cargo estar configurado
- ✅ Não quebra funcionalidades existentes
- ✅ Melhora a segurança e controle de permissões
- ✅ Mensagens de erro atualizadas para refletir a nova lógica

## Testes Realizados

- **`test_clear_punishments_roles.py`**: Teste completo da nova funcionalidade de permissões separadas
- **`test_limpar_punicoes_roles.py`**: Teste existente atualizado para validar a nova lógica
- **`ROLE_VALIDATION_FIXES.md`**: Documentação das alterações de validação de cargos

As alterações foram implementadas com sucesso, proporcionando maior segurança e controle sobre quem pode limpar o histórico de punições no sistema.