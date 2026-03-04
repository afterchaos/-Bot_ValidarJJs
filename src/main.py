import asyncio
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

import disnake
from disnake.ext import commands, tasks
from disnake import ApplicationCommandInteraction, Embed, Color, File
from disnake.enums import ButtonStyle, ActivityType
from disnake.ui import Button, View

# Adiciona o diretório atual ao Python path para permitir imports relativos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.utils.config import BotConfig, validate_config
from src.utils.data_manager import data_manager
from src.cogs.jj_validation_system import JJValidationSystem


class PunishmentReviewView(View):
    """
    View com botões interativos para aceitar ou recusar uma solicitação de punição.
    """
    def __init__(self, role_ids: List[int]):
        super().__init__(timeout=None)
        self.role_ids = role_ids
        
    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        """Verifica se o usuário tem algum dos cargos necessários para interagir."""
        # Se não houver cargos configurados, permite qualquer pessoa interagir
        if not self.role_ids:
            return True
             
        # Verifica se o usuário tem algum dos cargos responsáveis
        user_role_ids = [role.id for role in interaction.author.roles]
        has_permission = any(role_id in user_role_ids for role_id in self.role_ids)
        
        if has_permission:
            return True
            
        # Se não tiver nenhum cargo, envia mensagem de erro e bloqueia a interação
        role_mentions = []
        for role_id in self.role_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                role_mentions.append(role.mention)
            else:
                role_mentions.append(f"<@&{role_id}>")
        
        roles_str = ", ".join(role_mentions) if role_mentions else "cargos configurados"
        await interaction.response.send_message(
            f"❌ **Acesso Negado!**\nApenas membros com um dos seguintes cargos podem aprovar ou recusar solicitações:\n{roles_str}", 
            ephemeral=True
        )
        return False
        
    @disnake.ui.button(label="Aceitar", style=ButtonStyle.success, emoji="✅")
    async def accept(self, button: Button, interaction: disnake.MessageInteraction):
        # Obtém o cog do bot para acessar os métodos de registro
        cog = interaction.bot.get_cog("PunishmentRequestSystem")
        if cog:
            await cog.approve_punishment(interaction)
        else:
            await interaction.response.send_message("Erro ao processar aprovação.", ephemeral=True)
        
    @disnake.ui.button(label="Recusar", style=ButtonStyle.danger, emoji="❌")
    async def reject(self, button: Button, interaction: disnake.MessageInteraction):
        # Abre o modal para digitar o motivo da recusa
        modal = PunishmentRejectionModal()
        await interaction.response.send_modal(modal)


class PunishmentRejectionModal(disnake.ui.Modal):
    """
    Modal para digitar o motivo da recusa de punição.
    """
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Motivo da Recusa",
                placeholder="Digite o motivo da recusa...",
                custom_id="rejection_reason",
                style=disnake.TextInputStyle.paragraph,
                min_length=10,
                max_length=500
            )
        ]
        super().__init__(
            title="Motivo da Recusa",
            custom_id="punishment_rejection_modal",
            components=components
        )
    
    async def callback(self, interaction: disnake.ModalInteraction):
        """Processa o motivo da recusa quando o modal é enviado."""
        # Obtém o motivo digitado
        rejection_reason = interaction.text_values["rejection_reason"]
        
        # Obtém o cog do bot para acessar os métodos de registro
        cog = interaction.bot.get_cog("PunishmentRequestSystem")
        if cog:
            await cog.reject_punishment_with_reason(interaction, rejection_reason)
        else:
            await interaction.response.send_message("Erro ao processar recusa.", ephemeral=True)


