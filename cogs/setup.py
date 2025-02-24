
import asyncio
import json
from datetime import datetime

from discord.ext import commands
from discord import (
    Permissions, Interaction, Embed, Colour,
    TextChannel, app_commands
)
from discord.app_commands import Group

from utils import Utils
from client import Client
from storage import Storage


class AdminCMD(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

        self.utils = Utils()
        self.commands = Client()
        self.storage = Storage()

    setup = Group(name="setup", description="Admin Commands", default_permissions=Permissions(administrator=True), guild_only=True)
    start = Group(name="start", description="Admin Commands", default_permissions=Permissions(administrator=True), guild_only=True)
    node = Group(name="node", description="Admin Commands", default_permissions=Permissions(administrator=True), guild_only=True)
    messages = Group(name="messages", description="Admin Commands", default_permissions=Permissions(administrator=True), guild_only=True)

    @setup.command(name="node", description="setup bitcoinz full node")
    async def setup_node(self, ctx:Interaction):
        await ctx.response.defer()
        embed = self.embed("Setup Node","Progress :","Verifying binary files...")
        await ctx.followup.send(embed=embed)
        await asyncio.sleep(1)
        missing_files = self.utils.get_binary_files()
        if missing_files:
            embed = self.embed("Setup Node","Progress :","Downloading binary files...")
            await ctx.edit_original_response(embed=embed)
            await self.utils.fetch_binary_files()
        await self.verify_params_files(ctx)


    async def verify_params_files(self, ctx):
        embed = self.embed("Setup Node","Progress :","Verify params files...")
        await ctx.edit_original_response(embed=embed)
        await asyncio.sleep(1)
        missing_files = self.utils.get_zk_params()
        if missing_files:
            embed = self.embed("Setup Node","Progress :","Downloading params files...")
            await ctx.edit_original_response(embed=embed)
            await self.utils.fetch_params_files(missing_files)
        await self.verify_config_file(ctx)


    async def verify_config_file(self, ctx):
        embed = self.embed("Setup Node","Progress :", "Verify config file...")
        await ctx.edit_original_response(embed=embed)
        await asyncio.sleep(1)
        config_path = self.utils.get_config_path()
        if not config_path:
            embed = self.embed("Setup Node","Progress :","Create config file...")
            await ctx.edit_original_response(embed=embed)
            self.utils.create_config_file()
            await asyncio.sleep(1)
        embed = self.embed("Setup Node","Completed !","Setup complete! node is ready to start.")
        await ctx.edit_original_response(embed=embed)


    @setup.command(name="channel", description="set chat channel")
    @app_commands.describe(channel="select chat channel")
    async def setup_channel(self, ctx:Interaction, channel:TextChannel):
        await ctx.response.defer(ephemeral=True)
        database = self.storage.is_exists()
        if database:
            is_exists = self.storage.get_identity("channel")
            if is_exists:
                embed = self.embed("Channel Setup", "Error : ","A channel has already been set.")
                await ctx.followup.send(embed=embed)
        else:
            category = "group"
            username = self.client.user.name
            messages_address, error = await self.commands.z_getNewAddress()
            if error is not None:
                embed = self.embed("Channel Setup", "Error : ",error)
                await ctx.followup.send(embed=embed)
                return
            if messages_address:
                prv_key, _= await self.commands.z_ExportKey(messages_address)
                if prv_key:
                    self.storage.key(prv_key)
                self.storage.identity(category, username, messages_address, channel.id)
                embed = self.embed("ZKGroup", "Contact Address :", f"```{messages_address}```\n[Github](https://github.com/SpaceZ-Projects/zk-bridge-discord)")
                await ctx.followup.send(embed=embed)
                message = await channel.send(embed=embed)
                await message.pin()
            else:
                embed = self.embed("Channel Setup", "Error : ","Node is not running.")
                await ctx.followup.send(embed=embed)



    @start.command(name="node", description="starting bitcoinz node")
    async def start_node(self, ctx:Interaction):
        embed = self.embed("Starting Node", "Status :", "Starting Node...")
        await ctx.response.send_message(embed=embed, ephemeral=True)
        result, error = await self.commands.getInfo()
        if error is not None:
            embed = self.embed("Starting Node", "Error :", error)
            await ctx.edit_original_response(embed=embed)
            return
        if result:
            embed = self.embed("Starting Node", "Status :", "Node is already running.")
            await ctx.edit_original_response(embed=embed)
            return
        await self.commands.execute_bitcoinz_node()
        await self.waiting_node_status(ctx)


    async def waiting_node_status(self, ctx):
        await asyncio.sleep(1)
        result, error = await self.commands.getInfo()
        if result:
            self.node_status = True
            await self.verify_sync_progress(ctx)
            return
        else:
            while True:
                result, error = await self.commands.getInfo()
                if result:
                    self.node_status = True
                    await self.verify_sync_progress(ctx)
                    return
                else:
                    if error:
                        embed = self.embed("Starting Node", "Status :", error)
                        await ctx.edit_original_response(embed=embed)
                await asyncio.sleep(4)


    async def verify_sync_progress(self, ctx):
        await asyncio.sleep(1)
        blockchaininfo, _ = await self.commands.getBlockchainInfo()
        if isinstance(blockchaininfo, str):
            info = json.loads(blockchaininfo)
        if info is not None:
            sync = info.get('verificationprogress')
            sync_percentage = sync * 100
            if sync_percentage <= 99.95:
                while True:
                    blockchaininfo, _ = await self.commands.getBlockchainInfo()
                    if isinstance(blockchaininfo, str):
                        info = json.loads(blockchaininfo)
                    else:
                        self.node_status = False
                    if info is not None:
                        blocks = info.get('blocks')
                        sync = info.get('verificationprogress')
                        mediantime = info.get('mediantime')
                    else:
                        blocks = sync = mediantime = "N/A"
                    if isinstance(mediantime, int):
                        mediantime_date = datetime.fromtimestamp(mediantime).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        mediantime_date = "N/A"
                    sync_percentage = sync * 100
                    embed = self.embed("Starting Node","Status :",
                        f"**Blocks :** {blocks}\n"
                        f"**Date :** {mediantime_date}\n"
                        f"**Sync :** %{float(sync_percentage):.2f}"
                    )
                    await ctx.edit_original_response(embed=embed)
                    if sync_percentage > 99.95:
                        embed = self.embed("Starting Node", "Status :", "Node is ready")
                        await ctx.ed(embed=embed)
                        return
                    await asyncio.sleep(10)
            elif sync_percentage > 99.95:
                embed = self.embed("Starting Node", "Status :", "Node is ready")
                await ctx.edit_original_response(embed=embed)


    @node.command(name="getinfo", description="getinfo")
    async def node_getinfo(self, ctx:Interaction):
        await ctx.response.defer(ephemeral=True)
        getinfo, error = await self.commands.getInfo()
        if error is not None:
            embed = self.embed("Getinfo","Error :", error)
            await ctx.followup.send(embed=embed)
            return
        if getinfo:
            embed = self.embed("Getinfo","Result :", getinfo)
            await ctx.followup.send(embed=embed)
        else:
            embed = self.embed("Getinfo", "Error : ","Node is not running.")
            await ctx.followup.send(embed=embed)


    @node.command(name="withdraw", description="withdraw total balance")
    async def node_withdraw(self, ctx:Interaction, toaddress:str):
        address = self.storage.get_identity("address")
        if address:
            balance,_ = await self.commands.z_getBalance(address[0])
            if balance:
                if float(balance) > 0.0001:
                    txfee = 0.0001
                    amount = float(balance) - txfee
                    memo = "withdraw"
                    await self.make_transaction(address[0], toaddress, amount, txfee, memo, ctx)
                else:
                    embed = self.embed("Transaction Failed", "Error :", "The balance is insufficient")
                    await ctx.response.send_message(embed=embed, ephemeral=True)


    @messages.command(name="balance", description="balance of messages address")
    async def messages_balance(self, ctx:Interaction):
        await ctx.response.defer(ephemeral=True)
        address = self.storage.get_identity("address")
        if address:
            balance,_ = await self.commands.z_getBalance(address[0])
            listunspent, _ = await self.commands.z_listUnspent(address[0])
            listunspent = json.loads(listunspent)
            unspent_count = len(listunspent)
            if balance:
                embed = self.embed("Messages Balance","Result :",f"{balance} Unspent : {unspent_count}")
                await ctx.followup.send(embed=embed)
            else:
                embed = self.embed("Messages Balance","Error :","Node is not running.")
                await ctx.followup.send(embed=embed)
        else:
            embed = self.embed("Messages Balance","Error :","Messages address not found")
            await ctx.followup.send(embed=embed)


    @messages.command(name="import", description="import key")
    async def messages_import(self, ctx:Interaction):
        await ctx.response.defer(ephemeral=True)
        address = self.storage.get_identity("address")
        if address:
            balance, _= self.commands.z_getBalance(address[0])
            if balance:
                key = self.storage.get_key()
                if key:
                    await self.commands.z_ImportKey(key[0])
            else:
                embed= self.embed("Impoting Key", "Error :", "Key is already in wallet")
                await ctx.followup.send(embed=embed)



    async def make_transaction(self, address, toaddress, amount, txfee, memo, ctx):
        operation, _= await self.commands.SendMemo(address, toaddress, amount, txfee, memo)
        if operation:
            transaction_status, _= await self.commands.z_getOperationStatus(operation)
            transaction_status = json.loads(transaction_status)
            if isinstance(transaction_status, list) and transaction_status:
                status = transaction_status[0].get('status')
                if status == "executing" or status =="success":
                    await asyncio.sleep(1)
                    while True:
                        transaction_result, _= await self.commands.z_getOperationResult(operation)
                        transaction_result = json.loads(transaction_result)
                        if isinstance(transaction_result, list) and transaction_result:
                            result = transaction_result[0].get('result', {})
                            txid = result.get('txid')
                            self.storage.tx(txid)
                            embed = self.embed("Transaction Success", "transaction ID :", txid)
                            await ctx.response.send_message(embed=embed, ephemeral=True)
                            return
                        await asyncio.sleep(3)
                else:
                    embed = self.embed("Transaction Success", "Error :", "transaction failed !")
                    await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = self.embed("Transaction Success", "Error :", "transaction failed !")
            await ctx.response.send_message(embed=embed, ephemeral=True)
    

    
    def embed(self, title, field_name, field_value):
        embed = Embed()
        embed.title = title
        embed.color = Colour(0x2b2d31)
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed
    

async def setup(client: commands.Bot) -> None:
    await client.add_cog(AdminCMD(client))