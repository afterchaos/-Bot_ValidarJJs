# Correção do Bug de Imagens em Embeds

## Problema

O bot estava apresentando um bug onde as imagens enviadas pelos usuários para solicitação de punição não carregavam corretamente nos embeds, aparecendo como inválidas ou não sendo exibidas.

## Causa do Problema

O problema estava no uso do protocolo `attachment://` nas URLs das imagens nos embeds. O código estava fazendo:

```python
embed.set_image(url=f"attachment://{valid_attachment.filename}")
```

Esse protocolo é problemático porque:
1. Depende da sincronização perfeita entre o envio do arquivo e a definição da URL no embed
2. Pode falhar em condições de rede ou de carga do Discord
3. Não é confiável para garantir que a imagem será exibida corretamente

## Solução Implementada

A correção consiste em usar a URL direta do anexo enviado pelo bot, em vez do protocolo `attachment://`. O fluxo corrigido é:

1. **Enviar a mensagem com o arquivo**: `sent_message = await canal.send(embed=embed, file=file)`
2. **Obter a URL do anexo enviado**: `attachment_url = sent_message.attachments[0].url`
3. **Atualizar o embed com a URL direta**: `embed.set_image(url=attachment_url)`
4. **Editar a mensagem para garantir a exibição**: `await sent_message.edit(embed=embed)`

## Arquivos Modificados

### `main.py`

Foram corrigidos dois métodos no `PunishmentRequestSystem`:

1. **`process_photo_submission_autonomo`** (linhas ~1000-1050)
2. **`process_photo_submission`** (linhas ~1200-1250)

#### Antes (problemático):
```python
file = await valid_attachment.to_file()
embed.set_image(url=f"attachment://{valid_attachment.filename}")
sent_message = await canal.send(embed=embed, file=file)
```

#### Depois (corrigido):
```python
file = await valid_attachment.to_file()
sent_message = await canal.send(embed=embed, file=file)

if sent_message.attachments:
    attachment_url = sent_message.attachments[0].url
    self.pending_punishments[solicitante.id]["prova_url"] = attachment_url
    embed.set_image(url=attachment_url)
    await sent_message.edit(embed=embed)
else:
    self.pending_punishments[solicitante.id]["prova_url"] = valid_attachment.url
```

## Benefícios da Correção

1. **Confiabilidade**: As imagens agora carregam corretamente na maioria dos casos
2. **Compatibilidade**: Mantém fallback para casos onde o anexo não é encontrado
3. **Performance**: Elimina a dependência do protocolo `attachment://` que era instável
4. **Experiência do Usuário**: Os usuários podem ver claramente a foto que foi enviada

## Testes

Foram criados testes para validar a correção:

- **`test_image_fix_simple.py`**: Testa a lógica de substituição do protocolo `attachment://`
- **`test_image_fix.py`**: Teste mais completo (com emojis, mas com problemas de encoding)

Os testes validam:
- ✅ Substituição correta do protocolo `attachment://`
- ✅ Uso da URL direta do anexo enviado
- ✅ Funcionamento do fallback para casos de erro

## Compatibilidade

A correção é totalmente compatível com:
- ✅ Comandos `/punir` (modo autônomo)
- ✅ Comandos `/solicitar-punicao`
- ✅ Sistema de validação JJ's
- ✅ Armazenamento persistente de URLs de imagens

## Resultado

Com esta correção, as imagens enviadas pelos usuários para solicitação de punição agora são exibidas corretamente nos embeds de confirmação, eliminando o problema de imagens inválidas ou não carregadas.

## Observações

- A correção mantém o mesmo fluxo de trabalho para os usuários
- Não há mudanças na interface ou nos comandos disponíveis
- O fallback garante que o sistema continue funcionando mesmo em casos de erro
- A URL da imagem é armazenada corretamente para uso futuro nos relatórios de punição