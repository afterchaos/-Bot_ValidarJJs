# Sistema de Solicitação de Punição para Discord Bot

Um sistema completo para solicitação de punições em servidores Discord, com validação de foto comprobatória e armazenamento temporário em memória.

## 🚀 Funcionalidades

- **Comando Slash**: `/solicitacao-de-punicao` com validação de parâmetros
- **Validação de Dados**: Impede auto-punição, valida quantidade e motivo
- **Foto Comprobatória**: Sistema de espera por foto com timeout automático
- **Armazenamento Temporário**: Dados armazenados em memória (sem banco de dados)
- **Timeout Automático**: Cancelamento após 5 minutos sem foto
- **Código Modular**: Estrutura organizada e bem documentada
- **Configuração Flexível**: Arquivo de configuração separado

## 📋 Requisitos

- Python 3.8 ou superior
- Biblioteca `disnake`
- Conta de desenvolvedor Discord

## 🔧 Instalação

1. **Clone ou baixe os arquivos:**
   ```bash
   git clone <repositorio>
   cd NovaEra_ESA_BOT
   ```

2. **Instale as dependências:**
   ```bash
   pip install disnake
   ```

3. **Configure o bot:**
   - Crie um bot em [Discord Developer Portal](https://discord.com/developers/applications)
   - Obtenha o token do bot
   - Configure as intents necessárias (Message Content, Members)

4. **Configure as credenciais:**
   Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
   ```env
   # Token do bot (obrigatório) - Obtenha em: https://discord.com/developers/applications
   DISCORD_BOT_TOKEN=SEU_TOKEN_AQUI
   
   # IDs dos servidores de teste (para comandos slash) - Separe por vírgula se houver mais de um
   TEST_GUILD_IDS=123456789
   ```
   
   **⚠️ Importante:** Nunca compartilhe seu token do Discord. O arquivo `.env` deve ser mantido em segredo e não deve ser enviado para repositórios públicos.

## ⚙️ Configuração

### Arquivo `config.py`

```python
class BotConfig:
    # Token do bot (obrigatório)
    BOT_TOKEN = "SEU_TOKEN_AQUI"
    
    # IDs dos servidores de teste
    TEST_GUILDS = [123456789]
    
    class PunishmentSystem:
        TIMEOUT_MINUTES = 5          # Tempo para enviar foto
        MAX_QUANTITY = 10000         # Quantidade máxima de JJ's
        MIN_QUANTITY = 1             # Quantidade mínima de JJ's
        MIN_MOTIVO_LENGTH = 5        # Tamanho mínimo do motivo
```

### Configurações do Sistema

As configurações podem ser personalizadas no arquivo `.env`:

- **Timeout**: Tempo máximo para envio da foto (padrão: 5 minutos)
- **Quantidade Máxima**: Limite de JJ's por solicitação (padrão: 10.000)
- **Quantidade Mínima**: Mínimo de JJ's por solicitação (padrão: 1)
- **Tamanho do Motivo**: Mínimo de caracteres no campo motivo (padrão: 5)

#### Variáveis de Ambiente Disponíveis

```env
# Token do bot (obrigatório)
DISCORD_BOT_TOKEN=SEU_TOKEN_AQUI

# IDs dos servidores de teste (para comandos slash)
TEST_GUILD_IDS=123456789,987654321

# Configurações do sistema de punição
TIMEOUT_MINUTES=5
MAX_QUANTITY=10000
MIN_QUANTITY=1
MIN_MOTIVO_LENGTH=5

# Configurações de logging
LOG_LEVEL=INFO
LOG_FILE=
```

## 🎮 Uso

### Comando Slash

```
/solicitacao-de-punicao
  punido: @usuário
  quantidade: 10
  motivo: Descumprimento de ordem
```

### Fluxo da Solicitação

1. **Execução do Comando**: O militar executa `/solicitacao-de-punicao`
2. **Validação**: O bot valida os parâmetros (auto-punição, quantidade, motivo)
3. **Embed de Confirmação**: O bot envia uma embed com os detalhes da solicitação
4. **Instruções**: O bot instrui o solicitante a enviar a foto comprobatória
5. **Modo de Espera**: O bot entra em modo de espera aguardando a foto
6. **Validação da Foto**: O bot valida se o anexo é uma imagem válida
7. **Processamento**: Se válida, a foto é processada e a solicitação concluída
8. **Timeout**: Se não houver foto em 5 minutos, a solicitação é cancelada

### Regras de Validação

- **Auto-punição**: Não é permitido punir a si mesmo
- **Quantidade**: Deve ser maior que 0 e menor que o limite máximo
- **Motivo**: Deve ter pelo menos 5 caracteres
- **Foto**: Deve ser um arquivo de imagem válido (PNG, JPG, GIF, etc.)
- **Canal**: A foto deve ser enviada no mesmo canal da solicitação
- **Solicitante**: Apenas quem fez a solicitação pode enviar a foto

## 📁 Estrutura de Arquivos

```
NovaEra_ESA_BOT/
├── main.py          # Código principal do bot
├── config.py        # Configurações do sistema
├── README.md        # Este arquivo
└── requirements.txt # Dependências (opcional)
```

## 🚀 Execução

```bash
python main.py
```

## 📝 Exemplos de Uso

### Solicitação Válida
```
/solicitacao-de-punicao
  punido: @soldado123
  quantidade: 50
  motivo: Atraso no serviço
```

### Resposta do Bot
```
✅ Dados válidos
📸 @solicitante, por favor envie a foto comprobatória neste canal.
```

### Foto Enviada
```
✅ FOTO RECEBIDA COM SUCESSO
📸 Arquivo: comprovante.jpg (1.2 MB)
```

### Timeout
```
❌ SOLICITAÇÃO CANCELADA
Motivo: Tempo limite expirado
```

## 🔍 Validação de Imagens

O sistema aceita os seguintes formatos:
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)
- TIFF (.tiff)