class PunishmentPunishmentsView(View):
    """
    View com botões interativos para cumprir punições.
    """
    def __init__(self, user_id: int, punishment_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.punishment_id = punishment_id
        
    @disnake.ui.button(label="CUMPRIR PUNIÇÃO", style=ButtonStyle.danger, emoji="⚡")
    async def fulfill_punishment(self, button: Button, interaction: disnake.MessageInteraction):
        # Obtém o cog do bot para acessar os métodos de registro
        cog = interaction.bot.get_cog("PunishmentRequestSystem")
        if cog:
            await cog.fulfill_punishment(interaction, self.user_id, self.punishment_id)
        else:
            await interaction.response.send_message("Erro ao processar cumprimento de punição.", ephemeral=True)


class PunishmentRequestSystem(commands.Cog):
    """
    Sistema de Solicitação de Punição
    
    Gerencia solicitações de punição com validação de foto comprobatória.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dicionário global para armazenar estados temporários
        # Estrutura: {user_id: {solicitante, punido, quantidade, motivo, status, canal, criado_em}}
        self.pending_punishments: Dict[int, Dict] = {}
        
        # Banco de dados de punições (simulação)
        # Estrutura: {id: {solicitante, punido, quantidade, motivo, permissao, status, data}}
        self.punishments_db: Dict[int, Dict] = {}
        self.punishment_counter = 1
        
        # Configurações do sistema (importadas do config.py)
        self.TIMEOUT_MINUTES = BotConfig.PunishmentSystem.TIMEOUT_MINUTES
        self.MAX_QUANTITY = BotConfig.PunishmentSystem.MAX_QUANTITY
        self.MIN_QUANTITY = BotConfig.PunishmentSystem.MIN_QUANTITY
        self.MIN_MOTIVO_LENGTH = BotConfig.PunishmentSystem.MIN_MOTIVO_LENGTH
        self.VALID_IMAGE_TYPES = BotConfig.PunishmentSystem.VALID_IMAGE_TYPES
        self.VALID_IMAGE_EXTENSIONS = BotConfig.PunishmentSystem.VALID_IMAGE_EXTENSIONS
        self.RESPONSIBLE_ROLE_ID = BotConfig.PunishmentSystem.RESPONSIBLE_ROLE_ID
        self.PUNISHMENTS_CHANNEL_ID = BotConfig.PunishmentSystem.PUNISHMENTS_CHANNEL_ID
        self.REQUESTS_CHANNEL_ID = BotConfig.PunishmentSystem.REQUESTS_CHANNEL_ID
        self.APPROVAL_CHANNEL_ID = BotConfig.PunishmentSystem.APPROVAL_CHANNEL_ID
        
        # Configura o logger
        self.logger = logging.getLogger(__name__)
        
        # Carrega dados persistentes
        self.load_persistent_data()
    
    def load_persistent_data(self):
        """
        Carrega dados persistentes de punições e estados temporários.
        """
        try:
            # Carrega punições persistentes
            self.punishments_db, self.punishment_counter = data_manager.load_punishments()
            self.logger.info(f"Dados persistentes carregados: {len(self.punishments_db)} punições, próximo ID: {self.punishment_counter}")
            
            # Carrega estados temporários (geralmente vazio no início)
            self.pending_punishments = data_manager.load_pending_punishments()
            self.logger.info(f"Estados temporários carregados: {len(self.pending_punishments)} registros")
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados persistentes: {e}")
            # Inicializa com valores padrão em caso de erro
            self.punishments_db = {}
            self.punishment_counter = 1
            self.pending_punishments = {}
    
    def save_punishments_persistent(self):
        """
        Salva as punições no armazenamento persistente.
        Garante que não sobrescreva alterações feitas por outros módulos.
        """
        try:
            # Recarrega do disco para pegar alterações de outros módulos (ex: JJValidationSystem)
            punishments_disk, counter_disk = data_manager.load_punishments()
            
            # Mescla as punições da memória com as do disco
            # As da memória (self.punishments_db) têm prioridade para punições novas ou alteradas aqui
            for pid, pdata in self.punishments_db.items():
                punishments_disk[pid] = pdata
            
            # Atualiza o contador se o da memória for maior
            final_counter = max(self.punishment_counter, counter_disk)
            
            data_manager.save_punishments(punishments_disk, final_counter)
            
            # Atualiza a memória com os dados mesclados
            self.punishments_db = punishments_disk
            self.punishment_counter = final_counter
            
            self.logger.info(f"Dados persistentes salvos e sincronizados: {len(self.punishments_db)} punições")
        except Exception as e:
            self.logger.error(f"Erro ao salvar punições persistentes: {e}")
    
    def save_pending_punishments_persistent(self):
        """
        Salva os estados temporários no armazenamento persistente.
        """
        try:
            data_manager.save_pending_punishments(self.pending_punishments)
            self.logger.info(f"Estados temporários salvos: {len(self.pending_punishments)} registros")
        except Exception as e:
            self.logger.error(f"Erro ao salvar estados temporários: {e}")
    
    def backup_punishments(self) -> str:
        """
        Cria um backup das punições.
        
        Returns:
            str: Caminho do arquivo de backup criado
        """
        try:
            backup_file = data_manager.backup_punishments()
            self.logger.info(f"Backup criado: {backup_file}")
            return backup_file
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {e}")
            return ""
    
    def get_punishment_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas sobre as punições armazenadas.
        
        Returns:
            Dict: Estatísticas sobre as punições
        """
        try:
            stats = data_manager.get_statistics()
            self.logger.info(f"Estatísticas obtidas: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
        
    def validate_punishment_data(self, solicitante_id: int, punido_id: int, quantidade: int, motivo: str) -> Tuple[bool, str]:
        """
        Valida os dados da solicitação de punição.
        
        Args:
            solicitante_id: ID do usuário que está solicitando a punição
            punido_id: ID do usuário que será punido
            quantidade: Quantidade de JJ's a serem aplicados
            motivo: Motivo da punição
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_de_erro_ou_sucesso)
        """
        # Validar quantidade
        if quantidade < self.MIN_QUANTITY:
            return False, f"A quantidade de JJ's deve ser maior ou igual a {self.MIN_QUANTITY}."
            
        if quantidade > self.MAX_QUANTITY:
            return False, f"A quantidade máxima permitida é {self.MAX_QUANTITY} JJ's."
        
        # Validar motivo
        if not motivo or len(motivo.strip()) < self.MIN_MOTIVO_LENGTH:
            return False, f"O motivo deve ter pelo menos {self.MIN_MOTIVO_LENGTH} caracteres."
            
        return True, "Dados válidos"
    
    def validate_user_permissions(self, user: disnake.Member) -> Tuple[bool, str]:
        """
        Valida se o usuário tem permissão para usar os comandos de punição.
        
        Args:
            user: Membro a ser validado
            
        Returns:
            Tuple[bool, str]: (tem_permissão, mensagem_de_erro_ou_sucesso)
        """
        # Se não houver cargos permitidos configurados, permite qualquer usuário
        if not BotConfig.PunishmentSystem.ALLOWED_ROLES_IDS:
            return True, "Permissão concedida (nenhum cargo configurado)"
        
        # Verifica se o usuário tem algum dos cargos permitidos
        user_role_ids = [role.id for role in user.roles]
        has_permission = any(role_id in BotConfig.PunishmentSystem.ALLOWED_ROLES_IDS for role_id in user_role_ids)
        
        if has_permission:
            return True, "Permissão concedida"
        else:
            # Cria a lista de cargos permitidos para a mensagem de erro
            allowed_roles_mentions = []
            for role_id in BotConfig.PunishmentSystem.ALLOWED_ROLES_IDS:
                role = user.guild.get_role(role_id)
                if role:
                    allowed_roles_mentions.append(str(role.mention))
                else:
                    allowed_roles_mentions.append(f"<@&{role_id}>")
            
            allowed_roles_str = ", ".join(allowed_roles_mentions) if allowed_roles_mentions else "cargos configurados"
            
            return False, f"❌ **Acesso Negado!**\nApenas membros com um dos seguintes cargos podem usar este comando:\n{allowed_roles_str}"
    
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
                # Para testes, se o role_id for um Mock, usa o atributo mention
                if hasattr(role_id, 'mention'):
                    clear_roles_mentions.append(str(role_id.mention))
                else:
                    # Para produção, tenta obter o cargo do guild
                    role = user.guild.get_role(role_id)
                    if role:
                        clear_roles_mentions.append(str(role.mention))
                    else:
                        clear_roles_mentions.append(f"<@&{role_id}>")

            # Se não houver cargos válidos, usa fallback
            clear_roles_str = ", ".join(clear_roles_mentions) if clear_roles_mentions else "nenhum cargo configurado"
            
            return False, f"❌ **Acesso Negado!**\nApenas membros com um dos seguintes cargos podem usar este comando: cargos de limpeza configurados\n{clear_roles_str}"
    
    def create_punishment_embed(self, solicitante: disnake.Member, punido: disnake.Member, 
                              quantidade: int, motivo: str, status: str) -> Embed:
        """
        Cria uma embed formatada com os detalhes da solicitação de punição.
        
        Args:
            solicitante: Membro que solicitou a punição
            punido: Membro que será punido
            quantidade: Quantidade de JJ's
            motivo: Motivo da punição
            status: Status atual da solicitação
            
        Returns:
            Embed: Embed formatada com os detalhes
        """
        embed = Embed(
            title="Solicitação de Punição",
            description="Detalhes da solicitação enviada:",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Solicitante",
            value=f"{solicitante.mention}\n`{solicitante.name}`",
            inline=True
        )
        
        embed.add_field(
            name="Punido",
            value=f"{punido.mention}\n`{punido.name}`",
            inline=True
        )
        
        embed.add_field(
            name="Quantidade",
            value=f"**{quantidade} JJ's**",
            inline=True
        )
        
        embed.add_field(
            name="Motivo",
            value=f"```\n{motivo}\n```",
            inline=False
        )
        
        embed.add_field(
            name="Status Atual",
            value=status,
            inline=False
        )
        
        embed.set_footer(
            text=f"ID Solicitante: {solicitante.id} • Expira em {self.TIMEOUT_MINUTES}m"
        )
        
        self.logger.info(f"Solicitação de punição criada - Solicitante: {solicitante.id}, Punido: {punido.id}")
        
        return embed
    
    def create_report_embed(self, data: Dict) -> Embed:
        """
        Gera um relatório final da solicitação de punição.
        """
        solicitante = self.bot.get_user(data["solicitante"])
        punido = self.bot.get_user(data["punido"])
        
        # Obtém o cargo responsável para incluir na embed
        cargo_responsavel = None
        if BotConfig.PunishmentSystem.RESPONSIBLE_ROLE_ID != 0:
            cargo_responsavel = f"<@&{BotConfig.PunishmentSystem.RESPONSIBLE_ROLE_ID}>"
        
        embed = Embed(
            title="Solicitação de Punição!",
            description="Detalhes da solicitação enviada para análise:",
            color=Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Nome:",
            value=solicitante.mention if solicitante else f"ID: {data['solicitante']}",
            inline=True
        )
        
        embed.add_field(
            name="Punido:",
            value=punido.mention if punido else f"ID: {data['punido']}",
            inline=True
        )
        
        embed.add_field(
            name="Quantidade:",
            value=f"**{data['quantidade']} JJ's**",
            inline=True
        )
        
        embed.add_field(
            name="Motivo:",
            value=f"```\n{data['motivo']}\n```",
            inline=False
        )
        
        embed.add_field(
            name="Data/Hora:",
            value=f"<t:{int(data['criado_em'])}:F>",
            inline=True
        )
        
        if cargo_responsavel:
            embed.add_field(
                name="Menção do cargo responsável:",
                value=cargo_responsavel,
                inline=True
            )
        
        if "prova_url" in data:
            # Usa a URL da foto como imagem principal para melhor visualização da prova
            embed.set_image(url=data["prova_url"])
            
        # Adiciona o ID da punição no rodapé para rastreamento
        punishment_id = data.get("punishment_id", "Desconhecido")
        embed.set_footer(text=f"ID Punição: {punishment_id} • Status: Em Análise • Solicitante: {data['solicitante']}")
        
        return embed

    def is_valid_image_attachment(self, attachment: disnake.Attachment) -> bool:
        """
        Verifica se o anexo é uma imagem válida.
        
        Args:
            attachment: Anexo a ser validado
            
        Returns:
            bool: True se for imagem válida, False caso contrário
        """
        # Tipos de arquivos de imagem comuns
        valid_image_types = [
            'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
            'image/webp', 'image/bmp', 'image/tiff'
        ]
        
        # Verifica o tipo MIME
        if attachment.content_type not in self.VALID_IMAGE_TYPES:
            return False
        
        # Verifica a extensão do arquivo
        filename_lower = attachment.filename.lower()
        if not any(filename_lower.endswith(ext) for ext in self.VALID_IMAGE_EXTENSIONS):
            return False
            
        return True
    
    @commands.slash_command(
        name="punir",
        description="Aplica punição em JJ's para um militar (com foto comprobatória)."
    )
    async def punir_autonomo(
        self,
        interaction: ApplicationCommandInteraction,
        punido: disnake.Member,
        quantidade: int,
        motivo: str
    ):
        """
        Comando slash para aplicar punição de forma autônoma.
        
        Args:
            interaction: Interação do comando
            punido: Usuário a ser punido
            quantidade: Quantidade de JJ's
            motivo: Motivo da punição
        """
        # Defer a resposta como efêmera para não poluir o canal
        await interaction.response.defer(ephemeral=True)
        
        # Valida permissões do usuário
        has_permission, permission_message = self.validate_user_permissions(interaction.author)
        if not has_permission:
            await interaction.followup.send(permission_message, ephemeral=True)
            return
        
        # Valida os dados da punição
        is_valid, message = self.validate_punishment_data(
            interaction.author.id, 
            punido.id, 
            quantidade, 
            motivo
        )
        
        if not is_valid:
            await interaction.followup.send(message, ephemeral=True)
            return
        
        # Cria o registro da punição no dicionário
        timestamp = time.time()
        self.pending_punishments[interaction.author.id] = {
            "solicitante": interaction.author.id,
            "punido": punido.id,
            "quantidade": quantidade,
            "motivo": motivo,
            "status": "aguardando_foto",
            "canal": interaction.channel.id,
            "criado_em": timestamp
        }
        
        # Cria e envia a embed com os detalhes (efêmera)
        embed = self.create_punishment_embed(
            interaction.author, 
            punido, 
            quantidade, 
            motivo, 
            "Aguardando envio da foto comprobatória."
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Envia instruções para o usuário (efêmera)
        instructions = (
            f"**{interaction.author.mention}**, por favor envie a foto comprobatória neste canal.\n\n"
            f"**Importante:**\n"
            f"- Apenas você pode enviar a foto para esta punição;\n"
            f"- O arquivo deve ser uma imagem válida (PNG, JPG, etc.);\n"
            f"- Você tem **{self.TIMEOUT_MINUTES} minutos** para enviar a foto;\n"
            f"- Caso não envie, a punição será cancelada."
        )
        
        self.logger.info(f"Instruções enviadas para {interaction.author.id} no canal {interaction.channel.id}")
        
        await interaction.followup.send(instructions, ephemeral=True)
        
        # Inicia o processo de espera pela foto
        await self.wait_for_photo_autonomo(interaction.author, interaction.channel)
    
    async def wait_for_photo_autonomo(self, solicitante: disnake.Member, canal: disnake.TextChannel):
        """
        Aguarda o envio da foto comprobatória com timeout para punição autônoma.
        
        Args:
            solicitante: Membro que deve enviar a foto
            canal: Canal onde a foto deve ser enviada
        """
        def check_message(message: disnake.Message) -> bool:
            """Verifica se a mensagem atende aos critérios para ser considerada válida."""
            # Verifica se é do solicitante
            if message.author.id != solicitante.id:
                return False
            
            # Verifica se é no mesmo canal
            if message.channel.id != canal.id:
                return False
            
            # Verifica se tem anexos
            if not message.attachments:
                return False
            
            # Verifica se o anexo é uma imagem válida
            for attachment in message.attachments:
                if self.is_valid_image_attachment(attachment):
                    return True
            
            return False
        
        try:
            # Aguarda até 5 minutos por uma mensagem válida
            timeout_seconds = self.TIMEOUT_MINUTES * 60
            message = await self.bot.wait_for(
                'message', 
                check=check_message, 
                timeout=timeout_seconds
            )
            
            # Processa a foto enviada
            await self.process_photo_submission_autonomo(solicitante, canal, message)
            
        except asyncio.TimeoutError:
            # Timeout expirado - cancela a solicitação
            await self.cancel_punishment_request(solicitante, canal, "Tempo limite expirado")
            self.logger.warning(f"Timeout expirado para punição autônoma de {solicitante.id}")
    
    async def process_photo_submission_autonomo(self, solicitante: disnake.Member, canal: disnake.TextChannel, 
                                               message: disnake.Message):
        """
        Processa a foto enviada pelo usuário e avança para a etapa de confirmação para punição autônoma.
        
        Args:
            solicitante: Membro que enviou a foto
            canal: Canal onde a foto foi enviada
            message: Mensagem contendo a foto
        """
        # Encontra a imagem válida
        valid_attachment = None
        for attachment in message.attachments:
            if self.is_valid_image_attachment(attachment):
                valid_attachment = attachment
                break
        
        self.logger.info(f"Foto recebida de {solicitante.id} para punição autônoma: {valid_attachment.filename if valid_attachment else 'Nenhuma imagem válida'}")
        
        if not valid_attachment:
            await canal.send(f"{solicitante.mention}, a foto enviada não é válida. Punição cancelada.")
            if solicitante.id in self.pending_punishments:
                del self.pending_punishments[solicitante.id]
            return
        
        # Cria embed de confirmação de recebimento
        embed = Embed(
            title="Foto Recebida",
            description="A foto comprobatória foi validada com sucesso.",
            color=Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Arquivo",
            value=f"`{valid_attachment.filename}`",
            inline=True
        )
        
        embed.add_field(
            name="Solicitante",
            value=solicitante.mention,
            inline=True
        )
        
        # Adiciona a foto ao embed e prepara o arquivo
        file = await valid_attachment.to_file()
        
        # Envia a confirmação com o arquivo e solicita a confirmação manual
        sent_message = await canal.send(embed=embed, file=file)
        
        # Atualiza o estado com a URL da foto (agora do canal do bot, mais estável) e altera status
        if solicitante.id in self.pending_punishments:
            # Pega a URL do anexo da mensagem que o bot acabou de enviar
            if sent_message.attachments:
                # Usa a URL do anexo enviado para garantir que a imagem carregue corretamente
                attachment_url = sent_message.attachments[0].url
                self.pending_punishments[solicitante.id]["prova_url"] = attachment_url
                # Atualiza o embed para usar a URL direta do anexo enviado
                embed.set_image(url=attachment_url)
                # Edita a mensagem para garantir que a imagem seja exibida corretamente
                await sent_message.edit(embed=embed)
            else:
                # Fallback caso ocorra erro no anexo da nova mensagem
                self.pending_punishments[solicitante.id]["prova_url"] = valid_attachment.url
                
            self.pending_punishments[solicitante.id]["status"] = "aguardando_confirmacao"
        
        # Aguarda 2 segundos para garantir que a foto seja processada antes de apagar
        await asyncio.sleep(2)
        
        # Apaga a mensagem original que contém a foto
        try:
            await message.delete()
            self.logger.info(f"Foto apagada da mensagem {message.id} enviada por {solicitante.id}")
        except disnake.NotFound:
            self.logger.warning(f"Mensagem {message.id} já foi apagada")
        except disnake.Forbidden:
            self.logger.warning(f"Sem permissão para apagar a mensagem {message.id}")
        except Exception as e:
            self.logger.error(f"Erro ao apagar a mensagem {message.id}: {e}")
        
        confirmation_msg = (
            f"**{solicitante.mention}**, para finalizar e aplicar a punição, "
            f"digite uma das palavras abaixo neste canal: "
            f"`confirmar`, `enviar` ou `ok`"
        )
        
        await canal.send(confirmation_msg)
        
        # Inicia o processo de espera pela confirmação manual
        await self.wait_for_confirmation_autonomo(solicitante, canal)
    
    async def wait_for_confirmation_autonomo(self, solicitante: disnake.Member, canal: disnake.TextChannel):
        """
        Aguarda a confirmação manual do usuário por mensagem para punição autônoma.
        """
        def check_confirmation(message: disnake.Message) -> bool:
            # Verifica se é do solicitante no mesmo canal
            if message.author.id != solicitante.id or message.channel.id != canal.id:
                return False
            
            # Verifica se o status ainda é aguardando_confirmacao
            if solicitante.id not in self.pending_punishments or \
               self.pending_punishments[solicitante.id]["status"] != "aguardando_confirmacao":
                return False
            
            # Verifica as palavras-chave (case-insensitive)
            valid_words = ["confirmar", "enviar", "ok"]
            return message.content.lower().strip() in valid_words

        try:
            # Aguarda 5 minutos para a confirmação manual
            timeout_seconds = self.TIMEOUT_MINUTES * 60
            await self.bot.wait_for('message', check=check_confirmation, timeout=timeout_seconds)
            
            # Se chegou aqui, o usuário confirmou
            data = self.pending_punishments[solicitante.id]
            
            # Registra a punição no banco de dados
            punishment_id = self.punishment_counter
            self.punishment_counter += 1
            
            # Cria registro da punição
            punishment_data = {
                "id": punishment_id,
                "solicitante": data["solicitante"],
                "punido": data["punido"],
                "quantidade": data["quantidade"],
                "motivo": data["motivo"],
                "prova_url": data.get("prova_url"),
                "permissao": data["solicitante"],  # No modo autônomo, quem aplica é quem solicita
                "status": "pendente",
                "data": time.time()
            }
            
            self.punishments_db[punishment_id] = punishment_data
            
            # Salva os dados persistentes
            self.save_punishments_persistent()
            
            # Envia relatório no canal público de punições
            if self.PUNISHMENTS_CHANNEL_ID != 0:
                channel = self.bot.get_channel(self.PUNISHMENTS_CHANNEL_ID)
                if channel:
                    punishment_message = self.create_punishment_report_message(punishment_data, self.bot.get_user(data["solicitante"]))
                    await channel.send(punishment_message)
                    self.logger.info(f"Punição autônoma registrada e enviada ao canal {self.PUNISHMENTS_CHANNEL_ID}")
                else:
                    self.logger.warning(f"Canal de punições não encontrado: {self.PUNISHMENTS_CHANNEL_ID}")
            
            # Notifica o usuário que a punição foi aplicada
            await canal.send(
                f"**{solicitante.mention}**, sua punição foi registrada e enviada para o canal de punições."
            )
            
            # Remove o estado temporário
            del self.pending_punishments[solicitante.id]
            
            self.logger.info(f"Punição autônoma confirmada e aplicada: {solicitante.id}")
            
        except asyncio.TimeoutError:
            # Timeout expirado para confirmação
            await self.cancel_punishment_request(solicitante, canal, "Tempo limite de confirmação esgotado")
            self.logger.warning(f"Timeout de confirmação para punição autônoma de {solicitante.id}")
        except Exception as e:
            self.logger.error(f"Erro ao processar confirmação de punição autônoma: {e}")
            await canal.send("Ocorreu um erro ao processar sua confirmação.")
    
    @commands.slash_command(
        name="historico-punicoes",
        description="Mostra o histórico de punições de um usuário específico (Cargos permitidos apenas)."
    )
    async def historico_punicoes(
        self,
        interaction: ApplicationCommandInteraction,
        usuario: disnake.Member
    ):
        """
        Comando slash para mostrar histórico de punições de um usuário específico.
        Apenas membros com cargos permitidos podem usar este comando.
        
        Args:
            interaction: Interação do comando
            usuario: Usuário cujo histórico será exibido
        """
        # Defer a resposta como efêmera para não poluir o canal
        await interaction.response.defer(ephemeral=True)
        
        # Verifica se o usuário tem permissão para usar este comando (cargos permitidos)
        has_permission, permission_message = self.validate_user_permissions(interaction.author)
        if not has_permission:
            await interaction.followup.send(permission_message, ephemeral=True)
            return
        
        # Sincroniza memória com disco para pegar progresso atualizado
        try:
            self.punishments_db, self.punishment_counter = data_manager.load_punishments()
            self.logger.info(f"Dados carregados do banco de dados: {len(self.punishments_db)} punições")
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar dados antes de listar: {e}")
            await interaction.followup.send("❌ Erro ao carregar dados de punições.", ephemeral=True)
            return

        # Filtra punições do usuário especificado (tanto como solicitante quanto como punido)
        user_punishments_solicitante = []
        user_punishments_punido = []
        
        for punishment_id, punishment_data in self.punishments_db.items():
            if punishment_data.get("solicitante") == usuario.id:
                user_punishments_solicitante.append((punishment_id, punishment_data))
            if punishment_data.get("punido") == usuario.id:
                user_punishments_punido.append((punishment_id, punishment_data))
        
        # Separa as punições recebidas por status (para o formato do /punicoes)
        in_analysis = []
        pending = []
        in_progress = []
        paused = []
        completed = []
        
        for punishment_id, punishment_data in user_punishments_punido:
            status = punishment_data.get("status", "desconhecido")
            if status == "em_analise":
                in_analysis.append((punishment_id, punishment_data))
            elif status == "pendente":
                pending.append((punishment_id, punishment_data))
            elif status == "em_cumprimento":
                in_progress.append((punishment_id, punishment_data))
            elif status == "pausada":
                paused.append((punishment_id, punishment_data))
            elif status in ["concluida", "cumprida"]:
                completed.append((punishment_id, punishment_data))
        
        # Cria embed para exibir o histórico no formato do /punicoes
        embed = Embed(
            title=f"📋 Histórico de Punições - {usuario.display_name}",
            description=f"Histórico detalhado das punições de {usuario.mention}.",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        # Adiciona estatísticas gerais (similar ao /punicoes)
        total_punishments = len(user_punishments_punido)
        total_jjs = sum(p_data['quantidade'] for _, p_data in user_punishments_punido)
        
        # Calcula JJ's em andamento e concluídos
        jjs_in_progress = 0
        jjs_completed = 0
        
        for _, p_data in in_progress:
            if "progresso_atual" in p_data:
                jjs_in_progress += p_data['progresso_atual']
            else:
                jjs_in_progress += p_data['quantidade']
        
        for _, p_data in completed:
            jjs_completed += p_data['quantidade']
        
        # Calcula quantos faltam para cumprir
        jjs_pending = sum(p_data['quantidade'] for _, p_data in pending)
        jjs_paused = sum(p_data['quantidade'] for _, p_data in paused)
        
        if total_punishments > 0:
            embed.add_field(
                name="📊 Resumo Geral",
                value=f"**Total:** {total_punishments} punição(ões)\n"
                      f"**Total de JJ's a cumprir:** {total_jjs} JJ's\n"
                      f"**Em andamento:** {len(in_progress)} ({jjs_in_progress}/{sum(p_data['quantidade'] for _, p_data in in_progress)} JJ's)\n"
                      f"**Concluídas:** {len(completed)} ({jjs_completed} JJ's)\n"
                      f"**Pendentes:** {len(pending)} ({jjs_pending} JJ's)\n"
                      f"**Pausadas:** {len(paused)} ({jjs_paused} JJ's)",
                inline=False
            )
        
        # Função para formatar punições no estilo compacto do /punicoes
        def format_punishments_compact(punishments_list):
            """Formato compacto para punições com menos linhas"""
            if not punishments_list:
                return "Nenhuma punição encontrada."
            
            text = ""
            for p_id, p_data in punishments_list:
                solicitante = self.bot.get_user(p_data["solicitante"])
                solicitante_mention = solicitante.mention if solicitante else f"<@{p_data['solicitante']}>"
                data_formatada = datetime.fromtimestamp(p_data["data"]).strftime("%d/%m/%Y")
                
                # Linha principal com informações essenciais
                text += f"**ID {p_id}** • {p_data['quantidade']} JJ's • {data_formatada}\n"
                
                # Linha secundária com solicitante e progresso
                progress_info = ""
                if "progresso_atual" in p_data:
                    progresso = p_data['progresso_atual']
                    total = p_data['quantidade']
                    progress_info = f" • **Progresso:** {progresso}/{total}"
                
                text += f"> **Solicitante:** {solicitante_mention}{progress_info}\n"
                
                # Motivo resumido (primeiras 50 caracteres)
                motivo_resumido = p_data['motivo'][:50] + "..." if len(p_data['motivo']) > 50 else p_data['motivo']
                text += f"> **Motivo:** {motivo_resumido}\n"
                
                text += "\n"
            return text

        # Adiciona seções à embed com formato compacto (igual ao /punicoes)
        if in_analysis:
            embed.add_field(
                name="🔍 Em Análise", 
                value=format_punishments_compact(in_analysis), 
                inline=False
            )
        
        if pending:
            embed.add_field(
                name="📌 Pendentes (Aguardando Início)", 
                value=format_punishments_compact(pending), 
                inline=False
            )
            
        if in_progress:
            embed.add_field(
                name="⚡ Em Andamento", 
                value=format_punishments_compact(in_progress), 
                inline=False
            )
            
        if paused:
            embed.add_field(
                name="⏸️ Pausadas", 
                value=format_punishments_compact(paused), 
                inline=False
            )
            
        if completed:
            embed.add_field(
                name="✅ Concluídas", 
                value=format_punishments_compact(completed), 
                inline=False
            )

        # Adiciona seção de punições solicitadas (se houver)
        if user_punishments_solicitante:
            solicitadas_text = ""
            for p_id, p_data in sorted(user_punishments_solicitante, key=lambda x: x[1].get("data", 0), reverse=True):
                punido = self.bot.get_user(p_data["punido"])
                punido_mention = punido.mention if punido else f"<@{p_data['punido']}>"
                data_formatada = datetime.fromtimestamp(p_data["data"]).strftime("%d/%m/%Y")
                status_text = self.get_status_display(p_data.get("status", "desconhecido"))
                
                solicitadas_text += f"**ID {p_id}** • {p_data['quantidade']} JJ's • {data_formatada}\n"
                solicitadas_text += f"> **Punido:** {punido_mention}\n"
                solicitadas_text += f"> **Status:** {status_text}\n"
                solicitadas_text += f"> **Motivo:** {p_data['motivo']}\n"
                solicitadas_text += "\n"
            
            embed.add_field(
                name="📝 Punições Solicitadas", 
                value=solicitadas_text, 
                inline=False
            )

        if not user_punishments_solicitante and not user_punishments_punido:
            embed.description = f"🛡️ {usuario.mention} não possui nenhuma punição registrada."
            embed.color = Color.green()
        
        # Envia o embed
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        self.logger.info(f"Histórico de punições exibido para {interaction.author.id} - Usuário: {usuario.id}")

    def get_status_display(self, status: str) -> str:
        """Converte status interno para exibição amigável."""
        status_map = {
            "em_analise": "🔍 Em Análise",
            "pendente": "📌 Pendente",
            "em_cumprimento": "⚡ Em",
            "pausada": "⏸️ Pausada",
            "cumprida": "✅ Concluída",
            "recusada": "❌ Recusada",
            "desconhecido": "❓ Desconhecido"
        }
        return status_map.get(status, status)

    @commands.slash_command(
        name="punicoes",
        description="Mostra as punições do militar."
    )
    async def punicoes(
        self,
        interaction: ApplicationCommandInteraction
    ):
        """
        Comando slash para mostrar punições de um militar.
        Apenas mostra punições para quem foi punido.
        
        Args:
            interaction: Interação do comando
        """
        # Defer a resposta como efêmera para não poluir o canal
        await interaction.response.defer(ephemeral=True)
        
        # Obtém o usuário que solicitou o comando
        user = interaction.author
        
        # Sincroniza memória com disco para pegar progresso atualizado
        try:
            self.punishments_db, self.punishment_counter = data_manager.load_punishments()
        except Exception as e:
            self.logger.error(f"Erro ao sincronizar dados antes de listar: {e}")

        # Filtra punições do usuário apenas como punido (não como solicitante)
        user_punishments = []
        for punishment_id, punishment_data in self.punishments_db.items():
            if punishment_data.get("punido") == user.id:
                user_punishments.append((punishment_id, punishment_data))
        
        # Separa punições por status
        in_analysis = []
        pending = []
        in_progress = []
        paused = []
        completed = []
        
        for punishment_id, punishment_data in user_punishments:
            status = punishment_data.get("status", "desconhecido")
            if status == "em_analise":
                in_analysis.append((punishment_id, punishment_data))
            elif status == "pendente":
                pending.append((punishment_id, punishment_data))
            elif status == "em_cumprimento":
                in_progress.append((punishment_id, punishment_data))
            elif status == "pausada":
                paused.append((punishment_id, punishment_data))
            elif status in ["concluida", "cumprida"]:
                completed.append((punishment_id, punishment_data))
        
        # Cria embed para exibir as punições com layout melhorado
        embed = Embed(
            title=f"📋 Punições de {user.display_name}",
            description="Status detalhado das suas punições:",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        # Adiciona resumo rápido no topo
        total_punishments = len(user_punishments)
        total_jjs = sum(p_data['quantidade'] for _, p_data in user_punishments)
        
        if total_punishments > 0:
            embed.add_field(
                name="📊 Resumo Geral",
                value=f"**Total:** {total_punishments} punição(ões)\n"
                      f"**Total de JJ's a cumprir:** {total_jjs} JJ's\n"
                      f"**Em andamento:** {len(in_progress)}\n"
                      f"**Concluídas:** {len(completed)}",
                inline=False
            )
        
        def format_punishments_compact(punishments_list):
            """Formato compacto para punições com menos linhas"""
            if not punishments_list:
                return "Nenhuma punição encontrada."
            
            text = ""
            for p_id, p_data in punishments_list:
                solicitante = self.bot.get_user(p_data["solicitante"])
                solicitante_mention = solicitante.mention if solicitante else f"<@{p_data['solicitante']}>"
                data_formatada = datetime.fromtimestamp(p_data["data"]).strftime("%d/%m/%Y")
                
                # Linha principal com informações essenciais
                text += f"**ID {p_id}** • {p_data['quantidade']} JJ's • {data_formatada}\n"
                
                # Linha secundária com solicitante e progresso
                progress_info = ""
                if "progresso_atual" in p_data:
                    progresso = p_data['progresso_atual']
                    total = p_data['quantidade']
                    progress_info = f" • **Progresso:** {progresso}/{total}"
                
                text += f"> **Solicitante:** {solicitante_mention}{progress_info}\n"
                
                # Motivo resumido (primeiras 50 caracteres)
                motivo_resumido = p_data['motivo'][:50] + "..." if len(p_data['motivo']) > 50 else p_data['motivo']
                text += f"> **Motivo:** {motivo_resumido}\n"
                
                text += "\n"
            return text

        def format_punishments_detailed(punishments_list):
            """Formato detalhado para punições com mais informações"""
            if not punishments_list:
                return "Nenhuma punição encontrada."
            
            text = ""
            for p_id, p_data in punishments_list:
                solicitante = self.bot.get_user(p_data["solicitante"])
                solicitante_mention = solicitante.mention if solicitante else f"<@{p_data['solicitante']}>"
                data_formatada = datetime.fromtimestamp(p_data["data"]).strftime("%d/%m/%Y")
                
                text += f"**ID {p_id}**\n"
                text += f"• **Quantidade:** {p_data['quantidade']} JJ's\n"
                text += f"• **Data:** {data_formatada}\n"
                text += f"• **Solicitante:** {solicitante_mention}\n"
                
                if "progresso_atual" in p_data:
                    progresso = p_data['progresso_atual']
                    total = p_data['quantidade']
                    text += f"• **Progresso:** {progresso}/{total}\n"
                
                # Motivo em bloco separado
                text += f"• **Motivo:**\n```\n{p_data['motivo']}\n```\n"
                
                text += "\n"
            return text

        # Adiciona seções à embed com formato compacto
        if in_analysis:
            embed.add_field(
                name="🔍 Em Análise", 
                value=format_punishments_compact(in_analysis), 
                inline=False
            )
        
        if pending:
            embed.add_field(
                name="📌 Pendentes (Aguardando Início)", 
                value=format_punishments_compact(pending), 
                inline=False
            )
            
        if in_progress:
            embed.add_field(
                name="⚡ Em Andamento", 
                value=format_punishments_compact(in_progress), 
                inline=False
            )
            
        if paused:
            embed.add_field(
                name="⏸️ Pausadas", 
                value=format_punishments_compact(paused), 
                inline=False
            )
            
        if completed:
            embed.add_field(
                name="✅ Concluídas", 
                value=format_punishments_compact(completed), 
                inline=False
            )

        if not user_punishments:
            embed.description = "🛡️ Você não possui nenhuma punição registrada."
            embed.color = Color.green()
        
        # Cria view com botão de cumprir punição
        view = None
        # Prioriza punições em andamento, depois pendentes
        target_punishment = None
        if in_progress:
            target_punishment = in_progress[0]
        elif pending:
            target_punishment = pending[0]
            
        if target_punishment:
            view = PunishmentPunishmentsView(user.id, target_punishment[0])
        
        # Envia a embed com os resultados
        if view:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        self.logger.info(f"Punições exibidas para {user.id}: {len(pending)} pendentes, {len(completed)} concluídas")

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
        
        try:
            # Limpa os arquivos de dados
            data_manager.save_punishments({}, 1)
            data_manager.save_pending_punishments({})
            
            # Limpa a memória
            self.punishments_db = {}
            self.punishment_counter = 1
            self.pending_punishments = {}
            
            await interaction.followup.send(
                "✅ **Histórico de punições limpo com sucesso!**\nTodos os registros foram removidos.",
                ephemeral=True
            )
            
            self.logger.info(f"Histórico de punições limpo por {interaction.author.id}")
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar histórico de punições: {e}")
            await interaction.followup.send(
                "❌ **Erro ao limpar histórico de punições.**\nPor favor, tente novamente.",
                ephemeral=True
            )

    @commands.slash_command(
        name="solicitar-punicao",
        description="Solicita punição em JJ's para um militar."
    )
    async def solicitacao_punicao(
        self,
        interaction: ApplicationCommandInteraction,
        punido: disnake.Member,
        quantidade: int,
        motivo: str
    ):
        """
        Comando slash para solicitar punição.
        
        Args:
            interaction: Interação do comando
            punido: Usuário a ser punido
            quantidade: Quantidade de JJ's
            motivo: Motivo da punição
        """
        # Verifica se está no canal de solicitações correto
        if self.REQUESTS_CHANNEL_ID != 0 and interaction.channel.id != self.REQUESTS_CHANNEL_ID:
            requests_channel = self.bot.get_channel(self.REQUESTS_CHANNEL_ID)
            if requests_channel:
                await interaction.response.send_message(
                    f"❌ **Comando disponível apenas no canal {requests_channel.mention}**\n"
                    f"Por favor, use o comando no canal correto para solicitar punições.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ **Canal de solicitações não configurado corretamente.**\n"
                    "Por favor, contacte um administrador.",
                    ephemeral=True
                )
            return
        
        # Defer a resposta como efêmera para não poluir o canal
        await interaction.response.defer(ephemeral=True)
        
        # Valida permissões do usuário
        has_permission, permission_message = self.validate_user_permissions(interaction.author)
        if not has_permission:
            await interaction.followup.send(permission_message, ephemeral=True)
            return
        
        # Valida os dados da solicitação
        is_valid, message = self.validate_punishment_data(
            interaction.author.id, 
            punido.id, 
            quantidade, 
            motivo
        )
        
        if not is_valid:
            await interaction.followup.send(message, ephemeral=True)
            return
        
        # Cria o registro da solicitação no dicionário
        timestamp = time.time()
        self.pending_punishments[interaction.author.id] = {
            "solicitante": interaction.author.id,
            "punido": punido.id,
            "quantidade": quantidade,
            "motivo": motivo,
            "status": "aguardando_foto",
            "canal": interaction.channel.id,
            "criado_em": timestamp
        }
        
        # Cria e envia a embed com os detalhes (efêmera)
        embed = self.create_punishment_embed(
            interaction.author, 
            punido, 
            quantidade, 
            motivo, 
            "Aguardando envio da foto comprobatória."
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Envia instruções para o solicitante (efêmera)
        instructions = (
            f"**{interaction.author.mention}**, por favor envie a foto comprobatória neste canal.\n\n"
            f"**Importante:**\n"
            f"- Apenas você pode enviar a foto para esta solicitação;\n"
            f"- O arquivo deve ser uma imagem válida (PNG, JPG, etc.);\n"
            f"- Você tem **{self.TIMEOUT_MINUTES} minutos** para enviar a foto;\n"
            f"- Caso não envie, a solicitação será cancelada."
        )
        
        self.logger.info(f"Instruções enviadas para {interaction.author.id} no canal {interaction.channel.id}")
        
        await interaction.followup.send(instructions, ephemeral=True)
        
        # Inicia o processo de espera pela foto
        await self.wait_for_photo(interaction.author, interaction.channel)
    
    async def wait_for_photo(self, solicitante: disnake.Member, canal: disnake.TextChannel):
        """
        Aguarda o envio da foto comprobatória com timeout.
        
        Args:
            solicitante: Membro que deve enviar a foto
            canal: Canal onde a foto deve ser enviada
        """
        def check_message(message: disnake.Message) -> bool:
            """Verifica se a mensagem atende aos critérios para ser considerada válida."""
            # Verifica se é do solicitante
            if message.author.id != solicitante.id:
                return False
            
            # Verifica se é no mesmo canal
            if message.channel.id != canal.id:
                return False
            
            # Verifica se tem anexos
            if not message.attachments:
                return False
            
            # Verifica se o anexo é uma imagem válida
            for attachment in message.attachments:
                if self.is_valid_image_attachment(attachment):
                    return True
            
            return False
        
        try:
            # Aguarda até 5 minutos por uma mensagem válida
            timeout_seconds = self.TIMEOUT_MINUTES * 60
            message = await self.bot.wait_for(
                'message', 
                check=check_message, 
                timeout=timeout_seconds
            )
            
            # Processa a foto enviada
            await self.process_photo_submission(solicitante, canal, message)
            
        except asyncio.TimeoutError:
            # Timeout expirado - cancela a solicitação
            await self.cancel_punishment_request(solicitante, canal, "Tempo limite expirado")
            self.logger.warning(f"Timeout expirado para solicitação de {solicitante.id}")
    
    async def process_photo_submission(self, solicitante: disnake.Member, canal: disnake.TextChannel, 
                                     message: disnake.Message):
        """
        Processa a foto enviada pelo solicitante e avança para a etapa de confirmação.
        
        Args:
            solicitante: Membro que enviou a foto
            canal: Canal onde a foto foi enviada
            message: Mensagem contendo a foto
        """
        # Encontra a imagem válida
        valid_attachment = None
        for attachment in message.attachments:
            if self.is_valid_image_attachment(attachment):
                valid_attachment = attachment
                break
        
        self.logger.info(f"Foto recebida de {solicitante.id}: {valid_attachment.filename if valid_attachment else 'Nenhuma imagem válida'}")
        
        if not valid_attachment:
            await canal.send(f"{solicitante.mention}, a foto enviada não é válida. Solicitação cancelada.")
            if solicitante.id in self.pending_punishments:
                del self.pending_punishments[solicitante.id]
            return
        
        # Cria embed de confirmação de recebimento
        embed = Embed(
            title="Foto Recebida",
            description="A foto comprobatória foi validada com sucesso.",
            color=Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Arquivo",
            value=f"`{valid_attachment.filename}`",
            inline=True
        )
        
        embed.add_field(
            name="Solicitante",
            value=solicitante.mention,
            inline=True
        )
        
        # Adiciona a foto ao embed e prepara o arquivo
        file = await valid_attachment.to_file()
        
        # Envia a confirmação com o arquivo e solicita a confirmação manual
        sent_message = await canal.send(embed=embed, file=file)
        
        # Atualiza o estado com a URL da foto (agora do canal do bot, mais estável) e altera status
        if solicitante.id in self.pending_punishments:
            # Pega a URL do anexo da mensagem que o bot acabou de enviar
            if sent_message.attachments:
                # Usa a URL do anexo enviado para garantir que a imagem carregue corretamente
                attachment_url = sent_message.attachments[0].url
                self.pending_punishments[solicitante.id]["prova_url"] = attachment_url
                # Atualiza o embed para usar a URL direta do anexo enviado
                embed.set_image(url=attachment_url)
                # Edita a mensagem para garantir que a imagem seja exibida corretamente
                await sent_message.edit(embed=embed)
            else:
                # Fallback caso ocorra erro no anexo da nova mensagem
                self.pending_punishments[solicitante.id]["prova_url"] = valid_attachment.url
                
            self.pending_punishments[solicitante.id]["status"] = "aguardando_confirmacao"
        
        # Apaga a mensagem original que contém a foto
        try:
            await message.delete()
            self.logger.info(f"Foto apagada da mensagem {message.id} enviada por {solicitante.id}")
        except disnake.NotFound:
            self.logger.warning(f"Mensagem {message.id} já foi apagada")
        except disnake.Forbidden:
            self.logger.warning(f"Sem permissão para apagar a mensagem {message.id}")
        except Exception as e:
            self.logger.error(f"Erro ao apagar a mensagem {message.id}: {e}")
        
        confirmation_msg = (
            f"**{solicitante.mention}**, para finalizar e enviar sua solicitação para análise, "
            f"digite uma das palavras abaixo neste canal: "
            f"`confirmar`, `enviar` ou `ok`"
        )
        
        await canal.send(confirmation_msg)
        
        # Inicia o processo de espera pela confirmação manual
        await self.wait_for_confirmation(solicitante, canal)
    
    async def wait_for_confirmation(self, solicitante: disnake.Member, canal: disnake.TextChannel):
        """
        Aguarda a confirmação manual do solicitante por mensagem.
        """
        def check_confirmation(message: disnake.Message) -> bool:
            # Verifica se é do solicitante no mesmo canal
            if message.author.id != solicitante.id or message.channel.id != canal.id:
                return False
            
            # Verifica se o status ainda é aguardando_confirmacao
            if solicitante.id not in self.pending_punishments or \
               self.pending_punishments[solicitante.id]["status"] != "aguardando_confirmacao":
                return False
            
            # Verifica as palavras-chave (case-insensitive)
            valid_words = ["confirmar", "enviar", "ok"]
            return message.content.lower().strip() in valid_words

        try:
            # Aguarda 5 minutos para a confirmação manual
            timeout_seconds = self.TIMEOUT_MINUTES * 60
            await self.bot.wait_for('message', check=check_confirmation, timeout=timeout_seconds)
            
            # Se chegou aqui, o usuário confirmou
            data = self.pending_punishments[solicitante.id]
            data["status"] = "em_analise"
            
            # Registra a solicitação no banco de dados para visibilidade
            punishment_id = self.punishment_counter
            self.punishment_counter += 1
            data["punishment_id"] = punishment_id
            
            punishment_data = {
                "id": punishment_id,
                "solicitante": data["solicitante"],
                "punido": data["punido"],
                "quantidade": data["quantidade"],
                "motivo": data["motivo"],
                "prova_url": data.get("prova_url"),
                "status": "em_analise",
                "data": time.time()
            }
            
            self.punishments_db[punishment_id] = punishment_data
            self.save_punishments_persistent()
            
            # Gera o relatório final com botões
            report_embed = self.create_report_embed(data)
            view = PunishmentReviewView(BotConfig.PunishmentSystem.RESPONSIBLE_ROLE_IDS)
            
            # Verifica se há canal de aprovação configurado
            if self.APPROVAL_CHANNEL_ID != 0:
                approval_channel = self.bot.get_channel(self.APPROVAL_CHANNEL_ID)
                if approval_channel:
                    # Envia a solicitação para o canal de aprovação
                    await approval_channel.send(embed=report_embed, view=view)
                    
                    # Notifica o solicitante sobre o redirecionamento
                    await canal.send(
                        f"✅ **Solicitação enviada para análise!**\n"
                    )
                    
                    self.logger.info(f"Solicitação redirecionada para o canal de aprovação: {solicitante.id}")
                else:
                    # Canal de aprovação não encontrado, mantém no canal atual
                    await canal.send(embed=report_embed, view=view)
                    await canal.send(
                        f"⚠️ **Canal de aprovação não encontrado.**\n"
                        f"**{solicitante.mention}**, sua solicitação será analisada neste canal."
                    )
                    self.logger.warning(f"Canal de aprovação não encontrado, mantendo no canal atual: {solicitante.id}")
            else:
                # Canal de aprovação não configurado, mantém no canal atual
                await canal.send(embed=report_embed, view=view)
                await canal.send(
                    f"⚠️ **Canal de aprovação não configurado.**\n"
                    f"**{solicitante.mention}**, sua solicitação será analisada neste canal."
                )
                self.logger.warning(f"Canal de aprovação não configurado, mantendo no canal atual: {solicitante.id}")
            
            # Agora podemos remover do estado temporário pois já foi para o canal de análise
            del self.pending_punishments[solicitante.id]
            
            self.logger.info(f"Solicitação confirmada e enviada para análise: {solicitante.id}")
            
        except asyncio.TimeoutError:
            # Timeout expirado para confirmação
            await self.cancel_punishment_request(solicitante, canal, "Tempo limite de confirmação esgotado")
            self.logger.warning(f"Timeout de confirmação para {solicitante.id}")
        except Exception as e:
            self.logger.error(f"Erro ao processar confirmação: {e}")
            await canal.send("Ocorreu um erro ao processar sua confirmação.")

    async def fulfill_punishment(self, interaction: disnake.MessageInteraction, user_id: int, punishment_id: int):
        """
        Processa o cumprimento de uma punição.
        Cria canal privado para o cumprimento da punição.
        
        Args:
            interaction: Interação do botão de cumprir punição
            user_id: ID do usuário que está cumprindo a punição
            punishment_id: ID da punição a ser cumprida
        """
        try:
            # Verifica se a punição existe
            if punishment_id not in self.punishments_db:
                await interaction.response.send_message(
                    "❌ **Punição não encontrada!**\nEsta punição pode ter sido removida ou já cumprida.",
                    ephemeral=True
                )
                return
            
            punishment_data = self.punishments_db[punishment_id]
            
            # Verifica se o usuário tem permissão para cumprir esta punição
            if punishment_data["punido"] != user_id:
                await interaction.response.send_message(
                    "❌ **Acesso Negado!**\nVocê só pode cumprir punições que foram aplicadas a você.",
                    ephemeral=True
                )
                return
            
            # Verifica se a punição já foi cumprida
            if punishment_data["status"] == "concluida":
                await interaction.response.send_message(
                    "✅ **Punição já cumprida!**\nEsta punição já foi marcada como cumprida.",
                    ephemeral=True
                )
                return
            
            # Verifica se o usuário já tem algum canal de punição aberto
            guild = interaction.guild
            member = guild.get_member(user_id)
            if not member:
                await interaction.response.send_message(
                    "❌ **Usuário não encontrado no servidor!**",
                    ephemeral=True
                )
                return
            
            # Verifica se o usuário já tem algum canal de punição aberto
            existing_punishment_channels = []
            for channel in guild.text_channels:
                if channel.name.startswith("punicao-"):
                    # Verifica se o usuário tem permissão para ver este canal
                    if channel.permissions_for(member).view_channel:
                        existing_punishment_channels.append(channel)
            
            if existing_punishment_channels:
                # Se já existir canal de punição, impede a criação de outro
                existing_channel = existing_punishment_channels[0]  # Pega o primeiro canal encontrado
                await interaction.response.send_message(
                    f"⚠️ **Canal de punição já existe!**\nVocê já possui um canal de punição aberto: {existing_channel.mention}\n"
                    f"Para criar um novo canal, você precisa concluir a punição atual.",
                    ephemeral=True
                )
                return
            
            # Cria o nome do canal privado usando o nome de exibição do servidor
            channel_name = f"punicao-{member.display_name.lower().replace(' ', '-')}"
            
            # Verifica se o canal já existe (para garantir consistência)
            existing_channel = disnake.utils.get(guild.text_channels, name=channel_name)
            if existing_channel:
                # Se já existe, envia mensagem de aviso
                await interaction.response.send_message(
                    f"⚠️ **Canal já existe!**\nO canal {existing_channel.mention} já foi criado para esta punição.",
                    ephemeral=True
                )
                return
            
            try:
                # Cria o canal privado
                overwrites = {
                    guild.default_role: disnake.PermissionOverwrite(view_channel=False),
                    guild.me: disnake.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
                    member: disnake.PermissionOverwrite(view_channel=True, send_messages=True)
                }
                
                # Obtém a categoria onde o canal será criado
                category = None
                if BotConfig.PunishmentSystem.PUNISHMENT_CATEGORY_ID != 0:
                    category = guild.get_channel(BotConfig.PunishmentSystem.PUNISHMENT_CATEGORY_ID)
                    if not category:
                        self.logger.warning(f"Categoria de punição não encontrada: {BotConfig.PunishmentSystem.PUNISHMENT_CATEGORY_ID}")
                
                channel = await guild.create_text_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    category=category,  # Usa a categoria configurada ou None se não encontrada
                    reason=f"Canal privado para cumprimento da punição ID {punishment_id}"
                )
                
                self.logger.info(f"Canal privado criado: {channel.name} para punição {punishment_id}")
                
            except disnake.Forbidden:
                await interaction.response.send_message(
                    "❌ **Sem permissão para criar canal!**\nO bot não tem permissão para criar canais neste servidor.",
                    ephemeral=True
                )
                return
            except disnake.HTTPException as e:
                await interaction.response.send_message(
                    f"❌ **Erro ao criar canal!**\n{e}",
                    ephemeral=True
                )
                return
            
            # Registra o início do cumprimento da punição
            punishment_data["status"] = "em_cumprimento"
            punishment_data["data_inicio_cumprimento"] = time.time()
            
            # Salva os dados persistentes
            self.save_punishments_persistent()
            
            # Inicia o sistema de validação JJ's
            jj_cog = self.bot.get_cog("JJValidationSystem")
            if jj_cog:
                try:
                    # Inicia sessão de validação JJ's
                    await jj_cog.iniciar_jj(
                        user_id=user_id, 
                        punishment_id=punishment_id, 
                        quantidade=punishment_data["quantidade"]
                    )
                except Exception as e:
                    self.logger.error(f"Erro ao iniciar validação JJ's: {e}")
            
            # Cria embed de registro do início do cumprimento
            embed = Embed(
                title="Início do Cumprimento da Punição",
                description=f"O militar iniciou o cumprimento da punição ID {punishment_id}.",
                color=Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Punido",
                value=f"<@{user_id}>",
                inline=True
            )
            
            embed.add_field(
                name="Quantidade",
                value=f"**{punishment_data['quantidade']} JJ's**",
                inline=True
            )
            
            embed.add_field(
                name="Data de Início",
                value=f"<t:{int(time.time())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="Canal Privado",
                value=f"{channel.mention}",
                inline=True
            )
            
            embed.add_field(
                name="Status",
                value="**Em Cumprimento**",
                inline=True
            )
            
            embed.add_field(
                name="Motivo",
                value=f"```\n{punishment_data['motivo']}\n```",
                inline=False
            )
            
            # Envia a mensagem de registro no canal privado
            await channel.send(embed=embed)
            
            # Envia mensagem de boas-vindas no canal privado
            welcome_embed = Embed(
                title="Canal de Cumprimento de Punição",
                description=f"Este é o canal privado para o cumprimento da punição ID {punishment_id}.",
                color=Color.blue(),
                timestamp=datetime.now()
            )
            
            welcome_embed.add_field(
                name="Instruções",
                value=(
                    "1. Este canal é privado e apenas você e o bot podem ver as mensagens.\n"
                    "2. Cumpra a punição conforme solicitado.\n"
                    "3. Quando terminar, digite `concluído` ou `terminado` neste canal.\n"
                    "4. O bot registrará o cumprimento automaticamente."
                ),
                inline=False
            )
            
            welcome_embed.add_field(
                name="Punição",
                value=f"**{punishment_data['quantidade']} JJ's**",
                inline=True
            )
            
            welcome_embed.add_field(
                name="Motivo",
                value=f"```\n{punishment_data['motivo']}\n```",
                inline=True
            )
            
            welcome_embed.add_field(
                name="Status Atual",
                value="**Em Cumprimento**",
                inline=True
            )
            
            await channel.send(embed=welcome_embed)
            
            # Cria embed de confirmação para o usuário
            response_embed = Embed(
                title="Canal Privado Criado!",
                description=f"O canal {channel.mention} foi criado para o cumprimento da sua punição.",
                color=Color.green(),
                timestamp=datetime.now()
            )
            
            response_embed.add_field(
                name="Status da Punição",
                value="**Em andamento**",
                inline=True
            )
            
            response_embed.add_field(
                name="Quantidade",
                value=f"**{punishment_data['quantidade']} JJ's**",
                inline=True
            )
            
            response_embed.add_field(
                name="Próximos Passos",
                value="Acesse o canal privado e cumpra a punição. Quando terminar, informe no canal.",
                inline=False
            )
            
            await interaction.response.send_message(
                embed=response_embed,
                ephemeral=True
            )
            
            # Não remove os botões da mensagem original, pois a punição ainda não foi concluída
            # await interaction.message.edit(embed=interaction.message.embeds[0], view=None)
            
            self.logger.info(f"Punição {punishment_id} iniciada por {user_id} no canal {channel.name}")
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar cumprimento da punição: {e}")
            # Verifica se a interação já foi respondida antes de tentar responder novamente
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        "❌ Erro ao processar início do cumprimento da punição.",
                        ephemeral=True
                    )
                except Exception as response_error:
                    self.logger.error(f"Erro ao enviar mensagem de erro: {response_error}")

    async def cancel_punishment_request(self, solicitante: disnake.Member, canal: disnake.TextChannel, motivo: str):
        """
        Cancela uma solicitação de punição e remove o estado da memória.
        
        Args:
            solicitante: Membro da solicitação cancelada
            canal: Canal onde a solicitação foi feita
            motivo: Motivo do cancelamento
        """
        # Remove o estado da memória
        if solicitante.id in self.pending_punishments:
            del self.pending_punishments[solicitante.id]
        
        # Cria embed de cancelamento
        embed = Embed(
            title="Solicitação Cancelada",
            description=f"Motivo: {motivo}",
            color=Color.red(),
            timestamp=datetime.now()
        )
        
        self.logger.info(f"Solicitação cancelada para {solicitante.id}: {motivo}")
        
        embed.add_field(
            name="Solicitante",
            value=solicitante.mention,
            inline=True
        )
        
        embed.add_field(
            name="Data/Hora",
            value=f"<t:{int(time.time())}:f>",
            inline=True
        )
        
        await canal.send(embed=embed)

    async def approve_punishment(self, interaction: disnake.MessageInteraction):
        """
        Aprova uma solicitação de punição e registra no banco de dados.
        
        Args:
            interaction: Interação do botão de aprovação
        """
        try:
            # Obtém os dados da embed
            embed = interaction.message.embeds[0]
            
            # Tenta extrair o ID da punição do rodapé
            punishment_id = self.extract_punishment_id_from_footer(embed)
            
            if punishment_id and punishment_id in self.punishments_db:
                # Punição já existe no banco, apenas atualiza o status
                punishment_data = self.punishments_db[punishment_id]
                punishment_data["status"] = "pendente"
                punishment_data["permissao"] = interaction.author.id
                punishment_data["data_aprovacao"] = time.time()
            else:
                # Caso não encontre por ID (retrocompatibilidade ou erro), cria nova
                punishment_id = self.punishment_counter
                self.punishment_counter += 1
                
                punishment_data = {
                    "id": punishment_id,
                    "solicitante": self.extract_user_id_from_embed(embed, "Nome:"),
                    "punido": self.extract_user_id_from_embed(embed, "Punido:"),
                    "quantidade": self.extract_quantity_from_embed(embed),
                    "motivo": self.extract_reason_from_embed(embed),
                    "permissao": interaction.author.id,
                    "status": "pendente",
                    "data": time.time(),
                    "data_aprovacao": time.time()
                }
                self.punishments_db[punishment_id] = punishment_data
            
            # Salva os dados persistentes
            self.save_punishments_persistent()
            
            # Atualiza a mensagem original removendo os botões
            embed.color = Color.green()
            embed.set_footer(text=f"Aprovado por: {interaction.author.name} • ID Punição: {punishment_id}")
            await interaction.message.edit(embed=embed, view=None)
            
            await interaction.response.send_message(f"✅ **Punição ID {punishment_id} aprovada com sucesso!**", ephemeral=True)
            
            # Envia relatório no canal público de punições
            if self.PUNISHMENTS_CHANNEL_ID != 0:
                channel = self.bot.get_channel(self.PUNISHMENTS_CHANNEL_ID)
                if channel:
                    punishment_message = self.create_punishment_report_message(punishment_data, interaction.author)
                    await channel.send(punishment_message)
                    self.logger.info(f"Punição registrada e enviada ao canal {self.PUNISHMENTS_CHANNEL_ID}")
                else:
                    self.logger.warning(f"Canal de punições não encontrado: {self.PUNISHMENTS_CHANNEL_ID}")
            
            self.logger.info(f"Punição aprovada por {interaction.author.id}: ID {punishment_id}")
            
        except Exception as e:
            self.logger.error(f"Erro ao aprovar punição: {e}")
            await interaction.response.send_message("❌ Erro ao processar aprovação.", ephemeral=True)

    async def reject_punishment(self, interaction: disnake.MessageInteraction):
        """
        Recusa uma solicitação de punição e notifica o solicitante.
        
        Args:
            interaction: Interação do botão de recusa
        """
        try:
            # Obtém os dados da embed
            embed = interaction.message.embeds[0]
            
            # Atualiza a mensagem original removendo os botões
            embed.color = Color.red()
            embed.set_footer(text=f"Recusado por: {interaction.author.name}")
            await interaction.message.edit(embed=embed, view=None)
            
            # Notifica o solicitante
            solicitante_id = self.extract_user_id_from_embed(embed, "Nome:")
            if solicitante_id:
                solicitante = self.bot.get_user(solicitante_id)
                if solicitante:
                    try:
                        reject_embed = Embed(
                            title="Solicitação de Punição Recusada",
                            description="Sua solicitação de punição foi recusada.",
                            color=Color.red(),
                            timestamp=datetime.now()
                        )
                        
                        reject_embed.add_field(
                            name="Motivo da recusa:",
                            value=f"Punição negada por {interaction.author.mention}",
                            inline=False
                        )
                        
                        reject_embed.add_field(
                            name="Data/Hora:",
                            value=f"<t:{int(time.time())}:F>",
                            inline=True
                        )
                        
                        await solicitante.send(embed=reject_embed)
                        self.logger.info(f"Notificação de recusa enviada para {solicitante_id}")
                    except disnake.Forbidden:
                        self.logger.warning(f"Não foi possível enviar DM para {solicitante_id}")
            
            # Responde ao aprovador
            await interaction.response.send_message("❌ **Solicitação recusada com sucesso!**", ephemeral=True)
            
            self.logger.info(f"Punição recusada por {interaction.author.id}")
            
        except Exception as e:
            self.logger.error(f"Erro ao recusar punição: {e}")
            await interaction.response.send_message("❌ Erro ao processar recusa.", ephemeral=True)

    async def reject_punishment_with_reason(self, interaction: disnake.ModalInteraction, rejection_reason: str):
        """
        Recusa uma solicitação de punição com motivo personalizado e notifica o solicitante.
        
        Args:
            interaction: Interação do modal de recusa
            rejection_reason: Motivo da recusa digitado pelo responsável
        """
        try:
            # Obtém os dados da embed
            embed = interaction.message.embeds[0]
            
            # Tenta extrair o ID da punição do rodapé
            punishment_id = self.extract_punishment_id_from_footer(embed)
            
            if punishment_id and punishment_id in self.punishments_db:
                # Atualiza o status no banco
                punishment_data = self.punishments_db[punishment_id]
                punishment_data["status"] = "recusada"
                punishment_data["motivo_recusa"] = rejection_reason
                punishment_data["recusado_por"] = interaction.author.id
                punishment_data["data_recusa"] = time.time()
                
                self.save_punishments_persistent()
            
            # Atualiza a mensagem original removendo os botões
            embed.color = Color.red()
            embed.set_footer(text=f"Recusado por: {interaction.author.name} • ID Punição: {punishment_id if punishment_id else 'N/A'}")
            await interaction.message.edit(embed=embed, view=None)
            
            # Notifica o solicitante com o motivo personalizado
            solicitante_id = self.extract_user_id_from_embed(embed, "Nome:")
            if solicitante_id:
                solicitante = self.bot.get_user(solicitante_id)
                if solicitante:
                    try:
                        reject_embed = Embed(
                            title="Solicitação de Punição Recusada",
                            description="Sua solicitação de punição foi recusada.",
                            color=Color.red(),
                            timestamp=datetime.now()
                        )
                        
                        reject_embed.add_field(
                            name="Motivo da recusa:",
                            value=rejection_reason,
                            inline=False
                        )
                        
                        reject_embed.add_field(
                            name="Recusado por:",
                            value=interaction.author.mention,
                            inline=True
                        )
                        
                        reject_embed.add_field(
                            name="Data/Hora:",
                            value=f"<t:{int(time.time())}:F>",
                            inline=True
                        )
                        
                        await solicitante.send(embed=reject_embed)
                        self.logger.info(f"Notificação de recusa enviada para {solicitante_id} com motivo: {rejection_reason}")
                    except disnake.Forbidden:
                        self.logger.warning(f"Não foi possível enviar DM para {solicitante_id}")
            
            # Responde ao responsável confirmando a recusa
            await interaction.response.send_message(
                f"❌ **Solicitação recusada com sucesso!**\n"
                f"**Motivo:** {rejection_reason}",
                ephemeral=True
            )
            
            self.logger.info(f"Punição recusada por {interaction.author.id} com motivo: {rejection_reason}")
            
        except Exception as e:
            self.logger.error(f"Erro ao recusar punição com motivo: {e}")
            await interaction.response.send_message("❌ Erro ao processar recusa.", ephemeral=True)

    def extract_punishment_id_from_footer(self, embed: Embed) -> Optional[int]:
        """
        Extrai o ID da punição do rodapé da embed.
        """
        if not embed.footer or not embed.footer.text:
            return None
        
        # O formato é "ID Punição: 123 • Status: ..."
        import re
        match = re.search(r'ID Punição: (\d+)', embed.footer.text)
        if match:
            return int(match.group(1))
        return None

    def extract_user_id_from_embed(self, embed: Embed, field_name: str) -> Optional[int]:
        """
        Extrai o ID de usuário de um campo da embed.
        
        Args:
            embed: Embed contendo os dados
            field_name: Nome do campo a ser extraído
            
        Returns:
            Optional[int]: ID do usuário ou None se não encontrado
        """
        for field in embed.fields:
            if field.name == field_name:
                # Extrai o ID do mention (ex: <@123456789>)
                import re
                match = re.search(r'<@!?(\d+)>', field.value)
                if match:
                    return int(match.group(1))
        return None

    def extract_quantity_from_embed(self, embed: Embed) -> Optional[int]:
        """
        Extrai a quantidade de JJ's da embed.
        
        Args:
            embed: Embed contendo os dados
            
        Returns:
            Optional[int]: Quantidade de JJ's ou None se não encontrado
        """
        for field in embed.fields:
            if field.name == "Quantidade:":
                # Extrai o número (ex: "**100 JJ's**")
                import re
                match = re.search(r'(\d+)', field.value)
                if match:
                    return int(match.group(1))
        return None

    def extract_reason_from_embed(self, embed: Embed) -> Optional[str]:
        """
        Extrai o motivo da embed.
        
        Args:
            embed: Embed contendo os dados
            
        Returns:
            Optional[str]: Motivo ou None se não encontrado
        """
        for field in embed.fields:
            if field.name == "Motivo:":
                # Remove as crases e espaços extras
                return field.value.replace('```', '').strip()
        return None

    def create_punishment_report_embed(self, punishment_data: Dict, aprovador: disnake.User) -> Embed:
        """
        Cria o embed de relatório de punição para o canal público.
        
        Args:
            punishment_data: Dados da punição aprovada
            aprovador: Usuário que aprovou a punição
            
        Returns:
            Embed: Embed formatado para o canal público
        """
        solicitante = self.bot.get_user(punishment_data["solicitante"])
        punido = self.bot.get_user(punishment_data["punido"])
        
        embed = Embed(
            title="Relatório de Punição!",
            description="Uma nova punição foi aprovada e registrada.",
            color=Color.red(),
            timestamp=datetime.fromtimestamp(punishment_data["data"])
        )
        
        embed.add_field(
            name="Permissão:",
            value=aprovador.mention,
            inline=True
        )
        
        embed.add_field(
            name="Nome:",
            value=solicitante.mention if solicitante else f"ID: {punishment_data['solicitante']}",
            inline=True
        )
        
        embed.add_field(
            name="Punido:",
            value=punido.mention if punido else f"ID: {punishment_data['punido']}",
            inline=True
        )
        
        embed.add_field(
            name="Quantidade:",
            value=f"**{punishment_data['quantidade']} JJ's**",
            inline=True
        )
        
        embed.add_field(
            name="Motivo:",
            value=f"```\n{punishment_data['motivo']}\n```",
            inline=False
        )
        
        embed.add_field(
            name="Data/Hora:",
            value=f"<t:{int(punishment_data['data'])}:F>",
            inline=True
        )
        
        embed.set_footer(text=f"Status: Pendente • ID da Punição: {list(self.punishments_db.keys())[-1] if self.punishments_db else 'N/A'}")
        
        return embed

    def create_punishment_report_message(self, punishment_data: Dict, aprovador: disnake.User) -> str:
        """
        Cria a mensagem de relatório de punição para o canal público (texto simples).
        
        Args:
            punishment_data: Dados da punição aprovada
            aprovador: Usuário que aprovou a punição
            
        Returns:
            str: Mensagem formatada para o canal público
        """
        solicitante = self.bot.get_user(punishment_data["solicitante"])
        punido = self.bot.get_user(punishment_data["punido"])
        
        # Converte timestamp para data/hora formatada
        from datetime import datetime
        data_formatada = datetime.fromtimestamp(punishment_data["data"])
        data_hora = data_formatada.strftime("%d/%m/%Y • %Hh%Mm")
        
        # Formata a mensagem de texto simples no novo formato
        message = f"""**Relatório de Punição!**

> **Responsável:** **{solicitante.mention if solicitante else f"<@{punishment_data['solicitante']}>"}**
> 
> **Permissão:** **{aprovador.mention}**
> 
> **Punido(a):** **{punido.mention if punido else f"<@{punishment_data['punido']}>"}**
> 
> **Quantidade:** **{punishment_data['quantidade']} JJ's**
> 
> **Motivo:** **{punishment_data['motivo']}**

**Data:** **{data_hora}**"""
        
        return message


class Bot(commands.Bot):
    """
    Bot principal que inicializa o sistema de solicitação de punição.
    """
    
    def __init__(self):
        # Configurações do bot
        intents = disnake.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            test_guilds=BotConfig.TEST_GUILDS
        )
        
        # Configura o logger para a classe Bot
        self.logger = logging.getLogger(__name__)
        
        # Status rotativos do bot
        self.status_messages = [
            "Exército Brasileiro",
            "Monitorando Cabos",
            "Administrando a ESA"
        ]
        self.current_status_index = 0
        
        # Inicia a tarefa de mudança de status
        self.change_status.start()
    
    @tasks.loop(seconds=30)
    async def change_status(self):
        """Altera o status do bot a cada 30 segundos."""
        if self.status_messages:
            # Seleciona o próximo status
            status_text = self.status_messages[self.current_status_index]
            
            # Cria a atividade com o status
            activity = disnake.Activity(
                type=ActivityType.playing,
                name=status_text
            )
            
            # Atualiza o status do bot
            await self.change_presence(activity=activity)
            
            # Atualiza o índice para o próximo status
            self.current_status_index = (self.current_status_index + 1) % len(self.status_messages)
            
            self.logger.info(f"Status do bot atualizado para: {status_text}")
    
    @change_status.before_loop
    async def before_change_status(self):
        """Aguarda o bot estar pronto antes de iniciar a tarefa de mudança de status."""
        await self.wait_until_ready()
    
    async def on_ready(self):
        logging.basicConfig(
            level=getattr(logging, BotConfig.Logging.LOG_LEVEL),
            format=BotConfig.Logging.LOG_FORMAT,
            filename=BotConfig.Logging.LOG_FILE if BotConfig.Logging.LOG_FILE else None
        )

        print(f"Bot conectado como {self.user}")
        print(f"Servidores conectados: {len(self.guilds)}")
        print(f"Usuarios: {len(set(self.get_all_members()))}")
        print("-" * 50)

        errors = validate_config()
        if errors:
            print("Erros de configuração encontrados:")
            for error in errors:
                print(error)

        if not hasattr(self, "punishment_cog_loaded"):
            self.add_cog(PunishmentRequestSystem(self))
            self.add_cog(JJValidationSystem(self))
            self.punishment_cog_loaded = True

        print("Bot pronto e comandos registrados automaticamente.")


def main():
    """
    Função principal para iniciar o bot.
    """
    # Valida as configurações antes de iniciar
    errors = validate_config()
    if errors:
        print("❌ Erros de configuração encontrados:")
        for error in errors:
            print(f"  {error}")
        print("\n💡 Por favor, corrija as configurações no arquivo .env antes de iniciar o bot.")
        return
    
    # Usa o token configurado no .env através do config.py
    TOKEN = BotConfig.BOT_TOKEN
    
    try:
        # Inicia o bot
        bot = Bot()
        bot.run(TOKEN)
        
    except disnake.LoginFailure:
        print("❌ Token inválido. Por favor, verifique seu token do Discord.")
        print("💡 Verifique se o DISCORD_BOT_TOKEN está correto no arquivo .env")
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


if __name__ == "__main__":
    main()