## 🛠️ Personalização

### Alterar Tempo de Timeout
```python
# Em config.py
TIMEOUT_MINUTES = 10  # 10 minutos
```

### Alterar Limites de Quantidade
```python
# Em config.py
MAX_QUANTITY = 5000   # Máximo 5.000 JJ's
MIN_QUANTITY = 5      # Mínimo 5 JJ's
```

### Alterar Tamanho do Motivo
```python
# Em config.py
MIN_MOTIVO_LENGTH = 10  # Mínimo 10 caracteres
```

## 🐛 Solução de Problemas

### Token Inválido
```
❌ Token inválido. Por favor, verifique seu token do Discord.
```
**Solução**: Verifique se o `DISCORD_BOT_TOKEN` está correto no arquivo `.env`

### Comandos Não Aparecem
```
⚠️ IDs de servidores de teste não configurados
```
**Solução**: Atualize `TEST_GUILD_IDS` no arquivo `.env` com o ID do seu servidor

### Comandos Não Aparecem
```
⚠️ IDs de servidores de teste não configurados
```
**Solução**: Atualize `TEST_GUILDS` em `config.py` com o ID do seu servidor

### Foto Não Aceita
```
❌ A foto enviada não é válida
```
**Solução**: Envie uma imagem em formato suportado (PNG, JPG, GIF, etc.)

## 📚 Documentação do Código

### Principais Classes

- **`PunishmentRequestSystem`**: Sistema principal de solicitação de punição
- **`Bot`**: Bot principal que gerencia os comandos e eventos

### Principais Métodos

- **`validate_punishment_data()`**: Valida os parâmetros da solicitação
- **`create_punishment_embed()`**: Cria embeds formatadas
- **`wait_for_photo()`**: Aguarda o envio da foto com timeout
- **`is_valid_image_attachment()`**: Valida arquivos de imagem

## 🤝 Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Faça commit das alterações
4. Abra um pull request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- Comunidade Discord Developers
- Equipe disnake
- Todos que contribuíram com testes e feedback

## 🔒 Segurança

Este projeto utiliza variáveis de ambiente para armazenar credenciais sensíveis. Para maior segurança:

1. **Nunca compartilhe seu arquivo `.env`**
2. **Adicione `.env` ao seu `.gitignore`** para evitar commits acidentais
3. **Use tokens de bot com permissões mínimas necessárias**
4. **Revogue tokens periodicamente** para manter a segurança

---

**⚠️ Importante**: Este sistema é destinado apenas para uso em servidores Discord autorizados. Certifique-se de seguir as diretrizes da comunidade e obter as permissões necessárias antes de implementar.
